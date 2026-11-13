"""
Truthfulness and Provenance Tests for Schrödinger's Server Dashboard.
Enforces G1, G2, G3: Zero fabricated data, source provenance labels, and truthfulness.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
import pytest

from gatekeeper.decision_api import DecisionEngine
from gatekeeper.visitor_memory import VisitorMemory
from dashboard.app import DashboardServer

DASHBOARD_DIR = Path(__file__).resolve().parent


def test_no_math_random():
    """Acceptance (1): Grep for Math.random across all dashboard/ files returns nothing."""
    for root, _, files in os.walk(DASHBOARD_DIR):
        if "__pycache__" in root:
            continue
        for f in files:
            p = Path(root) / f
            if p.suffix in (".html", ".js", ".py") and p.name != "test_truthfulness.py":
                content = p.read_text(encoding="utf-8", errors="ignore")
                assert "Math.random" not in content, f"Found Math.random in {p}"


def test_no_hardcoded_session_arrays():
    """Verify no hardcoded session fixture arrays exist in dashboard source code."""
    for root, _, files in os.walk(DASHBOARD_DIR):
        if "__pycache__" in root:
            continue
        for f in files:
            p = Path(root) / f
            if p.suffix in (".html", ".js", ".py") and not p.name.startswith("test_"):
                content = p.read_text(encoding="utf-8", errors="ignore")
                assert "sample_sessions = [" not in content, f"Found sample_sessions in {p}"
                assert "sess_live_901" not in content, f"Found fake session row in {p}"
                assert "sess_live_902" not in content, f"Found fake session row in {p}"
                assert "sess_live_903" not in content, f"Found fake session row in {p}"


def test_no_base_rates_literals_in_dashboard():
    """Test fails if any file under dashboard/ contains numeric literals from results/base_rates.json."""
    base_rates_file = Path(__file__).resolve().parent.parent / "results" / "base_rates.json"
    assert base_rates_file.exists(), "results/base_rates.json must exist to extract comparison literals"

    with open(base_rates_file, "r", encoding="utf-8") as f:
        br = json.load(f)

    # Collect numeric literals from base_rates.json (overall totals and counts >= 52)
    extracted_literals = set()

    def collect_numbers(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                collect_numbers(v)
        elif isinstance(obj, list):
            for item in obj:
                collect_numbers(item)
        elif isinstance(obj, int) and not isinstance(obj, bool):
            if obj >= 52:  # Ignore small generic integers
                extracted_literals.add(str(obj))

    collect_numbers(br)

    # Check that no dashboard source/template file contains these literals as hard-coded text
    for root, _, files in os.walk(DASHBOARD_DIR):
        if "__pycache__" in root:
            continue
        for f in files:
            p = Path(root) / f
            if p.suffix in (".html", ".js", ".py") and p.name != "test_truthfulness.py":
                content = p.read_text(encoding="utf-8", errors="ignore")
                for lit in extracted_literals:
                    assert lit not in content, f"Found hardcoded literal {lit} from base_rates.json in {p}"


def test_each_api_panel_payload_includes_source_key():
    """Verify each API panel payload in app.py includes a `source` key with one of RECORDED, LAB, LIVE."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "dash.db")
        server = DashboardServer(db_path=db_path, port=0)

        valid_sources = {"RECORDED", "LAB", "LIVE"}

        # 1. /api/stats
        stats = server.get_stats_data()
        assert "source" in stats, "Missing 'source' in /api/stats"
        assert stats["source"] in valid_sources

        # 2. /api/decisions
        decisions = server.get_decisions_data()
        assert "source" in decisions, "Missing 'source' in /api/decisions"
        assert decisions["source"] in valid_sources

        # 3. /api/arms
        arms = server.get_arms_data()
        assert "source" in arms, "Missing 'source' in /api/arms"
        assert arms["source"] in valid_sources

        # 4. /api/natural_experiment
        nat = server.get_natural_experiment_data()
        assert "source" in nat, "Missing 'source' in /api/natural_experiment"
        assert nat["source"] in valid_sources

        # 5. /api/model
        model = server.get_model_data()
        assert "source" in model, "Missing 'source' in /api/model"
        assert model["source"] in valid_sources

        # 6. /api/exp0
        exp0 = server.get_exp0_data()
        assert "source" in exp0, "Missing 'source' in /api/exp0"
        assert exp0["source"] in valid_sources

        # 7. /api/detector
        detector = server.get_detector_data()
        assert "source" in detector, "Missing 'source' in /api/detector"
        assert detector["source"] in valid_sources


def test_provenance_three_source_cases_and_missing_file():
    """G3 Acceptance: Unit tests for the three source cases (RECORDED, LAB, LIVE) and missing-file case."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test_dash.db")

        # 1. Case RECORDED: data comes from results/
        rec_server = DashboardServer(db_path=db_path, port=0)
        rec_stats = rec_server.get_stats_data()
        assert rec_stats["source"] == "RECORDED"
        rec_arms = rec_server.get_arms_data()
        assert rec_arms["source"] == "RECORDED"

        # 2. Case LAB: decision log from sensor started in LAB mode
        lab_server = DashboardServer(db_path=db_path, mode="LAB", port=0)
        # Populate at least one decision in LAB mode
        memory = VisitorMemory(db_path=db_path)
        engine = DecisionEngine(db_path=db_path, memory=memory)
        engine.decide(session_id="sess_lab_01", source_ip="127.0.0.1", stage="S1")
        lab_decisions = lab_server.get_decisions_data()
        assert lab_decisions["source"] == "LAB"

        # 3. Case LIVE: mode is LIVE and log is non-empty
        live_server = DashboardServer(db_path=db_path, mode="LIVE", port=0)
        live_decisions = live_server.get_decisions_data()
        assert live_decisions["source"] == "LIVE"

        # 3b. Empty LIVE log falls back to LAB
        empty_db_path = os.path.join(tmp_dir, "empty.db")
        empty_live_server = DashboardServer(db_path=empty_db_path, mode="LIVE", port=0)
        empty_decisions = empty_live_server.get_decisions_data()
        assert empty_decisions["source"] == "LAB"

        # 4. Case Missing-File: If source file is missing, return status 'NO DATA'
        missing_server = DashboardServer(
            base_rates_path=os.path.join(tmp_dir, "nonexistent_rates.json"),
            arm_simulation_path=os.path.join(tmp_dir, "nonexistent_arms.json"),
            natural_experiment_path=os.path.join(tmp_dir, "nonexistent_nat.json"),
            model_path=os.path.join(tmp_dir, "nonexistent_model.json"),
            exp0_path=os.path.join(tmp_dir, "nonexistent_exp0.json"),
            db_path=os.path.join(tmp_dir, "nonexistent.db"),
            port=0,
        )
        assert missing_server.get_stats_data()["status"] == "NO DATA"
        assert missing_server.get_arms_data()["status"] == "NO DATA"
        assert missing_server.get_natural_experiment_data()["status"] == "NO DATA"
        assert missing_server.get_model_data()["status"] == "NO DATA"
        assert missing_server.get_exp0_data()["status"] == "NO DATA"
        assert missing_server.get_decisions_data()["status"] == "NO DATA"


def test_html_badges_and_no_data():
    """Verify HTML displays required badges and renders with or without data."""
    server = DashboardServer()
    html = server.render_index_html()

    assert "SIMULATED ORACLE (HINDSIGHT UPPER BOUND)" in html
    assert "EVAL H4 NOT YET EVALUATED" in html
    assert "RECORDED" in html
    assert "LAB" in html
    assert "LIVE" in html
    assert "NO DATA" in html
    assert "Math.random" not in html
