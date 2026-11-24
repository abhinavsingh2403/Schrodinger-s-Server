"""Check S3 model counters against each loopback session's ordered prefix."""
from collections import Counter, defaultdict
import argparse
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from analysis.live_sensor_proof import independent_lab
from gatekeeper.features import EVENT_COUNTERS, stage_counters
from harness.attackers.bot_like import run_bot_like
from harness.attackers.interactive import run_interactive
from harness.attackers.slow_recon import run_slow_recon
from harness.attackers.transfer_like import run_transfer_like


def check(rows):
    seq = Counter()
    counts = defaultdict(Counter)
    marked = Counter()
    errors = 0
    for row in rows:
        key = row["session"]
        if "event" in row:
            seq[key] += 1
            errors += row["seq"] != seq[key]
            field = EVENT_COUNTERS.get(row["event"])
            if field:
                counts[key][field] += 1
        else:
            errors += row["last_seq"] != seq[key]
            if row["stage"] == "S3":
                marked[key] += 1
                expected = stage_counters("S3", counts[key])
                errors += any(row["features"].get(k) != v for k,v in expected.items())
    return dict(sessions=len(seq), sessions_with_s3=len(marked), s3_markers=sum(marked.values()), errors=errors)


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture",type=Path,help="Write a new labelled prefix trace for the synthetic study")
    args = parser.parse_args()
    capture = []
    results = {}
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)/"prefix.jsonl"
        with patch.dict(os.environ, SENSOR_PREFIX_LOG=str(path)), independent_lab(root,folder):
            for run in (run_bot_like,run_interactive,run_slow_recon,run_transfer_like):
                start = path.stat().st_size if path.exists() else 0
                outcome = run(port=12222)
                with path.open("rb") as stream:
                    stream.seek(start)
                    rows = [json.loads(line) for line in stream]
                    results[run.__name__] = check(rows)
                    if run != run_slow_recon:
                        capture.extend(dict(row,label=int(run != run_bot_like)) for row in rows)
                results[run.__name__]["returncode"] = outcome["returncode"]
    passed = all(r["returncode"]==0 and r["sessions"] and r["sessions"]==r["sessions_with_s3"] and not r["errors"] for r in results.values())
    if args.capture:
        if any(r["returncode"] or r["errors"] for r in results.values()):
            raise RuntimeError("Invalid lab capture")
        with args.capture.open("x") as f:
            for row in capture:
                f.write(json.dumps(row)+"\n")
        return 0
    target = root/"results/study/marker_consistency.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(dict(scope="LAB",passed=passed,scenarios=results),indent=2)+"\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
