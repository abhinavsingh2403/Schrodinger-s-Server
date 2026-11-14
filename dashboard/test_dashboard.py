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
        engine.decide(session_id="sess_t1", source_ip="198.51.100.11", stage="S1", provenance="LAB")
        engine.decide(session_id="sess_t2", source_ip="203.0.113.88", stage="S4", features={"s4_cmd1_has_pipe": 1}, provenance="LAB")

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
        assert "SYNTHETIC" in html
        assert "UNKNOWN" in html
        assert "Yield per Rupee" in html
        assert "SIMULATED ORACLE (HINDSIGHT UPPER BOUND)" in html
        assert "EVAL H4 NOT YET EVALUATED" in html
        assert "NO DATA" in html


def test_dashboard_synthetic_provenance_marking():
    """Verify AGENTS.md Rules 1 & 2: Scripted/synthetic probe sessions are strictly labeled SYNTHETIC via provenance column."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "synth.db")
        memory = VisitorMemory(db_path=db_path)
        engine = DecisionEngine(db_path=db_path, memory=memory)

        # Record a synthetic probe session with explicit column provenance
        engine.decide(session_id="sess_synth_bot_01", source_ip="192.0.2.10", stage="S1", provenance="SYNTHETIC")

        server = DashboardServer(db_path=db_path, port=0, mode="LAB")
        decisions_data = server.get_decisions_data()
        assert decisions_data["status"] == "ok"
        # Must be detected as SYNTHETIC via column, never mislabeled as authentic LAB or LIVE
        assert decisions_data["source"] == "SYNTHETIC"
        assert decisions_data["decisions"][0]["provenance"] == "SYNTHETIC"

        stats = server.get_stats_data()
        assert stats["sensor"]["source"] == "SYNTHETIC"


def test_dashboard_empty_db_with_synthetic_mode():
    """Verify that an empty database with --mode SYNTHETIC returns SYNTHETIC provenance for both endpoints."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        empty_db = os.path.join(tmp_dir, "empty_synth.db")
        server = DashboardServer(db_path=empty_db, port=0, mode="SYNTHETIC")

        # 1. /api/decisions
        decisions_data = server.get_decisions_data()
        assert decisions_data["source"] == "SYNTHETIC"
        assert decisions_data["label"] == "SYNTHETIC"

        # 2. /api/stats
        stats_data = server.get_stats_data()
        assert stats_data["sensor"]["source"] == "SYNTHETIC"
        assert stats_data["sensor"]["label"] == "SYNTHETIC"


def test_dashboard_mixed_rows_provenance():
    """Verify that a database containing mixed provenance rows returns MIXED aggregate source and preserves per-row provenance."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        mixed_db = os.path.join(tmp_dir, "mixed.db")
        memory = VisitorMemory(db_path=mixed_db)
        engine = DecisionEngine(db_path=mixed_db, memory=memory)

        # Record 1 LAB row and 1 SYNTHETIC row
        engine.decide(session_id="sess_real_lab_01", source_ip="127.0.0.1", stage="S1", provenance="LAB")
        engine.decide(session_id="sess_scripted_02", source_ip="192.0.2.20", stage="S1", provenance="SYNTHETIC")

        server = DashboardServer(db_path=mixed_db, port=0, mode="LAB")

        # Decisions endpoint returns MIXED aggregate source
        decisions_data = server.get_decisions_data()
        assert decisions_data["status"] == "ok"
        assert decisions_data["source"] == "MIXED"
        assert decisions_data["count"] == 2

        # Verify per-row provenance is read and preserved
        row_provs = {d["session_id"]: d["provenance"] for d in decisions_data["decisions"]}
        assert row_provs["sess_real_lab_01"] == "LAB"
        assert row_provs["sess_scripted_02"] == "SYNTHETIC"

        # Stats endpoint returns MIXED aggregate source
        stats_data = server.get_stats_data()
        assert stats_data["sensor"]["source"] == "MIXED"


def test_dashboard_renamed_session_id_provenance_column():
    """Verify that provenance is read strictly from the column, NOT inferred from session ID prefixes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "renamed.db")
        memory = VisitorMemory(db_path=db_path)
        engine = DecisionEngine(db_path=db_path, memory=memory)

        # Session with arbitrary name having NO 'synth' prefix, but column provenance = 'SYNTHETIC'
        engine.decide(session_id="custom_honeypot_eval_alpha", source_ip="192.0.2.33", stage="S1", provenance="SYNTHETIC")

        server = DashboardServer(db_path=db_path, port=0, mode="LAB")
        decisions_data = server.get_decisions_data()
        assert decisions_data["source"] == "SYNTHETIC"
        assert decisions_data["decisions"][0]["provenance"] == "SYNTHETIC"

        stats_data = server.get_stats_data()
        assert stats_data["sensor"]["source"] == "SYNTHETIC"

        # Opposite case: Session with 'synth' in its name, but column provenance = 'LAB'
        db_path2 = os.path.join(tmp_dir, "renamed_lab.db")
        memory2 = VisitorMemory(db_path=db_path2)
        engine2 = DecisionEngine(db_path=db_path2, memory=memory2)
        engine2.decide(session_id="sess_synth_name_misleading", source_ip="127.0.0.1", stage="S1", provenance="LAB")

        server2 = DashboardServer(db_path=db_path2, port=0, mode="LAB")
        decisions2 = server2.get_decisions_data()
        assert decisions2["source"] == "LAB"
        assert decisions2["decisions"][0]["provenance"] == "LAB"


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


def test_dashboard_missing_provenance_becomes_unknown():
    """Verify missing/null provenance in decision log or empty DB safely resolves to UNKNOWN."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Case 1: Empty database without SYNTHETIC mode
        empty_db = os.path.join(tmp_dir, "empty_unk.db")
        server = DashboardServer(db_path=empty_db, port=0, mode="LAB")
        assert server.get_decisions_data()["source"] == "UNKNOWN"
        assert server.get_stats_data()["sensor"]["source"] == "UNKNOWN"

        # Case 2: Database with rows having NULL or missing provenance
        null_db = os.path.join(tmp_dir, "null_prov.db")
        memory = VisitorMemory(db_path=null_db)
        engine = DecisionEngine(db_path=null_db, memory=memory)
        # Calling decide() with default provenance writes UNKNOWN
        engine.decide(session_id="sess_legacy_01", source_ip="127.0.0.1", stage="S1")

        server2 = DashboardServer(db_path=null_db, port=0, mode="LAB")
        dec_data = server2.get_decisions_data()
        assert dec_data["source"] == "UNKNOWN"
        assert dec_data["decisions"][0]["provenance"] == "UNKNOWN"

        stats_data = server2.get_stats_data()
        assert stats_data["sensor"]["source"] == "UNKNOWN"


def test_dashboard_lab_only_db_under_mode_live_not_labeled_live():
    """Verify that a database containing only LAB decisions is NOT labeled LIVE under --mode LIVE."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        lab_db = os.path.join(tmp_dir, "lab_only.db")
        memory = VisitorMemory(db_path=lab_db)
        engine = DecisionEngine(db_path=lab_db, memory=memory)

        # Populate authentic LAB decisions
        engine.decide(session_id="sess_lab_01", source_ip="127.0.0.1", stage="S1", provenance="LAB")
        engine.decide(session_id="sess_lab_02", source_ip="127.0.0.1", stage="S2", provenance="LAB")

        # Start dashboard in LIVE mode
        server = DashboardServer(db_path=lab_db, port=0, mode="LIVE")

        # Both /api/decisions and /api/stats must report LAB, never falsely claiming LIVE
        dec_data = server.get_decisions_data()
        assert dec_data["source"] == "LAB"
        assert dec_data["label"] == "LAB"
        for d in dec_data["decisions"]:
            assert d["provenance"] == "LAB"

        stats_data = server.get_stats_data()
        assert stats_data["sensor"]["source"] == "LAB"
        assert stats_data["sensor"]["label"] == "LAB"

