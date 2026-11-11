"""Tests for Experiment 0 Training Harness (analysis/exp0_train.py).

Pre-registered in EXPERIMENT0.md.
Tests rule evaluation, paired cluster bootstrap, and Gate 0 decision rule logic.
"""

from __future__ import annotations

import pytest
from analysis.exp0_train import (
    evaluate_simple_rules,
    paired_cluster_bootstrap_delta,
    evaluate_gate0_decision_rule,
)


def test_evaluate_simple_rules_ranking():
    """Verify simple rule scores correctly compute recall at budget."""
    mock_records = [
        {"session": "s1", "cnt_login_success": 1, "cnt_login_failed": 0, "has_pty": True, "cnt_client_version": 1, "v_full": 1},
        {"session": "s2", "cnt_login_success": 1, "cnt_login_failed": 2, "has_pty": False, "cnt_client_version": 1, "v_full": 1},
        {"session": "s3", "cnt_login_success": 0, "cnt_login_failed": 5, "has_pty": False, "cnt_client_version": 2, "v_full": 0},
        {"session": "s4", "cnt_login_success": 0, "cnt_login_failed": 0, "has_pty": False, "cnt_client_version": 3, "v_full": 0},
    ]

    rules = evaluate_simple_rules(mock_records, budget=0.50)
    assert "R0_random" in rules
    assert "R1_login_success" in rules
    assert "R2_pty_requested" in rules
    assert "R6_failed_logins" in rules
    assert "R7_composite_tree" in rules

    # Both positive sessions (s1, s2) have login_success=1, so top 50% captures both
    assert rules["R1_login_success"] == 1.0


def test_paired_cluster_bootstrap_delta():
    """Verify paired cluster bootstrap computes difference and CI."""
    scores_ml = [0.9, 0.8, 0.1, 0.05]
    scores_rule = [0.1, 0.2, 0.8, 0.7]
    labels = [1, 1, 0, 0]
    clusters = ["ip_1", "ip_1", "ip_2", "ip_3"]

    delta, ci_low, ci_high = paired_cluster_bootstrap_delta(
        scores_ml=scores_ml,
        scores_rule=scores_rule,
        labels=labels,
        cluster_ids=clusters,
        budget=0.50,
        n_resamples=100,
        seed=42,
    )

    # ML has perfect recall at 50% (1.0), rule has 0.0, so delta = 1.0
    assert delta == 1.0
    assert ci_low <= delta <= ci_high


def test_evaluate_gate0_decision_rule_outcomes():
    """Verify exact EXPERIMENT0.md Section 12 Gate 0 decision rule logic."""
    # 1. PASS-ML: Stage S1-S3 improvement >= 0.05 and lower CI > 0
    res_pass = evaluate_gate0_decision_rule(
        delta_s1_s3=0.08,
        ci_lower_s1_s3=0.02,
        delta_s4_s5=0.10,
        ci_lower_s4_s5=0.05,
        threshold_delta=0.05,
    )
    assert res_pass["gate0_outcome"] == "PASS-ML"

    # 2. PASS-LATE-ONLY: S1-S3 fails, but S4-S5 >= 0.05 with lower CI > 0
    res_late = evaluate_gate0_decision_rule(
        delta_s1_s3=0.02,
        ci_lower_s1_s3=-0.01,
        delta_s4_s5=0.07,
        ci_lower_s4_s5=0.01,
        threshold_delta=0.05,
    )
    assert res_late["gate0_outcome"] == "PASS-LATE-ONLY"

    # 3. FAIL: Both fail to beat threshold with lower CI > 0
    res_fail = evaluate_gate0_decision_rule(
        delta_s1_s3=0.01,
        ci_lower_s1_s3=-0.03,
        delta_s4_s5=0.03,
        ci_lower_s4_s5=-0.02,
        threshold_delta=0.05,
    )
    assert res_fail["gate0_outcome"] == "FAIL"
