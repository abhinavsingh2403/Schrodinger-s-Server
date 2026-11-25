"""Render matched workload measurements and final-tier failures from saved repeats."""
import json
import math
from pathlib import Path

from gatekeeper.policy import parse_policy_yaml

ROOT = Path("results/cost")


def render():
    report = ROOT/"COST_PER_TIER.md"
    heading = "## T1 purity fix"
    history = report.read_text().split("\n"+heading)[0].rstrip()
    trace = json.loads((ROOT/"t1_trace.json").read_text())
    trigger = next(x for x in trace if any(r[2] == "T2" for r in x["rows"]))
    index = trace.index(trigger)
    row = next(r for r in trigger["rows"] if r[2] == "T2")
    before = [r for x in trace[:index] for r in x["rows"]]
    proposals = sum(r[1] == "S2" and r[3] == row[3] and r[5] >= row[5] for r in before)
    budgets = parse_policy_yaml("config/policy.yaml")
    fraction = budgets["budget"]["max_escalation_fraction"]
    previous_sessions = len({r[0] for r in before})
    slots_before = math.floor(previous_sessions*fraction)
    slots_at = math.floor((previous_sessions+1)*fraction)
    prior_t2 = sum(r[2] == "T2" for r in before)
    ptys = sum(x["pty"] for x in trace)
    s5_count = sum(r[1] == "S5" for x in trace for r in x["rows"])
    budget_supported = slots_before == 0 and slots_at == 1 and proposals > 0
    runs = json.loads((ROOT/"cost_T1_only.json").read_text())["runs"]
    date = next((r["stats"]["timestamp"][:10] for r in runs if "stats" in r), "attempt incomplete")
    lines = [history, "", f"{heading} ({date})", "",
        f"Fresh DEFAULT replay: invocation {trigger['invocation']} (`{trigger['command']}`), "
        f"session `{row[0]}`, first escalated at {row[1]} with {row[3]} score {row[5]}.",
        "", "| Hypothesis (first escalation only) | Verdict | Observation |", "|---|---|---|",
        f"| Visitor memory | {'REJECTED' if not prior_t2 else 'INCONCLUSIVE'} | {trigger['distinct_visitors']} visitor; "
        f"{prior_t2} earlier T2 decisions to inherit. |",
        f"| PTY | {'REJECTED' if not ptys else 'INCONCLUSIVE'} | {ptys} requests. |",
        f"| S5 rule | {'REJECTED' if not s5_count else 'INCONCLUSIVE'} | {s5_count} S5 decisions. |",
        f"| Session admission budget | {'CONFIRMED' if budget_supported else 'INCONCLUSIVE'} | {proposals} earlier successful-auth scores "
        f"were held at T1. Admissible slots at fraction {fraction:g}: {slots_before} before, "
        f"{slots_at} at session {previous_sessions+1}. |",
        f"| Successful-auth rule | {'CONFIRMED' if row[3]=='rule_r1_login_success' else 'INCONCLUSIVE'} | {row[3]} proposed escalation at {row[1]}; "
        "later decisions retained the tier. |", "",
        "Both measured arms now use LAB_DEMO_NOT_ML with one authenticated hostname query per "
        "session. Only PTY allocation differs. This removes the DEFAULT login-success trigger "
        "from the workload without changing either policy. Every session must be accounted for.",
        "", "| Workload | Attempt | Final T1/T2 sessions | Decisions T1/T2 | T1/T2 decision fractions | T1/T2 observed time fractions | T2 decisions by stage | Retained samples |",
        "|---|---:|---|---|---|---|---|---:|"]
    arms = {}
    stats_lines = []
    notes = []
    for tier in ("T1","T2"):
        payload = json.loads((ROOT/f"cost_{tier}_only.json").read_text())
        accepted = []
        for index,row in enumerate(payload["runs"],1):
            data = row["summary"]
            def pair(field):
                return " / ".join(format(data[field].get(t,0),".5g") if data[field].get(t,0) is not None else "NA" for t in ("T1","T2"))
            stages = ", ".join(f"{k}={v}" for k,v in sorted(data["t2_decision_stages"].items()))
            lines.append(f"| {tier} | {index} | {pair('final_tiers')} | {pair('decision_counts')} | {pair('decision_fraction')} | {pair('observed_time_fraction')} | {stages} | {row['samples']} |")
            if "stats" in row:
                accepted.append(row["stats"])
                st = row["stats"]
                stats_lines.append(f"| {tier} | {index} | {st['wall_time']} | {st['mean_cpu_pct']} | {st['max_cpu_pct']} | {st['mean_memory_mb']} | {st['max_memory_mb']} |")
        arms[tier] = accepted
        if accepted:
            for metric in ("mean_cpu_pct","mean_memory_mb"):
                values = [r[metric] for r in accepted]
                notes.append(f"\n{tier} {metric} across accepted repeats: {min(values)} to {max(values)}.")
        else:
            notes.append(f"\n{tier} NOT RUN to completion: retry failed final-tier purity. CPU, memory and repeat spread unavailable.\n")
    lines += ["",*notes,"","| Target | Attempt | Wall seconds | Mean CPU % | Max CPU % | Mean MB | Max MB |",
              "|---|---:|---:|---:|---:|---:|---:|",*stats_lines,"",
              "Matched session count and pacing window. Sampling includes pauses and early T1 "
              "time inside T2-final sessions. Both personas share one sensor process. Terminal "
              "allocation also differs, so this cannot isolate a persona-only resource effect."]
    if all(len(rows) == 3 for rows in arms.values()):
        for metric, unit in (("mean_cpu_pct","percentage points"),("mean_memory_mb","MB")):
            deltas = [b[metric]-a[metric] for a,b in zip(arms["T1"],arms["T2"])]
            lines.append(f"Repeat-index differences (T2-final minus T1-final), {metric}: "
                         f"{min(deltas):+.2f} to {max(deltas):+.2f} {unit}.")
    lines += ["", "Reproduce: `python -m analysis.t1_cost_trace`, "
              "`python -m analysis.tier_cost_study --tier T1`, "
              "`python -m analysis.tier_cost_study --tier T2`, `python -m analysis.render_tier_cost`."]
    (ROOT/"COST_PER_TIER.md").write_text("\n".join(lines)+"\n")


if __name__ == "__main__":
    render()
