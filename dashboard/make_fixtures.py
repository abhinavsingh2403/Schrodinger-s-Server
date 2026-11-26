"""Generate offline examples via the same dispatcher as HTTP, with temporary lab decisions."""
import json
from pathlib import Path
import subprocess
import tempfile

from dashboard.app import DashboardServer, LEGACY, api_response
from dashboard.evidence import CATALOG, ROOT


def generate(directory):
    from gatekeeper.decision_api import DecisionEngine

    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    directory.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "demo.sqlite"
        server = DashboardServer(db_path=db)

        def save(name, route):
            code, payload = api_response(server, route)
            item = {"generated_by": "dashboard.make_fixtures", "generated_from_commit": revision,
                    "method": "GET", "route": route, "http_status": code, "response": payload}
            (directory / (name + ".json")).write_text(json.dumps(item, indent=2, allow_nan=False) + "\n", encoding="utf8")
            return payload

        save("empty_summary", "/api/decisions/summary")
        save("unknown_session", "/api/session/unknown")
        engine = DecisionEngine(db_path=db, lab_mode=True)
        engine.decide("fixture", stage="S1", provenance="LAB")
        engine.decide("fixture", stage="S3", features={"has_pty": 1}, provenance="LAB")
        for name in LEGACY:
            save(name, "/api/" + name)
        session = api_response(server, "/api/sessions")[1]["sessions"][0]["session_id"]
        save("session", "/api/session/" + session)
        save("summary", "/api/decisions/summary")
        save("progress", "/api/progress")
        save("index", "/api/evidence/index")
        for item in CATALOG:
            save("evidence_" + item, "/api/evidence/" + item)


if __name__ == "__main__":
    generate(Path(__file__).with_name("fixtures"))
