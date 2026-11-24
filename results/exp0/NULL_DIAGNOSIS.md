# S3 null-control diagnosis



Observed model 0.291966. Session permutation seed 20261111: 0.649042; archived same seed 0.649042. Archived mean 0.649098.

REJECTED: row order drives the official tie estimate. Original 0.649042, permuted test-row order 0.649042. This estimator averages the cutoff bin.

INCONCLUSIVE: source-cluster exchangeability. One equal-size block permutation gives 0.649042; 1170 training labels changed. Unique-size blocks cannot move.

REJECTED: prevalence alone inflates recall. Test prevalence 0.085512; constant test scores give 0.100007. Constant training targets at prevalence 0.025700 produce recall 0.649042. The fitting procedure can rank positives without session-specific training labels.

INCONCLUSIVE: chronological training selection. Reversing the same shuffled training pairs gives recall 0.649042; holding the sample fixed cannot test collection-time confounding.

REJECTED: stable rather than random boundary ties explain the high control. Stable selection 0.634992, seeded random ties 0.649263.



2025-07-07: 2196/48645 complete command sessions have a counter at or after first command.

2025-08-03: 15237/50608 complete command sessions have a counter at or after first command.

2025-08-09: 13063/85130 complete command sessions have a counter at or after first command.



These counts show aggregate feature look-ahead relative to the first command. The event study uses first session.params as a proxy and includes timestamp ties. Raw events lack an authenticated per-session runtime decision boundary. Exact S3 prefix scores and recall: NOT RUN.



The mechanical gate result is exploratory. These controls do not establish validated pre-command triage.
