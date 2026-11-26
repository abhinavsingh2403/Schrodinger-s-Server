"""Guard public explanations against the recorded implementation and report."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_template_claims():
    templates = ROOT / "dashboard/templates"
    text = "\n".join(p.read_text(encoding="utf-8-sig") for p in templates.glob("*.html"))
    for claim in ("Decision Tree Model", "temporal leakage", "fail to reject", "Mandatory Scientific Finding"):
        assert claim not in text
    shell = (templates / "page_shell.html").read_text(encoding="utf8")
    body = shell.split("const RULE_EXPLANATIONS = {")[1].split("};")[0]
    engine = (ROOT / "gatekeeper/decision_api.py").read_text(encoding="utf8")
    for key in re.findall(r"'(\w+)':", body):
        assert key in engine
    outside = re.sub(r"const statusClass = .*?\n};", "", shell, flags=re.S)
    assert not re.search(r"['\x22](INVALID|INCONCLUSIVE|CONFIRMED|REJECTED)['\x22]", outside)

def test_configured_health_target(monkeypatch):
    from dashboard import app
    server = app.DashboardServer(gatekeeper_port=12345)
    def probe(host, port):
        assert (host, port) == ("127.0.0.1", 12345)
        return {"status": "UNAVAILABLE"}
    monkeypatch.setattr(app, "probe_gatekeeper_health", probe)
    assert app.api_response(server, "/api/gatekeeper/health")[1]["metadata"]["status"] == "INCONCLUSIVE"
