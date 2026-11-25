# Experiment 1
Post-hoc relative to Experiment 0. Offline, three audited days, one archive.

| Stage | Test day | Best baseline | Learned recall | Baseline recall | Shuffle | Constant | Ablation | Adjusted delta interval | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| S2 | 2025-08-09 | negative_activity | 0.063583 | 0.099913 | 0.065613 | 0.100001 | 0.100001 | [-0.0496, -0.0155] | INVALID |
| S4 | 2025-08-09 | R7 | 0.35634 | 0.141847 | 0.35634 | 0.100003 | 0.141847 | [-0.089, 0.6594] | INVALID |
| S5 | 2025-08-09 | negative_activity | 0.0 | 0.049105 | 0.082353 | 0.104348 | 0.011765 | [-0.068, 0.0258] | INCONCLUSIVE |

NO VALIDATED ML GAIN

Budgets, precision, PR-AUC, convergence and validation selection are in metrics.json. The table reports recall at the 10% budget. S5 has fewer than 500 test positives.
