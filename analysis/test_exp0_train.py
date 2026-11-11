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


def test_stage_valid_rules_filtering():
    """Verify rules valid at each stage adhere to EXPERIMENT0.md §7."""
    mock_records = [
        {"session": "s1", "cnt_login_success": 1, "cnt_login_failed": 0, "has_pty": True, "cnt_client_version": 1, "duration": 5.0, "v_full": 1},
        {"session": "s2", "cnt_login_success": 0, "cnt_login_failed": 2, "has_pty": False, "cnt_client_version": 2, "duration": 1.0, "v_full": 0},
    ]
    # S1 only permits R0 and R5 (no R1, R2, R4, R6, R7)
    from analysis.exp0_train import evaluate_stage_rules
    best_rule, score, valid_scores = evaluate_stage_rules("S1", mock_records, train_records=mock_records, budget=0.50)
    assert "R0_random" in valid_scores
    assert "R5_rarity" in valid_scores
    assert "R1_login_success" not in valid_scores
    assert "R2_pty_requested" not in valid_scores

    # S2 permits R1, R6, R7 in addition to R0, R5
    best_rule_s2, _, valid_scores_s2 = evaluate_stage_rules("S2", mock_records, train_records=mock_records, budget=0.50)
    assert "R1_login_success" in valid_scores_s2
    assert "R6_failed_logins" in valid_scores_s2
    assert "R7_decision_tree" in valid_scores_s2
    assert "R2_pty_requested" not in valid_scores_s2


def test_filter_prefix_determined_exclusions():
    """Verify reach criteria and prefix-determined exclusion per EXPERIMENT0.md §5."""
    from analysis.exp0_train import filter_prefix_determined_exclusions

    records = [
        # Session 1: reaches S1, S2, S3, S4; download on cmd1 (should be dropped at S4)
        {"session": "s1", "cnt_login_success": 1, "cnt_command_input": 2, "cnt_file_download": 1, "v_full": 1},
        # Session 2: reaches S1, S2, S3, S4; normal command without download/pivot
        {"session": "s2", "cnt_login_success": 1, "cnt_command_input": 1, "cnt_file_download": 0, "v_full": 0},
        # Session 3: connection only (fails at auth), reaches S1 only
        {"session": "s3", "cnt_login_success": 0, "cnt_login_failed": 0, "cnt_command_input": 0, "v_full": 0},
    ]

    # S1: all 3 reach, 0 dropped
    s1_reached, s1_stats = filter_prefix_determined_exclusions(records, stage="S1")
    assert len(s1_reached) == 3
    assert s1_stats["dropped_prefix_count"] == 0

    # S4: only s1 and s2 reach (cmds >= 1), s1 dropped because file download > 0
    s4_reached, s4_stats = filter_prefix_determined_exclusions(records, stage="S4")
    assert len(s4_reached) == 1
    assert s4_reached[0]["session"] == "s2"
    assert s4_stats["dropped_prefix_count"] == 1


def test_evaluate_gate0_decision_rule_stage_results():
    """Verify Gate 0 logic when evaluating full dictionary of stage results."""
    # 1. Early stage S2 achieves delta >= 0.05, lower CI > 0, min-size met -> PASS-ML
    stage_results_early = {
        "S1": {"delta": 0.02, "ci_lower": -0.01, "min_size_met": True},
        "S2": {"delta": 0.07, "ci_lower": 0.02, "min_size_met": True},
        "S3": {"delta": 0.04, "ci_lower": 0.00, "min_size_met": True},
        "S4": {"delta": 0.08, "ci_lower": 0.03, "min_size_met": True},
        "S5": {"delta": 0.10, "ci_lower": 0.05, "min_size_met": True},
    }
    res_early = evaluate_gate0_decision_rule(stage_results=stage_results_early)
    assert res_early["gate0_outcome"] == "PASS-ML"
    assert "S2" in res_early["passing_early_stages"]

    # 2. Early stages fail, but S4 meets criteria -> PASS-LATE-ONLY
    stage_results_late = {
        "S1": {"delta": 0.01, "ci_lower": -0.02, "min_size_met": True},
        "S2": {"delta": 0.02, "ci_lower": -0.01, "min_size_met": True},
        "S3": {"delta": 0.03, "ci_lower": -0.01, "min_size_met": True},
        "S4": {"delta": 0.06, "ci_lower": 0.01, "min_size_met": True},
        "S5": {"delta": 0.04, "ci_lower": -0.01, "min_size_met": True},
    }
    res_late = evaluate_gate0_decision_rule(stage_results=stage_results_late)
    assert res_late["gate0_outcome"] == "PASS-LATE-ONLY"
    assert "S4" in res_late["passing_late_stages"]

    # 3. All stages pending ML training
    stage_results_pending = {
        "S1": {"delta": None, "ci_lower": None, "min_size_met": True, "ml_status": "PENDING"},
        "S2": {"delta": None, "ci_lower": None, "min_size_met": True, "ml_status": "PENDING"},
        "S3": {"delta": None, "ci_lower": None, "min_size_met": True, "ml_status": "PENDING"},
        "S4": {"delta": None, "ci_lower": None, "min_size_met": True, "ml_status": "PENDING"},
        "S5": {"delta": None, "ci_lower": None, "min_size_met": True, "ml_status": "PENDING"},
    }
    res_pending = evaluate_gate0_decision_rule(stage_results=stage_results_pending)
    assert res_pending["gate0_outcome"] == "PENDING_ML_TRAINING"


def test_load_hyperparameter_grid(tmp_path):
    """Verify loading and validating grid.json."""
    from analysis.exp0_train import load_hyperparameter_grid
    grid_file = tmp_path / "grid.json"
    grid_file.write_text('{"logistic_regression": {"C": [1.0]}, "hist_gradient_boosting": {"learning_rate": [0.1]}}')
    loaded = load_hyperparameter_grid(grid_file)
    assert "logistic_regression" in loaded
    assert "hist_gradient_boosting" in loaded
