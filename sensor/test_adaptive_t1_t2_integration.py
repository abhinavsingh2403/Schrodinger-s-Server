"""
test_adaptive_t1_t2_integration.py: Full Lifecycle Integration Tests for Adaptive T1/T2 Persona System.

Pre-registered in SPEC.md Section 5.1, Section 5.3 and Sprint 1 Priority 3.
Verifies:
1. Initial T1 allocation at session connect.
2. Full stage event ingestion (S1 KEX -> S2 Auth -> S3 Channel PTY -> S4 Command -> S5 Activity).
3. Deterministic mid-session escalation from T1 to T2 upon interactive PTY allocation.
4. Monotone upward-only progression (no demotion from T2 to T1).
5. Persona filesystem switching and decoy asset presence in T2.
6. Session termination updating SQLite visitor memory.
7. Returning visitor sticky T2 allocation on initial handshake.
8. Escalation budget enforcement: when budget cap is reached, escalation is blocked.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import pytest

from gatekeeper.decision_api import DecisionEngine
from gatekeeper.feature_extractor import SessionFeatureExtractor
from gatekeeper.policy import EscalationPolicy, SessionBudget
from gatekeeper.visitor_memory import VisitorMemory
from sensor.adaptive_server import AdaptiveSessionAdapter, PersonaManager, TIER_ORDER


def test_adaptive_session_lifecycle_t1_to_t2_escalation():
    """Verify complete end-to-end adaptive session lifecycle with T1 -> T2 escalation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "adaptive_test.db"
        personas_dir = Path(tmp_dir) / "personas"
        salt = b"test-adaptive-salt-2026"

        personas = PersonaManager(base_dir=str(personas_dir))
        memory = VisitorMemory(db_path=db_path, salt=salt)
        engine = DecisionEngine(db_path=db_path, salt=salt, memory=memory, lab_mode=True)

        tier_changes = []
        def on_tier_changed(new_tier, persona):
            tier_changes.append((new_tier, persona.tier))

        visitor_ip = "198.51.100.45"
        session_id = "sess_live_integration_01"

        adapter = AdaptiveSessionAdapter(
            visitor_ip=visitor_ip,
            session_id=session_id,
            decision_engine=engine,
            persona_manager=personas,
            on_tier_changed=on_tier_changed,
            provenance="LAB",
        )

        # 1. Initial State: Must begin in T1
        assert adapter.current_tier == "T1"
        p_initial = adapter.get_active_persona()
        assert p_initial.tier == "T1"

        # 2. Stage S1: Key Exchange Completed
        adapter.on_kex_completed(
            client_version="SSH-2.0-OpenSSH_9.2p1",
            hassh="c7c4f4d2f8e1a5b3",
            kex_algs=["curve25519-sha256"],
            key_algs=["ssh-ed25519"],
        )
        assert adapter.current_tier == "T1", "Normal S1 handshake must remain in T1"

        # 3. Stage S2: Authentication Completed
        adapter.on_auth_completed(success=True, failed_count=0, username="admin")
        assert adapter.current_tier == "T1", "Auth success in baseline lab mode remains in T1"

        # 4. Stage S3: Channel Setup with Interactive PTY Allocation
        # This triggers deterministic escalation in LAB_DEMO mode (lab_pty_mechanism)
        adapter._evaluate_stage("S3", {"has_pty": 1, "cnt_login_success": 1})
        assert adapter.current_tier == "T2", "PTY allocation at S3 must trigger escalation to T2"
        assert len(tier_changes) == 1
        assert tier_changes[0] == ("T2", "T2")

        # 5. Active Persona Inspection
        p_escalated = adapter.get_active_persona()
        assert p_escalated.tier == "T2"
        # T2 filesystem contains enriched honeypot assets per SPEC Section 5.1
        t2_index_html = Path(p_escalated.fs_dir) / "var/www/html/index.html"
        assert t2_index_html.is_file(), "T2 honeypot filesystem must contain decoy index.html"
        assert "Maintenance Mode" in t2_index_html.read_text(encoding="utf-8")

        # 6. Stage S4 & S5: Shell Commands (Monotone Upward-Only Invariant)
        adapter.on_command_received("id")
        assert adapter.current_tier == "T2", "Subsequent command must not demote from T2"

        adapter.on_command_received("ls -la /var/www")
        assert adapter.current_tier == "T2", "Stage S5 commands must strictly maintain T2"

        # 7. Session Termination: Persists to Visitor Memory
        adapter.on_session_closed(value_label=1)

        # Verify Visitor Memory record
        profile = memory.get_visitor(visitor_ip)
        assert profile is not None
        assert profile["highest_tier_served"] == "T2"
        assert profile["n_sessions"] == 1

        # 8. Returning Visitor Session: Must start in T2 stickily
        sess_returning_id = "sess_live_integration_02"
        returning_adapter = AdaptiveSessionAdapter(
            visitor_ip=visitor_ip,
            session_id=sess_returning_id,
            decision_engine=engine,
            persona_manager=personas,
            provenance="LAB",
        )
        # S1 handshake for returning visitor queries memory and escalates immediately to T2
        returning_adapter._evaluate_stage("S1", {})
        assert returning_adapter.current_tier == "T2", "Returning visitor must stickily start in T2"


def test_escalation_budget_cap_enforcement():
    """Verify that escalation budget cap strictly prevents escalation when exhausted."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "budget_test.db"
        policy = EscalationPolicy(threshold_t2=0.50)
        policy.max_escalation_fraction = 0.10
        engine = DecisionEngine(db_path=db_path, policy=policy, lab_mode=False)

        # Baseline: 10 sessions all staying at T1
        for i in range(10):
            d = engine.decide(
                session_id=f"sess_base_{i}",
                source_ip=f"192.0.2.{i+10}",
                stage="S1",
                current_tier="T1",
                provenance="LAB",
            )
            assert d["tier"] == "T1"

        # Now 1 session escalates to T2 (1 out of 11 = 9.09% <= 10% budget)
        d_esc = engine.decide(
            session_id="sess_allowed_esc",
            source_ip="192.0.2.99",
            stage="S2",
            features={"login_success": 1},  # rule_r1_login_success yields score 0.70 > 0.50
            current_tier="T1",
            provenance="LAB",
        )
        # Should be admitted to T2
        assert d_esc["tier"] == "T2"
        assert d_esc["budget"]["blocked"] is False

        # Attempt another escalation immediately (2 out of 12 = 16.67% > 10% budget)
        d_blocked = engine.decide(
            session_id="sess_blocked_esc",
            source_ip="192.0.2.100",
            stage="S2",
            features={"login_success": 1},
            current_tier="T1",
            provenance="LAB",
        )
        # Budget cap must BLOCK this escalation and safely cap tier at T1!
        assert d_blocked["tier"] == "T1", "Escalation must be blocked when exceeding budget cap"
        assert d_blocked["budget"]["blocked"] is True
