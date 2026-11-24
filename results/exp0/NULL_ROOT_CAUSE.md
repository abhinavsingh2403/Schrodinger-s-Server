# S3 null ranking

Post-hoc exploratory, not part of the pre-registered gate.

Training sample 50000 (positive fraction 0.0257000); S3 reached test rows 100793, positives 8619. Budget 10%, expected cutoff ties. Archived real scorer 0.291966; fallback trained on identical soft targets 0.649042.

## Constant-target fit

CONFIRMED. exp0_train.train_and_evaluate_ml_candidates uses exp0_rules.PurePythonLogisticRegression. All coefficients and the intercept start at zero (initial probability 0.5). Each feature uses training (x-min)/range. The first slope update is -lr*(0.5-q)*mean(scaled x). With 60 steps, lr 0.5, C 0.01, slope penalty gradient w/(C*n) and an unpenalized intercept, the fitted intercept is -1.6637345. The exact constant-target optimum has zero slopes and intercept logit(q) = -3.6352283: its loss gradient vanishes for every training row. Its test recall is 0.100007. Finite simultaneous updates from zero leave activity-dependent slopes even though targets never vary.

| Feature | Train min | Range | First update | Constant final | Real refit | Null recall alone | Null recall omitted |
|---|---:|---:|---:|---:|---:|---:|---:|
| cnt_session_connect | 1 | 1e-06 | -0 | 0 | 0 | 0.100007 | 0.649042 |
| cnt_client_version | 0 | 1 | -0.2299738 | -1.41753 | -1.429471 | 0.100007 | 0.649042 |
| cnt_client_kex | 0 | 2 | -0.1109815 | -0.6756179 | -0.6694195 | 0.100007 | 0.649042 |
| cnt_client_fingerprint | 0 | 2 | -0.0005288445 | -0.00326809 | -0.003457101 | 0.099933 | 0.649042 |
| cnt_login_failed | 0 | 21 | -0.00968769 | -0.06014437 | -0.07161688 | 0.098696 | 0.647429 |
| cnt_login_success | 0 | 1 | -0.03396937 | -0.1801949 | 0.4108884 | 0.100007 | 0.649042 |
| cnt_client_size | 0 | 4 | -4.624425e-05 | -0.0002453099 | 0.0001227386 | 0.099904 | 0.649042 |
| cnt_client_var | 0 | 1e-06 | -0 | 0 | 0 | 0.100007 | 0.649042 |
| cnt_session_params | 0 | 146 | -0.0003176835 | -0.001685421 | 0.01405945 | 0.647778 | 0.098591 |

CONFIRMED: session.params dominates the null cutoff. Among 10466 reached rows with zero session.params, 5797 were positive. Giving priority to lower counts alone yields 0.647778; dropping this slope yields 0.098591. Real labels reverse its sign. Replacing only the real fit's session.params slope with the null slope yields 0.649494.

CONFIRMED: activity alone ranks positives. Negative unweighted sum of min-max counters has recall 0.648992; negative mean-weighted sum (first update) 0.649042. These rankings require no training outcomes. Equal recall need not imply identical full rankings.

## Real labels

CONFIRMED: changing only targets changes slopes and cutoff selection. Unweighted real-label refit intercept -1.6972690, test 0.291966; archived model 0.291966. Training recall with real slopes 0.437281, with constant-target slopes 0.000000 (training includes unreached sessions).
REJECTED: a prediction sign or scale reversal in the observed path. Positive-class sigmoid scoring on raw rows yields 0.649042; ranking its normalized linear predictor gives 0.649042.
CONFIRMED: the fallback omits the grid's balanced weights. Changing just class weights gives 0.294629 on test. INCONCLUSIVE: this comparison cannot identify overfitting or establish a causal contribution from training/test population shift.

## Timing

Removing session.params, client.size and client.var contributions together gives null 0.098696 and archived real 0.098696. This checks reliance on these aggregate columns, not prefix validity of the remaining features.
- 2025-07-07: 2196/48645 complete command sessions with a counter at or after first command.
- 2025-08-03: 15237/50608 complete command sessions with a counter at or after first command.
- 2025-08-09: 13063/85130 complete command sessions with a counter at or after first command.

INCONCLUSIVE: exact post-decision attribution. The event sample lacks a verified historical S3 decision timestamp. Removing columns cannot reconstruct per-row prefix counts.
