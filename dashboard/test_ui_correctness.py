"""Unit and contract tests for UI correctness, health checks, and data reality."""
import http.server
from io import BytesIO
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import threading
import time
import pytest
from dashboard.app import DashboardServer, make_dashboard_handler, probe_gatekeeper_health


def render_server_route(server: DashboardServer, path: str) -> tuple[int, str]:
    cls = make_dashboard_handler(server)
    req = object.__new__(cls)
    req.path = path
    req.wfile = BytesIO()
    status_codes = []
    req.send_response = status_codes.append
    req.send_header = lambda *_: None
    req.end_headers = lambda: None
    req.do_GET()
    return status_codes[0], req.wfile.getvalue().decode("utf-8")


def test_cowrie_is_never_reported_as_online():
    """Requirement 1 & 2: Cowrie status must be NOT CHECKED, never statically ONLINE or ACTIVE."""
    server = DashboardServer()
    for route in ["/", "/lab"]:
        code, html = render_server_route(server, route)
        assert code == 200
        # Must not claim Cowrie is online/active
        assert "Cowrie Sensor</span></td><td>SSH deception listener & telemetry extractor</td><td>Port 2222 (Loopback strictly)</td><td><span class=\"badge done\">ONLINE / ACTIVE" not in html
        assert "Port 2222 (Cowrie Listener)" not in html
        # Must clearly designate as NOT CHECKED or Configured
        if route == "/":
            assert "Port 2222 (Configured · NOT CHECKED)" in html
        elif route == "/lab":
            assert "NOT CHECKED (SSH protocol requires probe)" in html


def test_unknown_policy_fallback_in_templates():
    """Requirement 3: Fallback for missing policy profile must be UNKNOWN, not LAB_DEMO."""
    templates_dir = Path(__file__).parent / "templates"
    for tmpl_name in ["live.html", "page_shell.html"]:
        content = (templates_dir / tmpl_name).read_text(encoding="utf-8")
        # Ensure no fallback defaults to LAB_DEMO when profile is missing
        assert "meta.policy_profile || 'LAB_DEMO'" not in content
        assert "dec.policy_profile || 'LAB_DEMO'" not in content


def test_unobserved_stages_visually_absent():
    """Requirement 6: Missing decisions (e.g. S5) must remain visually absent from trajectories."""
    tmpl = (Path(__file__).parent / "templates" / "live.html").read_text(encoding="utf-8")
    # Must not loop over hardcoded S1..S5 rendering dashes with arrows to missing stages
    assert "for (let i = 0; i < stages.length; i++) {" not in tmpl
    assert "const observedEntries = Object.entries(session.stages)" in tmpl


def test_empty_database_behavior():
    """Requirement 8: UI and API behavior with an empty database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        empty_db_path = tf.name

    try:
        conn = sqlite3.connect(empty_db_path)
        conn.execute("""
            CREATE TABLE decision_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                score REAL NOT NULL,
                tier_decided TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                timestamp TEXT NOT NULL,
                provenance TEXT NOT NULL DEFAULT 'UNKNOWN',
                policy_profile TEXT NOT NULL DEFAULT 'UNKNOWN',
                score_source TEXT NOT NULL DEFAULT 'UNKNOWN'
            )
        """)
        conn.commit()
        conn.close()

        server = DashboardServer(db_path=empty_db_path)

        # 1. /api/sessions returns empty sessions array and 0 KPIs
        code, body = render_server_route(server, "/api/sessions")
        assert code == 200
        data = json.loads(body)
        assert data["sessions"] == []
        assert data["kpis"]["sessions"] == 0
        assert data["kpis"]["reached_t2"] == 0

        # 2. Mission Control renders clean empty state without crashing
        code, html = render_server_route(server, "/")
        assert code == 200
        assert "Mission Control" in html
        assert "Port 2222 (Configured · NOT CHECKED)" in html

        # 3. Lab console renders cleanly
        code, lab_html = render_server_route(server, "/lab")
        assert code == 200
        assert "NOT CHECKED (SSH protocol requires probe)" in lab_html
    finally:
        Path(empty_db_path).unlink(missing_ok=True)


def test_populated_database_and_verified_transition():
    """Requirement 4, 8 & 9: Verify populated database and authentic mid-session tier transition."""
    db_path = Path(__file__).resolve().parent.parent / "gatekeeper" / "gatekeeper.db"
    if not db_path.is_file():
        pytest.skip("gatekeeper.db not present in repo")

    server = DashboardServer(db_path=str(db_path))
    code, body = render_server_route(server, "/api/sessions")
    assert code == 200
    data = json.loads(body)
    assert len(data["sessions"]) > 0

    # Test verified session with authentic S1:T1 -> S2:T1 -> S3:T2 progression
    # ses_7f97ea60331c09294dac4e06 corresponds to ses_test_escalation_verify
    code, sess_body = render_server_route(server, "/api/session/ses_7f97ea60331c09294dac4e06")
    assert code == 200
    sess_data = json.loads(sess_body)
    decisions = sess_data.get("data", {}).get("decisions", [])
    assert len(decisions) >= 3

    # Assert consecutive stages and tier transition
    d_s1 = next(d for d in decisions if d["stage"] == "S1")
    d_s2 = next(d for d in decisions if d["stage"] == "S2")
    d_s3 = next(d for d in decisions if d["stage"] == "S3")

    assert d_s1["tier_decided"] == "T1"
    assert d_s2["tier_decided"] == "T1"
    assert d_s3["tier_decided"] == "T2"
    assert d_s3["score"] == 1.0
    assert d_s3["score_source"] == "lab_pty_mechanism"
    # Stage S3 timestamp must be after Stage S2 timestamp
    assert d_s3["timestamp"] >= d_s2["timestamp"]


class _MockHealthHandler(http.server.BaseHTTPRequestHandler):
    mode = "healthy"

    def do_GET(self):
        if self.path == "/health":
            if self.mode == "healthy":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "service": "gatekeeper", "version": "1.0.0"}).encode())
            elif self.mode == "malformed":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "corrupt_data"}')
            elif self.mode == "invalid_json":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"NOT_JSON")
            elif self.mode == "timeout":
                time.sleep(0.5)
                self.send_response(200)
                self.end_headers()
            elif self.mode == "500":
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


def test_gatekeeper_health_healthy_scenario():
    """Requirement 2 & 4: Probing healthy Gatekeeper returns ONLINE."""
    server = http.server.HTTPServer(("127.0.0.1", 0), _MockHealthHandler)
    port = server.server_address[1]
    _MockHealthHandler.mode = "healthy"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        res = probe_gatekeeper_health(port=port, timeout=1.0)
        assert res["status"] == "ONLINE"
        assert res["service"] == "gatekeeper"
        assert res["version"] == "1.0.0"
        assert res["port"] == port
    finally:
        server.shutdown()
        server.server_close()


def test_gatekeeper_health_stopped_scenario():
    """Requirement 4: Probing stopped Gatekeeper service returns UNAVAILABLE."""
    # Find a free port that is guaranteed not listening
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]
    res = probe_gatekeeper_health(port=free_port, timeout=0.2)
    assert res["status"] == "UNAVAILABLE"
    assert "Connection failed" in res["error"] or "refused" in res["error"] or "timed out" in res["error"]


def test_gatekeeper_health_malformed_scenario():
    """Requirement 4: Malformed responses or missing status='ok' return UNAVAILABLE."""
    server = http.server.HTTPServer(("127.0.0.1", 0), _MockHealthHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        # 1. Missing status=ok
        _MockHealthHandler.mode = "malformed"
        res1 = probe_gatekeeper_health(port=port, timeout=1.0)
        assert res1["status"] == "UNAVAILABLE"
        assert "Malformed" in res1["error"]

        # 2. Invalid non-JSON payload
        _MockHealthHandler.mode = "invalid_json"
        res2 = probe_gatekeeper_health(port=port, timeout=1.0)
        assert res2["status"] == "UNAVAILABLE"

        # 3. HTTP 500 status
        _MockHealthHandler.mode = "500"
        res3 = probe_gatekeeper_health(port=port, timeout=1.0)
        assert res3["status"] == "UNAVAILABLE"
        assert "500" in res3["error"]
    finally:
        server.shutdown()
        server.server_close()


def test_gatekeeper_health_timeout_scenario():
    """Requirement 4: Slow responding service exceeding timeout returns UNAVAILABLE."""
    server = http.server.HTTPServer(("127.0.0.1", 0), _MockHealthHandler)
    port = server.server_address[1]
    _MockHealthHandler.mode = "timeout"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        res = probe_gatekeeper_health(port=port, timeout=0.08)
        assert res["status"] == "UNAVAILABLE"
        assert "timed out" in res["error"].lower()
    finally:
        server.shutdown()
        server.server_close()


def test_gatekeeper_health_forbidden_external_host():
    """Requirement 3: Never accept an arbitrary user-supplied health-check URL."""
    res1 = probe_gatekeeper_health(host="192.168.1.100")
    assert res1["status"] == "UNKNOWN"
    assert "forbidden" in res1["error"].lower()

    res2 = probe_gatekeeper_health(host="attacker.com")
    assert res2["status"] == "UNKNOWN"
    assert "forbidden" in res2["error"].lower()


def test_gatekeeper_health_dashboard_api_endpoint():
    """Requirement 2: Same-origin dashboard endpoint /api/gatekeeper/health."""
    server = DashboardServer()
    for endpoint in ["/api/gatekeeper/health", "/api/health/gatekeeper"]:
        code, body = render_server_route(server, endpoint)
        assert code == 200
        data = json.loads(body)
        assert "status" in data
        assert data["status"] in ("ONLINE", "UNAVAILABLE", "UNKNOWN")

