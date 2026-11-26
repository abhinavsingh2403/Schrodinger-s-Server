# S4 root-cause diagnosis
Post-hoc exploratory, outside the pre-registered protocol.
Identical fitted slopes: REJECTED.
Identical real/shuffle weak order: False.
Label-free exact ranking reproduction: INCONCLUSIVE; matching rankers [].
Ablation/R7 identical weak order: REJECTED.
Label-free feature sum reproduces recall: CONFIRMED.
Elapsed time alone comes close. Both fits give positive weight to elapsed time, activity and auth counts. Removing elapsed time, activity and gap leaves auth counts to distinguish rows; R7 also uses auth counts.
real versus shuffle: 0 of 62778 selection weights differ at the cutoff; expected true-positive difference 0.
real versus activity_sum: 0 of 62778 selection weights differ at the cutoff; expected true-positive difference 0.
ablation versus R7: 0 of 62778 selection weights differ at the cutoff; expected true-positive difference 0.

| Ranker | Recall at 10% | Score bins | Same weak order as real |
|---|---:|---:|---|
| real | 0.35634 | 173 | True |
| shuffle | 0.35634 | 173 | False |
| ablation | 0.141847 | 7 | False |
| R7 | 0.141847 | 4 | False |
| elapsed:1 | 0.352005 | 118 | False |
| elapsed:-1 | 0.033659 | 118 | False |
| activity:1 | 0.144659 | 7 | False |
| activity:-1 | 0.095041 | 7 | False |
| attempts:1 | 0.141847 | 7 | False |
| attempts:-1 | 0.095354 | 7 | False |
| failures:1 | 0.141847 | 7 | False |
| failures:-1 | 0.095354 | 7 | False |
| successes:1 | 0.100003 | 1 | False |
| successes:-1 | 0.100003 | 1 | False |
| usernames:1 | 0.099989 | 2 | False |
| usernames:-1 | 0.100005 | 2 | False |
| commands:1 | 0.100003 | 1 | False |
| commands:-1 | 0.100003 | 1 | False |
| length:1 | 0.100003 | 1 | False |
| length:-1 | 0.100003 | 1 | False |
| tokens:1 | 0.100003 | 1 | False |
| tokens:-1 | 0.100003 | 1 | False |
| bucket:1 | 0.100003 | 1 | False |
| bucket:-1 | 0.100003 | 1 | False |
| gap:1 | 0.100003 | 1 | False |
| gap:-1 | 0.100003 | 1 | False |
| activity_sum | 0.35634 | 119 | False |

Exact weights and loss are in root_cause_details.json. Equal recall alone cannot establish equal rankings. This diagnostic reuses the exposed test cohort and supplies no fresh validation.
Reproduce with `python -m analysis.experiment1_root_cause`.
