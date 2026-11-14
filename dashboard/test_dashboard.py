"""
Tests for Read-Only Results Dashboard (dashboard/test_dashboard.py).
Pre-registered in SPEC.md Section 4 and AGENTS.md Rule 19.
"""

from __future__ import annotations

import json
import os
import tempfile
import pytest
from gatekeeper.decision_api import DecisionEngine
from gatekeeper.visitor_memory import VisitorMemory
from dashboard.app import DashboardServer, make_dashboard_handler


def test_dashboard_stats_endpoint_recorded_labels():
    """Verify /api/stats returns RECORDED dataset metrics and base rates from results/."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "dash.db")
        server = DashboardServer(db_path=db_path, port=0)

        stats = server.get_stats_data()
        assert stats["status"] == "ok"
        assert stats["source"] == "RECORDED"
        assert stats["dataset"]["label"] == "RECORDED"

        # Dynamically verify against results/base_rates.json without hard-coded numbers
        base_rates_file = "results/base_rates.json"
        if os.path.exists(base_rates_file):
            with open(base_rates_file, "r", encoding="utf-8") as f:
                expected = json.load(f)
            assert stats["dataset"]["total_sessions"] == expected["overall"]["total_sessions"]
            assert stats["dataset"]["days_covered"] == len(expected.get("by_day", {}))


def test_dashboard_decisions_masking_rule():
    """Verify AGENTS.md Rule 19: All visitor identifiers must be masked (vis_xxxx)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "dash.db")
        memory = VisitorMemory(db_path=db_path)
        engine = DecisionEngine(db_path=db_path, memory=memory)

        # Make decisions with simulated raw IPs
        engine.decide(session_id="sess_t1", source_ip="198.51.100.11", stage="S1")
        engine.decide(session_id="sess_t2", source_ip="203.0.113.88", stage="S4", features={"s4_cmd1_has_pipe": 1})

        server = DashboardServer(db_path=db_path, port=0)
        decisions_data = server.get_decisions_data()

        assert decisions_data["status"] == "ok"
        assert decisions_data["source"] in ("LAB", "LIVE")
        records = decisions_data["decisions"]
        assert len(records) >= 2

        for r in records:
            # Must start with vis_ prefix
            assert r["visitor_id"].startswith("vis_")
            # Raw IP must NEVER be present anywhere in the decision dict
            assert "198.51.100" not in json.dumps(r)
            assert "203.0.113" not in json.dumps(r)


def test_dashboard_arms_comparison_endpoint():
    """Verify /api/arms computes comparative intelligence yield per rupee."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "dash.db")
        server = DashboardServer(db_path=db_path, port=0)

        arms = server.get_arms_data()
        assert arms["status"] == "ok"
        assert arms["source"] == "RECORDED"
        assert arms["badge"] == "SIMULATED ORACLE (HINDSIGHT UPPER BOUND)"
        assert "Arm A (Static T1)" in arms
        assert ("Arm D (Schrodinger Adaptive)" in arms) or ("Arm D (Adaptive)" in arms)
        assert arms.get("Arm D (Schrodinger Adaptive)", arms.get("Arm D (Adaptive)"))["yield_per_rupee"] > 0
        assert arms["Arm A (Static T1)"]["yield_per_rupee"] > 0


def test_dashboard_natural_experiment_endpoint():
    """Verify /api/natural_experiment returns valid observational data or status."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "dash.db")
        server = DashboardServer(db_path=db_path, port=0)

        nat_data = server.get_natural_experiment_data()
        assert "status" in nat_data
        assert nat_data["source"] == "RECORDED"
        if nat_data["status"] == "NATURAL_EXPERIMENT_COMPLETE":
            assert "caveat_disclaimer" in nat_data
            assert "n_instances_evaluated" in nat_data
            assert "instances" in nat_data


def test_dashboard_html_rendering():
    """Verify HTML dashboard renders panel markers and design structure."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "dash.db")
        server = DashboardServer(db_path=db_path, port=0)
        html = server.render_index_html()

        assert "Schrödinger's Server" in html
        assert "RECORDED" in html
        assert "LAB" in html
        assert "LIVE" in html
        assert "Yield per Rupee" in html
        assert "SIMULATED ORACLE (HINDSIGHT UPPER BOUND)" in html
        assert "EVAL H4 NOT YET EVALUATED" in html
        assert "NO DATA" in html


def test_dashboard_custom_db_path():
    """Verify DashboardServer correctly accepts and reads from a custom db_path."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        custom_db = os.path.join(tmp_dir, "custom_gatekeeper.db")
        memory = VisitorMemory(db_path=custom_db)
        engine = DecisionEngine(db_path=custom_db, memory=memory)
        engine.decide(session_id="sess_custom_01", source_ip="127.0.0.1", stage="S1")

        server = DashboardServer(db_path=custom_db, port=0)
        decisions = server.get_decisions_data()
        assert decisions["status"] == "ok"
        assert decisions["count"] == 1
        assert decisions["decisions"][0]["session_id"] == "sess_custom_01"
