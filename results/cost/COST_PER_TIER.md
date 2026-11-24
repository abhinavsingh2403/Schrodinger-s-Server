# Per-tier Docker cost

Both workloads failed the persisted decision purity check. Partial samples were discarded. CPU and memory means and maxima are unavailable.

| Target | T1 decisions | T2 decisions | Retained samples |
|---|---:|---:|---:|
| T1 | 37 | 3 | 0 |
| T2 | 2 | 22 | 0 |

NOT RUN to completion: three matched repeats per tier. In the native WSL lab environment run `python -m analysis.tier_cost_study --tier T1` and `python -m analysis.tier_cost_study --tier T2`. The runner stops at the first wrong-tier decision. Both personas share one sensor process. No monetary or savings estimates or extrapolation.
