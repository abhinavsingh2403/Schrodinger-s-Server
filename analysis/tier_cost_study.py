"""Run fresh-volume lab cost workloads and reject a repeat as soon as tier purity fails."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from analysis.measure_cost import measure_cost
from harness.attackers.bot_like import run_bot_like
from harness.attackers.interactive import run_interactive

COMPOSE = ["docker","compose","-p","schrodinger-final","-f","infra/docker-compose.yml"]
OUT = Path("results/cost")


class MixedTier(Exception):
    """Persist the first disqualifying tier mix without reporting partial costs."""


def decisions(compose):
    query = "select tier_decided,count(*) from decision_log group by tier_decided"
    code = f"import sqlite3,json; print(json.dumps(dict(sqlite3.connect('/app/data/gatekeeper.db').execute({query!r}))))"
    mix = json.loads(subprocess.check_output(compose+["exec","-T","gatekeeper","python","-c",code]))
    return mix


def run(tier, compose):
    workload = run_bot_like if tier == "T1" else run_interactive
    env = dict(os.environ, GATEKEEPER_PROFILE="DEFAULT" if tier=="T1" else "LAB_DEMO")
    runs = []
    for repeat in range(3):
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
                def paced(**kwargs):
                    start = time.monotonic()
                    result = workload(**kwargs)
                    mix = decisions(compose)
                    if set(mix) != {tier}:
                        raise MixedTier(mix)
                    remaining = 20 - (time.monotonic()-start)
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
                runs.append(dict(repeat=repeat+1,stats=stats,decision_counts=mix,samples=samples))
        except MixedTier as exc:
            runs.append(dict(repeat=repeat+1,status="BLOCKED: mixed decisions",decision_counts=exc.args[0],samples=0))
            break
        finally:
            subprocess.run(compose+["down","-v"],check=True)
    payload = dict(target=tier,pure=len(runs)==3 and all(set(r["decision_counts"])=={tier} for r in runs),runs=runs)
    (OUT/f"cost_{tier}_only.json").write_text(json.dumps(payload,indent=2)+"\n")


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier",required=True,choices=["T1","T2"])
    with tempfile.TemporaryDirectory() as tmp:
        override = Path(tmp)/"compose.yml"
        override.write_text("services:\n  sensor:\n    container_name: schrodinger-final-cost-sensor\n")
        run(parser.parse_args().tier, COMPOSE+["-f",str(override)])
