"""Exercise the public API against the persisted SQLite column types."""
import sqlite3
from dashboard.app import DashboardServer, api_response


def test_timelines_and_summary(tmp_path):
    path = tmp_path / "decision.sqlite"
    server = DashboardServer(db_path=path)
    summary = "/api/decisions/summary"
    assert api_response(server, summary)[1]["data"] is None
    assert not path.exists()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE decision_log(id INTEGER, session_id, visitor_id, stage, tier_decided, score, score_source, latency_ms, timestamp, provenance, policy_profile)")
        db.executemany("INSERT INTO decision_log VALUES (?, 'private-session','private-visitor', ?, ?, 0.5, 'ml_model_s3', ?, '2026-01-01T12:00:00', 'LAB', 'LAB_DEMO')",
                       [(2,'S3','T2',3), (1,'S1','T1',None), (3,'S4','T2',1)])
    data = api_response(server, summary)[1]
    assert data["demo_label"] == "LAB_DEMO_NOT_ML"
    assert data["data"]["total_sessions"] == 1
    assert data["data"]["latency_ms"] == dict(min=1, median=2, p95=3, max=3)
    assert data["data"]["counts"]["tier"] == {"T1":1, "T2":2}
    sessions = api_response(server, "/api/sessions")[1]
    assert "private-" not in str(sessions)
    sid = sessions["sessions"][0]["session_id"]
    rows = api_response(server, "/api/session/" + sid)[1]["data"]["decisions"]
    assert [r["stage"] for r in rows] == ["S1","S3","S4"]
    assert rows[0]["latency_ms"] is None
    assert api_response(server, "/api/session/private-session")[0] == 404
