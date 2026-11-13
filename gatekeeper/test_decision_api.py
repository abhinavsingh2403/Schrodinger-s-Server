"""
Unit tests for gatekeeper DecisionEngine and decision API contract.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from gatekeeper.decision_api import DecisionEngine


def test_decision_engine_basic_flow(tmp_path: Path) -> None:
    db_file = tmp_path / "test_gatekeeper.db"
    engine = DecisionEngine(db_path=db_file, salt=b"test-salt")

    # S1 Stage with minimal features
    s1_features = {"s1_is_openssh": 1, "s1_kex_count": 5}
    d1 = engine.decide(
        session_id="sess_001",
        source_ip="192.168.1.50",
        stage="S1",
        features=s1_features,
        current_tier="T1",
    )

    assert d1["tier"] == "T1"
    assert d1["fail_cheap"] is False
    assert d1["latency_ms"] < 50.0  # Under 50ms latency target

    # S2 Stage with successful login
    s2_features = {"s2_has_success": 1, "s2_failed_logins": 0}
    d2 = engine.decide(
        session_id="sess_001",
        source_ip="192.168.1.50",
        stage="S2",
        features=s2_features,
        current_tier="T1",
    )

    # The first unique session has no admission slot despite exceeding threshold.
    assert d2["tier"] == "T1"
    assert d2['budget']['blocked']
    assert d2["score"] >= 0.50


def test_decision_engine_logs_to_db(tmp_path: Path) -> None:
    db_file = tmp_path / "test_gatekeeper.db"
    engine = DecisionEngine(db_path=db_file, salt=b"test-salt")

    engine.decide(
        session_id="sess_logged",
        source_ip="10.10.10.10",
        stage="S2",
        features={"s2_has_success": 1},
    )

    # Verify row exists in SQLite table
    conn = sqlite3.connect(db_file)
    row = conn.execute("SELECT * FROM decision_log WHERE session_id = 'sess_logged'").fetchone()
    conn.close()

    assert row is not None
    assert row[1] == "sess_logged"  # session_id column


def test_decision_engine_fail_cheap_guarantee(tmp_path: Path) -> None:
    db_file = tmp_path / "test_gatekeeper.db"
    engine = DecisionEngine(db_path=db_file, salt=b"test-salt")

    # Simulate an internal runtime error during policy evaluation
    from unittest.mock import MagicMock
    engine.policy.decide_tier = MagicMock(side_effect=RuntimeError("Forced policy failure"))

    res = engine.decide(
        session_id="sess_fail",
        source_ip="1.1.1.1",
        stage="S1",
        features={},
        current_tier="T1",
    )

    # Must return fail_cheap=True and default to T1 without crashing
    assert res["tier"] == "T1"
    assert res["fail_cheap"] is True


def test_decision_engine_sensor_feature_key_reconciliation(tmp_path: Path) -> None:
    """Verify raw sensor dict keys (login_success, n_login_failed) work identically to extractor keys."""
    db_file = tmp_path / "test_gatekeeper.db"
    engine = DecisionEngine(db_path=db_file, salt=b"test-salt")

    # Sensor passes {"login_success": 1, "n_login_failed": 0}
    sensor_features = {"login_success": 1, "n_login_failed": 0}
    decision = engine.decide(
        session_id="sess_sensor_raw",
        source_ip="192.168.1.100",
        stage="S2",
        features=sensor_features,
        current_tier="T1",
    )

    assert decision["tier"] == "T1"
    assert decision['budget']['blocked']
    assert decision["score"] == 0.70


def test_decision_engine_record_session_lifecycle(tmp_path: Path) -> None:
    """Verify record_session updates visitor memory and influences subsequent visits."""
    db_file = tmp_path / "test_gatekeeper.db"
    engine = DecisionEngine(db_path=db_file, salt=b"test-salt")
    ip = "192.168.1.200"

    # Initial session: unknown visitor, stage S1 -> stays T1
    d1 = engine.decide("sess_1", ip, stage="S1", features={}, current_tier="T1")
    assert d1["tier"] == "T1"

    # Session completes at T2 after escalating
    engine.record_session(source_ip=ip, tier_served="T2", value_label=1)

    # Second session from same visitor: visitor memory knows visitor previously reached T2
    profile = engine.memory.get_visitor(ip)
    assert profile is not None
    assert profile["n_sessions"] == 1
    assert profile["highest_tier_served"] == "T2"


def test_gatekeeper_http_service_and_client_lifecycle(tmp_path: Path) -> None:
    """Verify Gatekeeper HTTP service endpoints (/health, /decide, /record_session) and client."""
    import http.server
    import threading
    import urllib.request
    from gatekeeper.decision_api import GatekeeperHTTPHandler, GatekeeperClient

    db_file = tmp_path / "test_http_gatekeeper.db"
    engine = DecisionEngine(db_path=db_file, salt=b"http-salt")

    # Start server on ephemeral port (0)
    server = http.server.HTTPServer(("127.0.0.1", 0), GatekeeperHTTPHandler)
    server.decision_engine = engine  # type: ignore[attr-defined]
    host, port = server.server_address

    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()

    try:
        # 1. Health check
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2.0) as resp:
            assert resp.status == 200
            data = resp.read().decode("utf-8")
            assert "gatekeeper" in data

        # 2. Client decide over HTTP
        client = GatekeeperClient(base_url=f"http://127.0.0.1:{port}", timeout=2.0)
        res = client.decide(
            session_id="sess_http_01",
            source_ip="192.168.1.99",
            stage="S2",
            features={"login_success": 1},
        )
        assert res["tier"] == "T1"
        assert res['budget']['blocked']
        assert res["fail_cheap"] is False

        # 3. Client record_session over HTTP
        rec = client.record_session(source_ip="192.168.1.99", tier_served="T2", value_label=1)
        assert rec.get("highest_tier_served") == "T2"

        # 4. Fail-cheap behavior on unreachable host
        bad_client = GatekeeperClient(base_url="http://127.0.0.1:59999", timeout=0.1)
        fallback = bad_client.decide(session_id="sess_dead", source_ip="1.2.3.4", current_tier="T1")
        assert fallback["fail_cheap"] is True
        assert fallback["tier"] == "T1"

    finally:
        server.shutdown()
        server.server_close()

