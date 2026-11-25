"""Verify boundary ties, auth retries and already-determined outcomes on a tiny cohort."""
import duckdb

from analysis.experiment1_feasibility import boundaries


def test_only_untied_complete_future_risk_sessions_count():
    with duckdb.connect() as db:
        db.execute("CREATE TABLE events(sensor VARCHAR,session VARCHAR,ts TIMESTAMP,"
                   "eventid VARCHAR,command_hash VARCHAR)")
        events = [(0, "session.connect"), (1, "login.failed"), (2, "login.success"),
                  (3, "command.input"), (3, "client.var"), (4, "session.file_upload"),
                  (5, "command.input"), (6, "command.input"), (7, "session.closed")]
        for stamp, event in events:
            db.execute("INSERT INTO events VALUES ('lab','session',?,?,?)",
                       [f"2025-01-01 00:00:0{stamp}", "cowrie."+event,
                        "repeat" if event == "command.input" else None])
        rows = boundaries(db)
    assert rows["S2"] == dict(reached=1, tied=0, eligible=1, future=1)
    assert rows["S4"] == dict(reached=1, tied=1, eligible=0, future=0)
    assert rows["S5"] == dict(reached=1, tied=0, eligible=0, future=0)
