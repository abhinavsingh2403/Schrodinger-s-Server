"""Check cutoff ties and rank equivalence on small, explicit examples."""
from analysis.experiment1_root_cause import inclusion, ranking


def test_distinct_rankings_can_have_identical_cutoff_weights():
    left, right = [5,4,4,1,0], [8,6,6,0,1]
    assert ranking(left) != ranking(right)
    assert inclusion(left,.4) == inclusion(right,.4) == [1,.5,.5,0,0]
