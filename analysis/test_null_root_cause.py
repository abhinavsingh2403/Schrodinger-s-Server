"""Check grouped diagnostics against the mechanical gate on small, repeated rows."""
from collections import Counter

import pytest

from analysis.exp0_rules import PurePythonLogisticRegression, recall_at_budget
from analysis.null_root_cause import fit_grouped, normalize, recall


def test_grouped_update_matches_gate_and_balances_classes():
    x = [[1], [1], [1], [3]]
    labels = [0, 0, 1, 1]
    model = PurePythonLogisticRegression(max_iter=5).fit(x, labels)
    bins = Counter((normalize(r, model), y) for r, y in zip(x, labels))
    weights, bias = fit_grouped(bins, model)
    assert weights == pytest.approx(model.weights)
    assert bias == pytest.approx(model.bias)
    # With one distinct row, balanced class weights cancel at probability one half.
    weights, bias = fit_grouped({((1.,), 0): 9, ((1.,), 1): 1}, model, balanced=True)
    assert weights == pytest.approx([0.])
    assert bias == pytest.approx(0.)


def test_grouped_recall_preserves_boundary_ties():
    bins = {((0,), 0): 9, ((1,), 0): 3, ((1,), 1): 8}
    assert recall(bins, lambda row: row[0]) == pytest.approx(
        recall_at_budget([0]*9 + [1]*11, [0]*12 + [1]*8, .1))
