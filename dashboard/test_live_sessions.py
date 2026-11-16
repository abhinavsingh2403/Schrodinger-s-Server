"""Session metrics derive from real engine rows and retain honest empty states."""
import sqlite3
import statistics
import pytest
from dashboard.app import DashboardServer
from gatekeeper.decision_api import DecisionEngine

@pytest.mark.parametrize('mode',[False,True])
def test_sessions_match_db(tmp_path,mode):
    db=tmp_path/'demo.db'
    engine=DecisionEngine(db_path=db,lab_mode=mode)
    engine.decide('first',stage='S1',provenance='LAB')
    engine.decide('first',stage='S3',features={'has_pty':1},provenance='LAB')
    engine.decide('return',stage='S1',provenance='LAB')
    server=DashboardServer(db_path=str(db),port=0)
    data=server.get_sessions_data()
    with sqlite3.connect(db) as c:
        count=c.execute('SELECT count(DISTINCT session_id) FROM decision_log').fetchone()[0]
        escalated=c.execute("SELECT count(DISTINCT session_id) FROM decision_log WHERE tier_decided IN ('T2','T3')").fetchone()[0]
        latencies=[round(r[0],2) for r in c.execute('SELECT latency_ms FROM decision_log')]
    assert data['kpis']=={'sessions':count,'reached_t2':escalated,'escalation_fraction':escalated/count,'median_compute_ms':statistics.median(latencies)}
    assert data['has_lab_demo'] is mode
    assert not data['sessions'][0]['returning_visitor']
    assert data['sessions'][1]['returning_visitor']
    assert bool(data['sessions'][0]['transitions']) is mode
    assert all('score_source' in d for s in data['sessions'] for d in s['decisions'])
    assert 'id="banner" hidden' in server.render_live_html()
    assert 'engine compute time' in server.render_live_html()

def test_empty_sessions(tmp_path):
    db=tmp_path/'empty.db'
    DecisionEngine(db_path=db)
    server=DashboardServer(db_path=str(db),port=0)
    data=server.get_sessions_data()
    assert data['sessions']==[] and not data['has_lab_demo']
    assert data['kpis']['sessions']==0
    assert data['kpis']['escalation_fraction'] is None
    assert data['kpis']['median_compute_ms'] is None
    assert 'NO DATA' in server.render_live_html()

def test_banner_includes_older_lab_rows(tmp_path):
    db=tmp_path/'mixed.db'
    DecisionEngine(db_path=db,lab_mode=True).decide('lab',provenance='LAB')
    engine=DecisionEngine(db_path=db)
    for i in range(55):
        engine.decide(str(i),provenance='SYNTHETIC')
    data=DashboardServer(db_path=str(db),port=0).get_sessions_data()
    assert data['has_lab_demo']
    assert data['source']=='MIXED'
    assert len(data['sessions'])==56
