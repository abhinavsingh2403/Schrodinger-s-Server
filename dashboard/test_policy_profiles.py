"""Profile display stays independent of provenance and preserves legacy records."""
import sqlite3
import pytest
from dashboard.app import DashboardServer
from gatekeeper.decision_api import DecisionEngine


@pytest.mark.parametrize('modes,expected', [([False],'DEFAULT'),([True],'LAB_DEMO'),([False,True],'MIXED')])
def test_profile_aggregation(tmp_path, modes, expected):
    db = tmp_path/'decisions.db'
    for i, mode in enumerate(modes):
        DecisionEngine(db_path=db, lab_mode=mode).decide(str(i), provenance='LAB')
    server = DashboardServer(db_path=str(db), port=0)
    result = server.get_decisions_data()
    assert result['policy_profile'] == expected
    assert server.get_stats_data()['sensor']['policy_profile'] == expected
    assert result['source'] == 'LAB'
    assert {r['policy_profile'] for r in result['decisions']} == {'LAB_DEMO' if m else 'DEFAULT' for m in modes}


@pytest.mark.parametrize('profile', [None, 'INVALID', 'UNKNOWN'])
def test_legacy_and_invalid_profiles(tmp_path, profile):
    db = tmp_path/'legacy.db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE decision_log(id INTEGER,session_id TEXT,visitor_id TEXT,stage TEXT,score REAL,tier_decided TEXT,latency_ms REAL,timestamp TEXT,provenance TEXT)')
        conn.execute("INSERT INTO decision_log VALUES(1,'legacy','vis_masked','S1',0,'T1',0,'test','LAB')")
        if profile is not None:
            conn.execute('ALTER TABLE decision_log ADD COLUMN policy_profile TEXT')
            conn.execute('UPDATE decision_log SET policy_profile=?',(profile,))
    server = DashboardServer(db_path=str(db), port=0)
    assert server.get_decisions_data()['decisions'][0]['policy_profile'] == 'UNKNOWN'
    assert server.get_stats_data()['sensor']['total_decisions'] == 1
    assert server.get_stats_data()['sensor']['policy_profile'] == 'UNKNOWN'


def test_missing_database_profile(tmp_path):
    server = DashboardServer(db_path=str(tmp_path/'missing.db'), port=0)
    assert server.get_decisions_data()['policy_profile'] == 'UNKNOWN'


def test_known_and_unknown_are_mixed_and_limit_is_respected(tmp_path):
    db = tmp_path/'mixed.db'
    engine = DecisionEngine(db_path=db)
    engine.decide('old', provenance='LAB')
    engine.decide('new', provenance='LAB')
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE decision_log SET policy_profile='UNKNOWN' WHERE session_id='old'")
    server = DashboardServer(db_path=str(db), port=0)
    assert server.get_stats_data()['sensor']['policy_profile'] == 'MIXED'
    assert server.get_decisions_data()['policy_profile'] == 'MIXED'
    assert server.get_decisions_data(limit=1)['policy_profile'] == 'DEFAULT'
