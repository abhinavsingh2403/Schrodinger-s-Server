"""Policy profile survives migration and cannot be forged through provenance."""
import sqlite3
import pytest
from gatekeeper.decision_api import DecisionEngine


@pytest.mark.parametrize('lab,profile', [(False,'DEFAULT'), (True,'LAB_DEMO')])
def test_profile(tmp_path, lab, profile):
    db = tmp_path / 'profile.db'
    engine = DecisionEngine(db_path=db, lab_mode=lab)
    result = engine.decide('session', provenance='LIVE')
    assert result['policy_profile'] == profile
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT policy_profile FROM decision_log').fetchone()[0] == profile
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE decision_log SET policy_profile='FAKE'")


def test_migration(tmp_path):
    db = tmp_path / 'legacy.db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE decision_log(id INTEGER PRIMARY KEY,session_id TEXT,visitor_id TEXT,stage TEXT,score REAL,tier_decided TEXT,latency_ms REAL,timestamp TEXT)')
        conn.execute("INSERT INTO decision_log VALUES(1,'old','masked','S1',0,'T1',0,'historical')")
    DecisionEngine(db_path=db)
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT policy_profile FROM decision_log').fetchone()[0] == 'UNKNOWN'
