"""Guard generated dates, mirrored reports and explicit aggregate-proxy labelling."""
import csv
from datetime import datetime, timezone, timedelta
from analysis import exp0_train


def test_table_marks_proxy_without_changing_rule_identifier(tmp_path):
    path = tmp_path / 'table.csv'
    exp0_train.write_table_csv(path, [{'stage': 'S3', 'best_rule': 'R5_rarity', 'best_rule_test_recall': .25}])
    row = next(csv.DictReader(path.open()))
    assert row['best_rule'] == 'R5_rarity'
    assert row['best_rule_test_recall'] == '0.25'
    assert 'PROXY (aggregate counter, not version string)' in row['proxy_notice']


def test_report_date_uses_utc_timestamp_and_mirrors(tmp_path, monkeypatch):
    monkeypatch.setattr(exp0_train, 'PROJECT_ROOT', tmp_path)
    path = tmp_path / 'generated.md'
    timestamp = datetime(2030, 1, 2, 1, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    exp0_train.write_exp0_result_md(path, {'gate0_outcome': 'PASS-ML'}, [], {}, timestamp)
    assert '**Date**: 2030-01-01' in path.read_text()
    assert path.read_bytes() == (tmp_path / 'EXP0_RESULT.md').read_bytes()
