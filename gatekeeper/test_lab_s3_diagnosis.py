"""Captured real live vectors must match offline inputs and frozen-model scores."""
from pathlib import Path
from gatekeeper.diagnose_lab_s3 import diagnose


def test_captured_s3_not_zero():
    result = diagnose(Path(__file__).resolve().parents[1])
    assert result['rows']
    assert all(not r['all_zero'] and not r['missing_fields'] for r in result['rows'])
    assert all(r['live_vector']==r['offline_vector'] for r in result['rows'])
