"""Unique-session budget invariants, persistence and monotone obligations."""
import sqlite3
from gatekeeper.decision_api import DecisionEngine


def test_exact_cap_duplicate_and_restart(tmp_path):
    db = tmp_path / 'budget.db'
    engine = DecisionEngine(db_path=db)
    for i in range(9):
        assert engine.decide(str(i), '127.0.0.1', 'S1')['tier'] == 'T1'
    kwargs = {'source_ip': '127.0.0.1', 'stage': 'S2', 'features': {'cnt_login_success': 1}}
    assert engine.decide('earned', **kwargs)['tier'] == 'T2'
    for _ in range(3):
        assert engine.decide('earned', **kwargs)['tier'] == 'T2'
    engine = DecisionEngine(db_path=db)
    assert engine.decide('over-cap', **kwargs)['tier'] == 'T1'
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT count(*),sum(tier>=2) FROM session_budget').fetchone() == (11, 1)


def test_no_warmup_and_memory_obligation(tmp_path):
    engine = DecisionEngine(db_path=tmp_path / 'budget.db')
    high = {'cnt_login_success': 1}
    assert engine.decide('first', '127.0.0.1', 'S2', high)['tier'] == 'T1'
    engine.record_session('127.0.0.2', tier_served='T2')
    assert engine.decide('returning', '127.0.0.2', 'S1')['tier'] == 'T2'
    assert engine.decide('fresh', '127.0.0.3', 'S2', high)['tier'] == 'T1'
    # Retries need not repeat the client's current_tier to preserve earned state.
    assert engine.decide('returning', '127.0.0.2', 'S1')['tier'] == 'T2'


def test_upgrade_migrates_existing_decisions(tmp_path):
    db = tmp_path / 'legacy.db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE decision_log(id INTEGER PRIMARY KEY, session_id TEXT, visitor_id TEXT, stage TEXT, score REAL, tier_decided TEXT, latency_ms REAL, timestamp TEXT)')
        conn.execute("INSERT INTO decision_log VALUES (1,'legacy','masked','S2',0.9,'T2',0,'lab')")
    engine = DecisionEngine(db_path=db)
    assert engine.decide('fresh', '127.0.0.1', 'S2', {'cnt_login_success': 1})['tier'] == 'T1'
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT tier FROM session_budget WHERE session_id='legacy'").fetchone() == (2,)


def test_concurrent_admission_cannot_overspend(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from gatekeeper.policy import SessionBudget
    budget = SessionBudget(tmp_path / 'concurrent.db')
    for i in range(19):
        budget.apply(str(i), 'T1', 'T1', 'T1', .1)
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda i: budget.apply(str(i), 'T2', 'T1', 'T1', .1), range(19, 24)))
    assert sum(tier == 'T2' for tier, _ in results) == 2
