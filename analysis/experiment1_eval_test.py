"""Check that validity and minimum size take precedence over a positive interval."""
from analysis.experiment1_eval import verdict


def test_decision_rule():
    assert verdict(.15,501,.09,.01)=='INVALID'
    assert verdict(.12,499,.09,.01)=='INCONCLUSIVE'
    assert verdict(.08,500,.05,.01)=='CONFIRMED'
    assert verdict(.10,500,.05,0)=='REJECTED'
