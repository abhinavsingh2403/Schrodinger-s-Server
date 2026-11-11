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

    # Score of 0.70 exceeds default threshold_t2 (0.50) -> Escalates to T2
    assert d2["tier"] == "T2"
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
