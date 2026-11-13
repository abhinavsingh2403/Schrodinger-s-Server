"""
Unit tests for monotone upward-only escalation policy engine.
"""

from __future__ import annotations

import pytest

from gatekeeper.policy import EscalationPolicy


def test_default_tier_t1() -> None:
    policy = EscalationPolicy(threshold_t2=0.5, threshold_t3=0.85, t3_enabled=False)
    tier = policy.decide_tier(current_tier="T1", model_score=0.1)
    assert tier == "T1"


def test_escalation_to_t2() -> None:
    policy = EscalationPolicy(threshold_t2=0.5, threshold_t3=0.85, t3_enabled=False)
    tier = policy.decide_tier(current_tier="T1", model_score=0.6)
    assert tier == "T2"


def test_upward_only_invariance_session() -> None:
    policy = EscalationPolicy(threshold_t2=0.5, threshold_t3=0.85, t3_enabled=False)
    # Session is already at T2; score drops to 0.05. Must remain T2.
    tier = policy.decide_tier(current_tier="T2", model_score=0.05)
    assert tier == "T2"


def test_upward_only_invariance_visitor_memory() -> None:
    policy = EscalationPolicy(threshold_t2=0.5, threshold_t3=0.85, t3_enabled=False)
    # New session starts at T1, but visitor memory shows visitor already earned T2 previously
    visitor = {"highest_tier_served": "T2", "n_sessions": 3}
    tier = policy.decide_tier(current_tier="T1", model_score=0.01, visitor_profile=visitor)
    assert tier == "T2"


def test_t3_escalation_when_enabled() -> None:
    policy = EscalationPolicy(threshold_t2=0.5, threshold_t3=0.85, t3_enabled=True)
    tier = policy.decide_tier(current_tier="T1", model_score=0.92)
    assert tier == "T3"


def test_t3_capped_when_disabled() -> None:
    policy = EscalationPolicy(threshold_t2=0.5, threshold_t3=0.85, t3_enabled=False)
    # High score should cap at T2 when T3 is deferred
    tier = policy.decide_tier(current_tier="T1", model_score=0.95)
    assert tier == "T2"


def test_fail_cheap_on_invalid_input() -> None:
    policy = EscalationPolicy()
    # Malformed score or tier should fail-cheap to T1
    tier = policy.decide_tier(current_tier="INVALID", model_score=float("nan"))
    assert tier == "T1"


def test_policy_loads_yaml_and_stage_thresholds() -> None:
    policy = EscalationPolicy()
    assert policy.max_escalation_fraction == 0.10
    assert policy.max_concurrent_t3 == 4
    # S1 tau_v2 is 0.80 from policy.yaml
    assert policy.get_threshold_t2("S1") == 0.80
    # S4 tau_v2 is 0.50 from policy.yaml
    assert policy.get_threshold_t2("S4") == 0.50


def test_policy_budget_ceiling_enforcement(tmp_path) -> None:
    from gatekeeper.policy import SessionBudget
    budget = SessionBudget(tmp_path / 'budget.db')
    tier, accounting = budget.apply('first', 'T2', 'T1', 'T1', .1)
    assert tier == 'T1'
    assert accounting['blocked']

