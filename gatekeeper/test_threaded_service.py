"""Threaded HTTP admission keeps the cap, deduplicates sessions and survives restart."""
import concurrent.futures,http.server,sqlite3,threading
from gatekeeper.decision_api import DecisionEngine,GatekeeperClient,GatekeeperHTTPHandler

def test_threaded_budget_contract(tmp_path):
    db=tmp_path/'budget.db'
    engine=DecisionEngine(db_path=db)
    for i in range(19):engine.decide(str(i),stage='S1')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),GatekeeperHTTPHandler)
    server.decision_engine=engine
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    client=GatekeeperClient(base_url=f'http://127.0.0.1:{server.server_port}',timeout=5)
    try:
        def decide(i):return client.decide('same' if i<2 else str(i+19),stage='S2',features={'cnt_login_success':1})
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(decide,range(5)))
        assert all(not r['fail_cheap'] for r in rows)
    finally:server.shutdown();server.server_close();thread.join()
    with sqlite3.connect(db) as c:
        count,escalated=c.execute('SELECT count(*),sum(tier>=2) FROM session_budget').fetchone()
        assert c.execute("SELECT count(*) FROM session_budget WHERE session_id='same'").fetchone()[0]==1
        assert escalated<=int(.1*count)
    DecisionEngine(db_path=db)
    with sqlite3.connect(db) as c:assert c.execute('SELECT count(*),sum(tier>=2) FROM session_budget').fetchone()==(count,escalated)
