"""
Tests for Adversary Lab Detector Harness (harness/detector_runner.py).
Pre-registered in SPEC.md Section 5.4, SAFETY.md, and SPIKES.md S4.
"""

from __future__ import annotations

import os
import tempfile
import pytest
from harness.detector_runner import (
    AdversaryDetectorRunner,
    SafetyViolationError,
    ProbeResult,
    is_target_allowlisted,
)
from sensor.adaptive_server import PersonaManager


def test_safety_guard_blocks_external_ip():
    """Verify SAFETY.md enforcement: external IPs must raise SafetyViolationError."""
    runner = AdversaryDetectorRunner(target_host="8.8.8.8", target_port=22)
    with pytest.raises(SafetyViolationError, match="External network target forbidden"):
        runner.run_audit()

    runner_domain = AdversaryDetectorRunner(target_host="google.com", target_port=22)
    with pytest.raises(SafetyViolationError, match="External network target forbidden"):
        runner_domain.run_audit()


def test_safety_guard_allows_lab_targets():
    """Verify that localhost and loopback targets are permitted."""
    assert is_target_allowlisted("127.0.0.1") is True
    assert is_target_allowlisted("localhost") is True
    assert is_target_allowlisted("::1") is True
    assert is_target_allowlisted("10.0.0.5", allow_rfc1918=True) is True
    assert is_target_allowlisted("198.51.100.1") is False


def test_persona_coherence_probe():
    """Test OS coherence audit against generated persona filesystem."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        pm = PersonaManager(base_dir=tmp_dir)
        p1 = pm.get_persona("T1")
        p2 = pm.get_persona("T2")

        runner = AdversaryDetectorRunner(target_host="127.0.0.1", target_port=2222)

        # Audit T1 persona
        res_t1 = runner.audit_persona_coherence(p1)
        assert res_t1.category == "OS_COHERENCE"
        assert res_t1.passed is True
        assert res_t1.score >= 0.90

        # Audit T2 persona
        res_t2 = runner.audit_persona_coherence(p2)
        assert res_t2.category == "OS_COHERENCE"
        assert res_t2.passed is True
        assert res_t2.score >= 0.95


def test_filesystem_leak_probe():
    """Test detection of default honeypot indicators (SPEC Risk R8)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        runner = AdversaryDetectorRunner(target_host="127.0.0.1", target_port=2222)

        # Clean directory matching Ubuntu profile
        clean_dir = os.path.join(tmp_dir, "clean")
        os.makedirs(os.path.join(clean_dir, "etc"), exist_ok=True)
        with open(os.path.join(clean_dir, "etc", "issue"), "w") as f:
            f.write("Ubuntu 22.04.3 LTS \\n \\l\n")

        res_clean = runner.audit_filesystem_artifacts(clean_dir)
        assert res_clean.passed is True
        assert res_clean.score == 1.0

        # Dirty directory containing known default Cowrie giveaway artifact
        dirty_dir = os.path.join(tmp_dir, "dirty")
        os.makedirs(os.path.join(dirty_dir, "home", "richard"), exist_ok=True)
        with open(os.path.join(dirty_dir, "home", "richard", ".bash_history"), "w") as f:
            f.write("cowrie test\n")

        res_dirty = runner.audit_filesystem_artifacts(dirty_dir)
        assert res_dirty.passed is False
        assert res_dirty.score < 1.0
        assert any("richard" in tell.lower() for tell in res_dirty.findings)


def test_full_lab_audit_execution():
    """Execute complete simulated audit run producing structured report."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        pm = PersonaManager(base_dir=tmp_dir)
        p2 = pm.get_persona("T2")

        runner = AdversaryDetectorRunner(target_host="127.0.0.1", target_port=2222)
        report = runner.run_persona_audit(p2)

        assert report["target"] == "127.0.0.1:2222"
        assert report["tier"] == "T2"
        assert "overall_evasion_score" in report
        assert report["overall_evasion_score"] >= 0.80
        assert len(report["categories"]) >= 3
