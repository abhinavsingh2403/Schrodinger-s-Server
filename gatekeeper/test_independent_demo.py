"""Independent demo storage preserves memory and fail-cheap contracts."""
from unittest.mock import patch

from gatekeeper.decision_api import DecisionEngine, GatekeeperClient


def test_independent_memory(tmp_path):
    old = DecisionEngine(db_path=tmp_path / 'old.db', salt=b'lab-test')
    old.memory.record_session('127.0.0.1', tier_served='T2')
    assert old.decide('remembered', source_ip='127.0.0.1', stage='S1')['tier'] == 'T2'
    fresh = DecisionEngine(db_path=tmp_path / 'fresh.db', salt=b'lab-test')
    assert fresh.decide('fresh', source_ip='127.0.0.1', stage='S1')['tier'] == 'T1'
    with patch('urllib.request.urlopen', side_effect=ConnectionRefusedError):
        result = GatekeeperClient().decide('down', stage='S1')
    assert result['tier'] == 'T1' and result['fail_cheap']
