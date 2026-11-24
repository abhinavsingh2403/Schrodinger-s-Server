# Docker final-tier cost study

Purity uses the last persisted decision for each SSH session. Decision shares count requests. Time shares sum the intervals between consecutive decisions within each session, credited to the earlier tier. Time before the first decision and after the last is unobserved. Both personas run inside one sensor process. A T2-final session can spend early time in T1.

The previous volumes were removed. Only aggregated counts survive from those runs, so the historical sessions and triggers cannot be identified. Fresh-volume reruns isolate each attempt. Stage counts indicate when a tier was returned, without identifying why policy selected it.

| Workload | Attempt | Final T1/T2 sessions | Decisions T1/T2 | T1/T2 decision fractions | T1/T2 observed time fractions | T2 decisions by stage | Retained samples |
|---|---:|---|---|---|---|---|---:|
| T1 | 1 | 9 / 1 | 37 / 3 | 0.925 / 0.075 | 0.99237 / 0.0076259 | S2=1, S3=1, S4=1 | 0 |
| T1 | 2 | 9 / 1 | 37 / 3 | 0.925 / 0.075 | 0.99219 / 0.0078071 | S2=1, S3=1, S4=1 | 0 |
| T2 | 1 | 0 / 120 | 2 / 478 | 0.0041667 / 0.99583 | 0.0089729 / 0.99103 | S1=119, S2=119, S3=120, S4=120 | 200 |
| T2 | 2 | 0 / 120 | 2 / 478 | 0.0041667 / 0.99583 | 0.0081542 / 0.99185 | S1=119, S2=119, S3=120, S4=120 | 200 |
| T2 | 3 | 0 / 120 | 2 / 478 | 0.0041667 / 0.99583 | 0.0078053 / 0.99219 | S1=119, S2=119, S3=120, S4=120 | 200 |


T1 NOT RUN to completion: retry failed final-tier purity. CPU, memory and repeat spread unavailable.


T2 mean_cpu_pct across accepted repeats: 2.29 to 2.47.

T2 mean_memory_mb across accepted repeats: 106.81 to 107.32.

| Target | Attempt | Wall seconds | Mean CPU % | Max CPU % | Mean MB | Max MB |
|---|---:|---:|---:|---:|---:|---:|
| T2 | 1 | 402.3183 | 2.29 | 41.07 | 106.91 | 113.7 |
| T2 | 2 | 402.2897 | 2.29 | 36.64 | 107.32 | 114.4 |
| T2 | 3 | 402.512 | 2.47 | 42.15 | 106.81 | 114.0 |

The schedule uses the same number of paced harness invocations per completed repeat. Each invocation opens multiple SSH sessions; actual session counts are shown above. Sampling includes pacing pauses. An impure workload prevents a matched comparison.

Reproduce in WSL: `python -m analysis.tier_cost_study --tier T1`, `python -m analysis.tier_cost_study --tier T2`, then `python -m analysis.render_tier_cost`.
