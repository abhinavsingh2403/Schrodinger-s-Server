"""Ensure S3 extraction stops at the first verified decision boundary."""
import pytest

from analysis.prefix_s3_eval import prefixes
from gatekeeper.features import stage_counters, stage_vector


def event(seq):
    return dict(session="masked",event="cowrie.session.params",seq=seq)


def marker(seq):
    features = stage_counters("S3",{"cnt_session_params":seq})
    return dict(session="masked",stage="S3",last_seq=seq,features=features,label=1)


def test_later_events_do_not_enter_first_prefix():
    first = marker(1)
    result = prefixes([event(1),first,event(2),marker(2)])
    assert result["masked"] == (stage_vector("S3",first["features"]),1)


def test_missing_event_and_stale_marker_rejected():
    with pytest.raises(ValueError,match="sequence"):
        prefixes([event(2)])
    with pytest.raises(ValueError,match="boundary"):
        prefixes([event(1),event(2),marker(1)])
