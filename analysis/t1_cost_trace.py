"""Observe the original cost workload against a fresh, loopback-only DEFAULT stack."""
import json
import os
import subprocess
import time
import tempfile
from pathlib import Path
from unittest.mock import patch

from analysis.tier_cost_study import COMPOSE
from harness.attackers import bot_like

QUERY = """select session_id,stage,tier_decided,score_source,policy_profile,score,
visitor_id from decision_log order by rowid"""


def trace(compose):
    call = bot_like.execute_ssh_command
    observations = []
    seen = set()

    def observe(*args, **kwargs):
        result = call(*args, **kwargs)
        code = ("import sqlite3,json; print(json.dumps(sqlite3.connect("
                "'/app/data/gatekeeper.db').execute(" + repr(QUERY) + ").fetchall()))")
        rows = json.loads(subprocess.check_output(compose + ["exec", "-T", "gatekeeper",
                                                             "python", "-c", code]))
        new = [row for row in rows if row[0] not in seen]
        seen.update(row[0] for row in new)
        observations.append(dict(invocation=len(observations)+1, command=kwargs["command"],
                                 pty=kwargs.get("allocate_pty", False),
                                 rows=[row[:6] for row in new],
                                 distinct_visitors=len({row[6] for row in rows})))
        return result

    subprocess.run(compose + ["down", "-v"], check=True)
    try:
        subprocess.run(compose + ["up", "-d", "--build"], check=True,
                       env=dict(os.environ, GATEKEEPER_PROFILE="DEFAULT"))
        for _ in range(60):
            if subprocess.run(compose + ["exec", "-T", "sensor", "python", "-c",
                    "import socket; socket.create_connection(('127.0.0.1',2222),1).close()"],
                    capture_output=True).returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("sensor unavailable")
        with patch.object(bot_like, "execute_ssh_command", observe):
            for _ in range(2):
                bot_like.run_bot_like()
        Path("results/cost/t1_trace.json").write_text(json.dumps(observations, indent=2)+"\n")
    finally:
        subprocess.run(compose + ["down", "-v"], check=True)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        override = Path(tmp) / "compose.yml"
        override.write_text("services:\n  sensor:\n    container_name: schrodinger-final-cost-sensor\n")
        trace(COMPOSE + ["-f", str(override)])

