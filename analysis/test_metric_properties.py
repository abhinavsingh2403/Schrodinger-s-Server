"""Distribution and budget invariants independent of the experiment outcome."""
import random
import statistics
from analysis.exp0_rules import recall_at_budget


def test_equal_scores_average_is_budget():
    labels = [1]*100 + [0]*900
    mean = statistics.mean(recall_at_budget([0.0]*1000,labels,.1,seed=s) for s in range(300))
    assert abs(mean-.1)<.015


def test_random_scores_average_is_budget():
    labels = [1]*100 + [0]*900
    values=[]
    for seed in range(300):
        rng=random.Random(seed)
        values.append(recall_at_budget([rng.random() for _ in labels],labels,.1))
    assert abs(statistics.mean(values)-.1)<.015


def test_perfect_separation_and_exact_budget():
    labels=[1]*100+[0]*900
    assert recall_at_budget(labels,labels,.1)==1
    assert recall_at_budget([0]*1000,[1]*1000,.1)==.1


def test_metrics_at_budget_invariants():
    from analysis.exp0_rules import metrics_at_budget

    labels = [1] * 100 + [0] * 900
    scores = [1.0] * 100 + [0.0] * 900  # Perfect separation

    for budget in [0.01, 0.05, 0.10, 0.20]:
        res = metrics_at_budget(scores, labels, budget)
        cm = res["confusion_matrix"]

        # Invariant 1: Total selected == TP + FP
        assert cm["TP"] + cm["FP"] == res["selected_sessions"]

        # Invariant 2: Total positives == TP + FN
        assert cm["TP"] + cm["FN"] == 100

        # Invariant 3: Total negatives == FP + TN
        assert cm["FP"] + cm["TN"] == 900

        # Invariant 4: Precision, Recall, F1 bounds
        assert 0.0 <= res["precision"] <= 1.0
        assert 0.0 <= res["recall"] <= 1.0
        assert 0.0 <= res["f1_score"] <= 1.0
        assert 0.0 <= res["fpr"] <= 1.0

    # At 10% budget with perfect separation and 10% prevalence:
    res10 = metrics_at_budget(scores, labels, 0.10)
    assert res10["precision"] == 1.0
    assert res10["recall"] == 1.0
    assert res10["f1_score"] == 1.0
    assert res10["fpr"] == 0.0
    assert res10["confusion_matrix"] == {"TP": 100.0, "FP": 0.0, "FN": 0.0, "TN": 900.0}


def test_metrics_at_budget_edge_cases():
    import pytest
    from analysis.exp0_rules import metrics_at_budget

    # Mismatched lengths
    with pytest.raises(ValueError):
        metrics_at_budget([0.5, 0.2], [1], 0.10)

    # Empty inputs
    with pytest.raises(ValueError):
        metrics_at_budget([], [], 0.10)

    # Invalid budgets
    with pytest.raises(ValueError):
        metrics_at_budget([0.5], [1], 0.0)
    with pytest.raises(ValueError):
        metrics_at_budget([0.5], [1], 1.5)

    # All negatives
    all_neg = metrics_at_budget([0.9, 0.1], [0, 0], 0.50)
    assert all_neg["recall"] == 0.0
    assert all_neg["precision"] == 0.0
    assert all_neg["f1_score"] == 0.0

    # Budget 1.0 (100% selection)
    labels = [1] * 20 + [0] * 80
    scores = [float(i) for i in range(100)]
    full = metrics_at_budget(scores, labels, 1.0)
    assert full["recall"] == 1.0
    assert full["fpr"] == 1.0
    assert full["confusion_matrix"]["FN"] == 0.0
    assert full["confusion_matrix"]["TN"] == 0.0


def test_pr_auc_properties():
    from analysis.exp0_rules import pr_auc_score

    # Perfect ranking
    labels = [1] * 50 + [0] * 950
    scores_perfect = [1.0] * 50 + [0.0] * 950
    assert pr_auc_score(scores_perfect, labels) == 1.0

    # Inverted ranking (worst possible)
    scores_worst = [0.0] * 50 + [1.0] * 950
    auc_worst = pr_auc_score(scores_worst, labels)
    assert auc_worst < 0.10

    # Edge cases
    assert pr_auc_score([0.5] * 10, [0] * 10) == 0.0
    assert pr_auc_score([0.5] * 10, [1] * 10) == 1.0


def test_evaluate_escalation_budgets():
    from analysis.exp0_rules import evaluate_escalation_budgets

    labels = [1] * 50 + [0] * 950
    scores = [1.0] * 50 + [0.0] * 950
    eval_res = evaluate_escalation_budgets(scores, labels, [0.01, 0.05, 0.10, 0.20])

    assert "budgets" in eval_res
    assert "pr_auc" in eval_res
    assert eval_res["pr_auc"] == 1.0
    for b in ["1%", "5%", "10%", "20%"]:
        assert b in eval_res["budgets"]
        assert "recall" in eval_res["budgets"][b]
        assert "precision" in eval_res["budgets"][b]
        assert "f1_score" in eval_res["budgets"][b]
        assert "fpr" in eval_res["budgets"][b]
        assert "confusion_matrix" in eval_res["budgets"][b]
