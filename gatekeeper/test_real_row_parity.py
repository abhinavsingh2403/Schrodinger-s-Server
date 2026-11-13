"""Real aggregate rows replay equivalent counter events, without claiming chronology."""
import gzip
import itertools
import json
from pathlib import Path
import pytest
from gatekeeper.feature_extractor import SessionFeatureExtractor
from analysis.exp0_train import STAGE_ALLOWED_FEATURES
from gatekeeper.features import stage_vector


def test_real_rows_match_every_stage_counter():
    path = Path(__file__).resolve().parents[1] / 'data/session_aggregation.jsonl.gz'
    if not path.exists():
        pytest.skip('Real session_aggregation.jsonl.gz is absent; real-row parity NOT VERIFIED')
    with gzip.open(path, 'rt', encoding='utf-8') as source:
        rows = [json.loads(line) for line in itertools.islice(source, 100)]
    assert len(rows) == 100
    for row in rows:
        live = SessionFeatureExtractor()
        for name in STAGE_ALLOWED_FEATURES['S3']:
            eventid = 'cowrie.' + name.removeprefix('cnt_').replace('_', '.')
            for _ in range(int(row.get(name, 0) or 0)):
                live.ingest_event({'eventid': eventid})
        for stage in ('S1', 'S2', 'S3'):
            features = live.extract_stage_features(stage)
            expected = [float(row.get(f, 0) or 0) for f in STAGE_ALLOWED_FEATURES[stage]]
            assert stage_vector(stage, row) == expected
            assert [features[f] for f in STAGE_ALLOWED_FEATURES[stage]] == expected


def test_no_inferred_counts_or_future_fingerprint():
    live = SessionFeatureExtractor()
    live.ingest_event({'eventid': 'cowrie.client.kex', 'hassh': 'lab'})
    assert 'cnt_client_fingerprint' not in live.extract_stage_features('S1')
    assert live.extract_stage_features('S2')['cnt_client_fingerprint'] == 0
    assert live.extract_stage_features('S1')['cnt_session_connect'] == 0
    for _ in range(2):
        live.ingest_event({'eventid': 'cowrie.login.success'})
    assert live.extract_stage_features('S2')['cnt_login_success'] == 2
