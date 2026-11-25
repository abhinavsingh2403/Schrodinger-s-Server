"""Run fresh-volume lab cost workloads and reject a repeat as soon as tier purity fails."""
import argparse
from collections import Counter
from datetime import datetime
import csv
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from analysis.measure_cost import measure_cost
from harness.attackers.common import execute_ssh_command

COMPOSE = ["docker","compose","-p","schrodinger-final","-f","infra/docker-compose.yml"]
OUT = Path("results/cost")


class MixedTier(Exception):
    """Persist the first disqualifying tier mix without reporting partial costs."""


def summarize(rows):
    tiers = Counter()
    seconds = Counter()
    previous = {}
    t2_stages = Counter()
    for sid,stage,tier,stamp in rows:
        now = datetime.fromisoformat(stamp)
        if sid in previous:
            last,when = previous[sid]
            seconds[last] += (now-when).total_seconds()
        previous[sid] = tier,now
        tiers[tier] += 1
        if tier == "T2":
            t2_stages[stage] += 1
    def fractions(counts):
        total = sum(counts.values())
        return {t: counts[t]/total if total else None for t in ("T1","T2")}
    return dict(final_tiers=dict(Counter(t for t,_ in previous.values())), decision_counts=dict(tiers),
                decision_fraction=fractions(tiers), observed_time_fraction=fractions(seconds),
                t2_decision_stages=dict(t2_stages))


def decisions(compose):
    query = "select session_id,stage,tier_decided,timestamp from decision_log order by rowid"
    code = f"import sqlite3,json; print(json.dumps(sqlite3.connect('/app/data/gatekeeper.db').execute({query!r}).fetchall()))"
    return summarize(json.loads(subprocess.check_output(compose+["exec","-T","gatekeeper","python","-c",code])))


def matched_login(tier, host, port, dry_run=False):
    """Run one benign identity query. Only the terminal request differs by arm."""
    if dry_run or tier not in ("T1", "T2"):
        raise ValueError("a measured tier is required")
    result = execute_ssh_command(host, port, "root", password="password",
                                 command="hostname", allocate_pty=tier == "T2")
    return {"ok": result.returncode == 0 and "srv-app-01" in result.stdout.splitlines()}


def run(tier, compose):
    env = dict(os.environ, GATEKEEPER_PROFILE="LAB_DEMO")
    runs = []
    complete = 0
    failures = 0
    while complete < 3 and failures < 2:
        subprocess.run(compose+["down","-v"],check=True)
        try:
            subprocess.run(compose+["up","-d","--build"],env=env,check=True)
            for _ in range(60):
                if subprocess.run(compose+["exec","-T","sensor","python","-c",
                        "import socket; socket.create_connection(('127.0.0.1',2222),1).close()"],
                        capture_output=True).returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("sensor readiness timeout")
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                # Keep the requested workload window identical across tiers.
                completed_sessions = 0
                def paced(**kwargs):
                    nonlocal completed_sessions
                    start = time.monotonic()
                    result = matched_login(tier, **kwargs)
                    completed_sessions += 1
                    mix = decisions(compose)
                    if mix["final_tiers"] != {tier: completed_sessions}:
                        raise MixedTier(mix)
                    remaining = 6 - (time.monotonic()-start)
                    if remaining < 0:
                        raise RuntimeError("workload exceeded fixed slot")
                    time.sleep(remaining)
                    return result
                from unittest.mock import patch
                with patch("analysis.measure_cost.run_bot_like",side_effect=paced):
                    stats = measure_cost(tier=tier,sessions=20,host="127.0.0.1",port=2222,
                        container_name="schrodinger-final-cost-sensor",output_dir=folder,cost_model_file=folder/"cost.json",
                        raw_command_line=f"python -m analysis.tier_cost_study --tier {tier}")
                mix = decisions(compose)
                with next(folder.glob("*.csv")).open() as f:
                    samples = sum(1 for _ in csv.DictReader(f))
                runs.append(dict(repeat=complete+1,stats=stats,summary=mix,samples=samples))
                complete += 1
                failures = 0
        except MixedTier as exc:
            runs.append(dict(repeat=complete+1,status="BLOCKED: impure final tiers",summary=exc.args[0],samples=0))
            failures += 1
        finally:
            subprocess.run(compose+["down","-v"],check=True)
    payload = dict(target=tier,pure=complete==3,runs=runs)
    (OUT/f"cost_{tier}_only.json").write_text(json.dumps(payload,indent=2)+"\n")


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier",required=True,choices=["T1","T2"])
    with tempfile.TemporaryDirectory() as tmp:
        override = Path(tmp)/"compose.yml"
        override.write_text("services:\n  sensor:\n    container_name: schrodinger-final-cost-sensor\n")
        run(parser.parse_args().tier, COMPOSE+["-f",str(override)])
