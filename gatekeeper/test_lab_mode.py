"""Unit tests for Gatekeeper Lab Mode (config/policy_lab.yaml).

Verifies:
1. In Lab Mode, lower thresholds and demo budget allow interactive sessions to escalate to T2.
2. Bot-like sessions with low scores remain in T1 Lite.
3. Production thresholds (policy.yaml) remain strict and unmodified.
"""

from __future__ import annotations

from pathlib import Path

from gatekeeper.decision_api import DecisionEngine
from gatekeeper.policy import EscalationPolicy


def test_lab_mode_escalates_interactive_session(tmp_path: Path) -> None:
    """Asserts that in lab mode, an interactive session with login success escalates to T2."""
    lab_config = Path(__file__).resolve().parent.parent / "config" / "policy_lab.yaml"
    policy_lab = EscalationPolicy(config_path=lab_config)
    engine = DecisionEngine(db_path=tmp_path / "lab.db", policy=policy_lab)

    res = engine.decide(
        session_id="sess_interactive_01",
        source_ip="127.0.0.1",
        stage="S2",
        features={"cnt_login_success": 1, "cnt_login_failed": 0, "has_pty": 0},
    )

    assert res["tier"] == "T2"
    assert res["score"] >= res["threshold_applied"]
    assert res["fail_cheap"] is False


def test_lab_mode_retains_bot_in_t1(tmp_path: Path) -> None:
    """Asserts that in lab mode, a bot-like probe with failed logins stays in T1 Lite."""
    lab_config = Path(__file__).resolve().parent.parent / "config" / "policy_lab.yaml"
    policy_lab = EscalationPolicy(config_path=lab_config)
    engine = DecisionEngine(db_path=tmp_path / "lab_bot.db", policy=policy_lab)

    res = engine.decide(
        session_id="sess_bot_01",
        source_ip="127.0.0.1",
        stage="S2",
        features={"cnt_login_success": 0, "cnt_login_failed": 1, "has_pty": 0},
    )

    assert res["tier"] == "T1"


def test_production_mode_unmodified(tmp_path: Path) -> None:
    """Asserts that production mode without lab config uses default 10% budget ceiling."""
    engine = DecisionEngine(db_path=tmp_path / "prod.db")
    res = engine.decide(
        session_id="sess_prod_01",
        source_ip="127.0.0.1",
        stage="S2",
        features={"cnt_login_success": 1, "cnt_login_failed": 0, "has_pty": 0},
    )
    # Under 10% budget on a single session, budget ceiling blocks escalation
    assert res["tier"] == "T1"
