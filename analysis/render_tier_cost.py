"""Render matched workload measurements and final-tier failures from saved repeats."""
import json
from pathlib import Path

ROOT = Path("results/cost")


def render():
    lines = ["# Docker final-tier cost study","",
             "Purity uses the last persisted decision for each SSH session. Decision shares count requests. Time shares sum the intervals between consecutive decisions within each session, credited to the earlier tier. Time before the first decision and after the last is unobserved. Both personas run inside one sensor process. A T2-final session can spend early time in T1.",
             "", "The previous volumes were removed. Only aggregated counts survive from those runs, so the historical sessions and triggers cannot be identified. Fresh-volume reruns isolate each attempt. Stage counts indicate when a tier was returned, without identifying why policy selected it.",
             "", "| Workload | Attempt | Final T1/T2 sessions | Decisions T1/T2 | T1/T2 decision fractions | T1/T2 observed time fractions | T2 decisions by stage | Retained samples |",
             "|---|---:|---|---|---|---|---|---:|"]
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
        if accepted:
            for metric in ("mean_cpu_pct","mean_memory_mb"):
                values = [r[metric] for r in accepted]
                notes.append(f"\n{tier} {metric} across accepted repeats: {min(values)} to {max(values)}.")
        else:
            notes.append(f"\n{tier} NOT RUN to completion: retry failed final-tier purity. CPU, memory and repeat spread unavailable.\n")
    lines += ["",*notes,"","| Target | Attempt | Wall seconds | Mean CPU % | Max CPU % | Mean MB | Max MB |",
              "|---|---:|---:|---:|---:|---:|---:|",*stats_lines,"",
              "The schedule uses the same number of paced harness invocations per completed repeat. Each invocation opens multiple SSH sessions; actual session counts are shown above. Sampling includes pacing pauses. An impure workload prevents a matched comparison.",
              "", "Reproduce in WSL: `python -m analysis.tier_cost_study --tier T1`, `python -m analysis.tier_cost_study --tier T2`, then `python -m analysis.render_tier_cost`."]
    (ROOT/"COST_PER_TIER.md").write_text("\n".join(lines)+"\n")


if __name__ == "__main__":
    render()
