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
    """Verify /api/stats returns RECORDED dataset metrics and base rates."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "dash.db")
        server = DashboardServer(db_path=db_path, port=0)

        stats = server.get_stats_data()
        assert stats["status"] == "ok"
        assert stats["dataset"]["label"] == "RECORDED"
        assert stats["dataset"]["total_sessions"] == 38126048
        assert stats["dataset"]["base_rate_pct"] == 3.23
        assert stats["dataset"]["days_covered"] == 52


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

        assert decisions_data["label"] in ("LAB", "LIVE")
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
        assert "Arm A (Static T1)" in arms
        assert "Arm D (Schrodinger Adaptive)" in arms
        assert arms["Arm D (Schrodinger Adaptive)"]["yield_per_rupee"] > 0
        assert arms["Arm A (Static T1)"]["yield_per_rupee"] > 0


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
