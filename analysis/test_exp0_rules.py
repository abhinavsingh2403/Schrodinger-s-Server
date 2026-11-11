"""
Unit tests for Experiment 0 baseline rules and budget recall evaluation.
"""

from __future__ import annotations

import pytest

from analysis.exp0_rules import (
    recall_at_budget,
    score_r0_random,
    score_r1_login_success,
    score_r2_pty_requested,
    score_r5_rarity,
    score_r6_failed_logins,
)


def test_recall_at_budget_perfect_selection() -> None:
    # 10 sessions, 2 positives at index 0 and 1
    scores = [10.0, 9.0, 1.0, 1.0, 0.5, 0.2, 0.1, 0.0, 0.0, 0.0]
    labels = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]

    # At 20% budget (top 2 sessions), recall should be 1.0
    rec_20 = recall_at_budget(scores, labels, budget=0.20)
    assert rec_20 == 1.0

    # At 10% budget (top 1 session), recall should be 0.5 (1/2)
    rec_10 = recall_at_budget(scores, labels, budget=0.10)
    assert rec_10 == 0.5


def test_recall_at_budget_zero_positives() -> None:
    scores = [1.0, 2.0, 3.0]
    labels = [0, 0, 0]
    assert recall_at_budget(scores, labels, budget=0.5) == 0.0


def test_r0_random_bounds_and_determinism() -> None:
    s1 = score_r0_random(100, seed=42)
    s2 = score_r0_random(100, seed=42)
    s3 = score_r0_random(100, seed=99)

    assert len(s1) == 100
    assert all(0.0 <= x <= 1.0 for x in s1)
    assert s1 == s2
    assert s1 != s3


def test_r1_login_success() -> None:
    scores = score_r1_login_success([0, 1, 3, 0])
    assert scores == [0.0, 1.0, 1.0, 0.0]


def test_r2_pty_requested() -> None:
    scores = score_r2_pty_requested([False, True, True, False])
    assert scores == [0.0, 1.0, 1.0, 0.0]


def test_r5_rarity() -> None:
    train_counts = {"common": 1000, "rare": 2}
    scores = score_r5_rarity(["common", "rare"], train_counts, total_train=1002)
    # Rare should have higher score (negative log frequency)
    assert scores[1] > scores[0]


def test_r6_failed_logins() -> None:
    scores_pos = score_r6_failed_logins([0, 2, 5], sign=1)
    scores_neg = score_r6_failed_logins([0, 2, 5], sign=-1)

    assert scores_pos == [0.0, 2.0, 5.0]
    assert scores_neg == [0.0, -2.0, -5.0]


def test_r3_interactive_and_r4_timing() -> None:
    from analysis.exp0_rules import score_r3_interactive, score_r4_timing_delay
    assert score_r3_interactive([True, False, True]) == [1.0, 0.0, 1.0]
    assert score_r4_timing_delay([0.5, 2.0, -1.0], sign=1) == [0.5, 2.0, 0.0]
    assert score_r4_timing_delay([0.5, 2.0], sign=-1) == [-0.5, -2.0]


def test_r7_pure_python_decision_tree() -> None:
    from analysis.exp0_rules import train_r7_decision_tree
    # Simple XOR-like or split problem
    # Feature 0: login_success, Feature 1: has_pty
    X_train = [
        [1.0, 1.0],
        [1.0, 0.0],
        [0.0, 1.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [1.0, 1.0],
    ]
    y_train = [1, 1, 0, 0, 0, 1]

    tree = train_r7_decision_tree(X_train, y_train, max_depth=3)
    preds = tree.predict_proba([[1.0, 1.0], [0.0, 0.0]])
    assert len(preds) == 2
    # Probability for [1, 1] should be higher than [0, 0]
    assert preds[0] > preds[1]
