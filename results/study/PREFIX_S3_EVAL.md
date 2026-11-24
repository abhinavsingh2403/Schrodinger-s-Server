# S3 prefix evaluation

SYNTHETIC harness data. Label = script type. Mechanism check only, tiny N.

Train sessions 12, test sessions 12. First S3 per session, 10% budget, expected cutoff ties.
Balanced optimizer uses the archived C and caps its step at C*n/2 for small samples.

| Scorer | Recall |
|---|---:|
| Real | 0.222222 |
| Constant | 0.166667 |
| Shuffle | 0.111111 |
| Negative activity | 0.111111 |
| Random | 0.166667 |
Shuffle diagnostic: INVALID (outside random +/-0.02).
Exploratory only. No inference about real attackers or validated ML.
