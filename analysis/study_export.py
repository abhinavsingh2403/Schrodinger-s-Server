"""Join lab study labels to verified sensor prefixes and SQLite decisions."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import sqlite3
from collections import Counter

from analysis.prefix_s3_eval import prefixes
from gatekeeper.features import STAGE_ALLOWED_FEATURES
from gatekeeper.visitor_memory import derive_visitor_id

FEATURES = STAGE_ALLOWED_FEATURES["S3"]


def export(events, db, labels, output):
    secret = os.environ.get("SENSOR_PREFIX_JOIN_KEY")
    if not secret:
        raise ValueError("Set the same private SENSOR_PREFIX_JOIN_KEY used by the sensor")
    assignments = {}
    with labels.open() as f:
        for row in csv.DictReader(f):
            hint = row["session_hint"]
            if not re.fullmatch(r"[0-9a-f]{16}",hint) or hint in assignments:
                raise ValueError("Expected unique masked session_hint")
            code, task = row["participant_code"], row["instruction"]
            if not re.fullmatch(r"P[0-9]{2,}",code) or task not in ("A","B","C"):
                raise ValueError("Invalid participant code or instruction")
            assignments[hint] = code,task
    with sqlite3.connect(db.resolve().as_uri()+"?mode=ro",uri=True) as conn:
        requested = Counter({derive_visitor_id(sid,secret.encode()):n for sid,n in
            conn.execute("select session_id,count(*) from decision_log where stage='S3' group by session_id")})
    observed = Counter()
    def labelled(stream):
        for line in stream:
            r = json.loads(line)
            if r.get("stage") == "S3":
                key = r["session"]
                if key not in assignments:
                    raise ValueError("Missing label for S3 session")
                observed[key] += 1
                r["label"] = int(assignments[key][1] != "B")
            yield r
    with events.open() as f:
        data = prefixes(labelled(f))
    if not data or observed != requested or set(data) != set(assignments):
        raise ValueError("Study labels, sensor markers and S3 database sessions must match")
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("x",newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["session","participant_code","instruction","label",*FEATURES])
        for key,(values,label) in data.items():
            writer.writerow([key,*assignments[key],label,*values])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("events","db","labels"):
        p.add_argument("--"+name,required=True,type=Path)
    p.add_argument("--output",type=Path,default=Path("results/study/study_sessions.csv"))
    export(**vars(p.parse_args()))
