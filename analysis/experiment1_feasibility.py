"""Probe offline SSH stage boundaries on the audited local days without fitting a model."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import time

import duckdb

from analysis.event_prefix_study import summarize

REPORT = Path("results/exp0/EXPERIMENT1_FEASIBILITY.md")
COLUMNS = "{ts:'VARCHAR',sensor:'VARCHAR',session:'VARCHAR',eventid:'VARCHAR',input:'VARCHAR'}"


def boundaries(conn):
    """Count complete sessions; exclude same-timestamp ambiguity from usable prefixes."""
    summary = summarize(conn)
    conn.execute("""CREATE TEMP TABLE auth AS
        SELECT sensor,session,min(ts) AS first_auth FROM events
        WHERE eventid IN ('cowrie.login.success','cowrie.login.failed') GROUP BY ALL""")
    counts = {}
    for stage, expression in (("S2", "first_auth"), ("S4", "s4"), ("S5", "commands[3]")):
        row = conn.execute(f"""WITH anchors AS (
            SELECT sensor,session,{expression} AS anchor,connected,closed,value
            FROM sessions LEFT JOIN auth USING(sensor,session)
        ), prefixes AS (
            SELECT a.sensor,a.session,a.value,
                   count(*) FILTER (WHERE ts=anchor) AS simultaneous,
                   count(DISTINCT command_hash)>=5 OR count(*) FILTER (
                      WHERE eventid IN ('cowrie.session.file_download','cowrie.session.file_upload',
                                        'cowrie.direct-tcpip.request'))>0 AS already_positive
            FROM anchors a JOIN events USING(sensor,session)
            WHERE anchor BETWEEN connected AND closed AND ts<=anchor
            GROUP BY a.sensor,a.session,a.value
        ) SELECT count(*), count(*) FILTER (WHERE simultaneous>1),
            count(*) FILTER (WHERE simultaneous=1 AND NOT already_positive),
            count(*) FILTER (WHERE simultaneous=1 AND NOT already_positive AND value)
            FROM prefixes""").fetchone()
        counts[stage] = Counter(dict(zip(("reached", "tied", "eligible", "future"), row)))
        if stage != "S2" and row[0] != summary["stages"][stage]["reached"]:
            raise ValueError("boundary cohort disagrees with existing audit")
    return counts


def probe(folder):
    audit = json.loads(Path("results/exp0/event_prefix_study.json").read_text())
    schema = json.loads(Path("results/s3_event_schema.json").read_text())
    fields = set(schema["schema_verification"]["all_fields_found"])
    totals = defaultdict(Counter)
    sizes = events = 0
    runtimes = []
    newkeys = 0
    for day, recorded in sorted(audit["days"].items()):
        path = folder / (day+".json.gz")
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != recorded["sha256"]:
                raise ValueError(f"cache digest mismatch for {day}")
        sizes += path.stat().st_size
        start = time.monotonic()
        with duckdb.connect() as conn:
            conn.execute("SET threads=2")
            conn.execute("SET memory_limit='1GB'")
            conn.execute(f"""CREATE TABLE events AS SELECT sensor, session,
                TRY_CAST(ts AS TIMESTAMP) AS ts,eventid,
                CASE WHEN eventid='cowrie.command.input' THEN sha256(input) END AS command_hash
                FROM read_json(?,format='newline_delimited',compression='gzip',columns={COLUMNS})""",
                         [str(path)])
            n = conn.execute("SELECT count(*) FROM events").fetchone()[0]
            if n != recorded["events"]:
                raise ValueError(f"event count mismatch for {day}")
            newkeys += conn.execute("SELECT count(*) FROM events WHERE "
                                   "lower(eventid) LIKE '%newkeys%'").fetchone()[0]
            events += n
            conn.execute("DELETE FROM events WHERE ts IS NULL OR session IS NULL OR sensor IS NULL")
            for stage, counts in boundaries(conn).items():
                totals[stage].update(counts)
        runtimes.append(time.monotonic()-start)

    names = ("ts", "sensor", "session", "eventid", "input", "src_ip")
    if newkeys:
        raise ValueError("NEWKEYS events found: review S1 mapping")
    prior = Path("results/exp0/PRECOMMAND_NOT_VERIFIABLE.md").read_text()
    s3 = int(next(line for line in prior.splitlines() if "Verified historical S3 decision boundaries"
                  in line).split("|")[2].strip())
    if s3:
        raise ValueError("historical S3 evidence changed")
    lines = ["# Experiment 1 feasibility", "Post-hoc probe, not part of the pre-registered gate.", "",
             f"Local audited members: {len(runtimes)}; compressed bytes: {sizes}; events: {events}. "
             f"First day stream and boundary check: {runtimes[0]:.2f} seconds (digest check excluded).",
             "Full ZIP in the cache: "+("yes" if (folder/"data_all.zip").exists() else "no")+". Source: DATA.md, data_all.zip.",
             "Archive fields present: "+", ".join(f"{k}={'yes' if k in fields else 'no'}" for k in names)+
             ". Command text is available and hashed in memory.",
             "", "| Stage | Reached | Tied | Tie rate | Identifiable (untied) | Future outcome unresolved | Future positive | Verdict |",
             "|---|---:|---:|---:|---:|---:|---:|---|"]
    feasible = []
    for stage in ("S1", "S2", "S3", "S4", "S5"):
        if stage not in totals:
            verified = newkeys if stage == "S1" else s3
            lines.append(f"| {stage} | NA | NA | NA | {verified} | NA | NA | NOT IDENTIFIABLE |")
            continue
        data = totals[stage]
        n, tied = data["reached"], data["tied"]
        verdict = "IDENTIFIABLE" if n > tied else "INCONCLUSIVE"
        if n > tied:
            feasible.append(stage)
        rate = f"{tied/n:.4%}" if n else "NA"
        lines.append(f"| {stage} | {n} | {tied} | {rate} | {n-tied} | {data['eligible']} | "
                     f"{data['future']} | {verdict} |")
    lines += ["", "S1 uses the runtime NEWKEYS hook. The archived client algorithm offer cannot "
              "date completion. S3 uses the previously recorded zero in PRECOMMAND_NOT_VERIFIABLE.md.",
              "S2 uses first auth outcome per session. S4 and S5 use the first and third command "
              "events (SPEC and the existing offline audit; the live adapter also calls S5 on command two). A tie means any other event at the same timestamp in that session. "
              "Only complete same-day sessions with untied anchors enter the unresolved and future-positive counts. "
              "The outcome is five distinct commands, transfer or direct-TCPIP.",
              "", "FEASIBLE FOR stages ["+", ".join(feasible)+"]. Laptop CPU: yes for these "
              "cached members, processed one at a time. Full archive runtime unmeasured. "
              "Before fitting, register endpoint definitions, preserve session grouping, and check "
              "chronological/source-disjoint splits. Capture explicit S1/S3 markers for those stages.",
              "", "Reproduce: `python -m analysis.experiment1_feasibility --cache data/event_prefix_study`."]
    REPORT.write_text("\n".join(lines)+"\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    probe(parser.parse_args().cache)
