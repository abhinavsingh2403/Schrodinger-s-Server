"""Check that cost purity uses the last decision of each session."""
from analysis.tier_cost_study import summarize


def test_final_tiers_and_interleaved_intervals():
    rows=[("a","S1","T1","2020-01-01T00:00:00"),("b","S1","T2","2020-01-01T00:00:01"),
          ("a","S3","T2","2020-01-01T00:00:02"),("b","S3","T2","2020-01-01T00:00:05")]
    result=summarize(rows)
    assert result["final_tiers"]=={"T2":2}
    assert result["decision_fraction"]["T1"]==.25
    assert result["observed_time_fraction"]["T1"]==2/6
