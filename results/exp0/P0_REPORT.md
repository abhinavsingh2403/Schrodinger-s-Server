# P0 metric and permutation audit

The old seeded metric selected exactly the ceiling budget and passed the new invariants before modification. No tie-bin overflow was found. Its point estimator differed from the tie-averaged bootstrap. Both now use one expected uniform boundary-tie estimator, selected in DECISIONS.md before rerunning.

Root-cause evidence: the fallback optimizer starts with zero weights and intercept (initial probability one-half). With rare training positives, finite gradient iterations give common counters persistent negative weights. A diagnostic fit using the same training prevalence for every label reproduces the shuffled model recall, without any label-to-row association. Thus permuting training labels does not make test rankings uniformly random. This control is not an official candidate; the optimizer, grid, labels and splits were not changed.

| Stage | Old rule | New rule | Old ML | New ML | Old delta | New delta | Old CI | New CI |
|---|---|---|---|---|---|---|---|---|
| S1 | 0.097 | 0.097 | 0.0572 | 0.0596 | -0.0398 | -0.0374 | [-0.0937, -0.0109] | [-0.0937, -0.0109] |
| S2 | 0.5632 | 0.5609 | 0.5497 | 0.5477 | -0.0135 | -0.0132 | [-0.0418, 0.0] | [-0.0418, 0.0] |
| S3 | 0.1151 | 0.1118 | 0.2919 | 0.292 | 0.1768 | 0.1802 | [0.0052, 0.6125] | [0.0052, 0.6125] |
| S4 | N/A | N/A | N/A | N/A | NOT_EVALUABLE | NOT_EVALUABLE | [N/A, N/A] | [N/A, N/A] |
| S5 | N/A | N/A | N/A | N/A | NOT_EVALUABLE | NOT_EVALUABLE | [N/A, N/A] | [N/A, N/A] |

Exact generated Gate 0 result:
```json
{
  "gate0_outcome": "PASS-ML",
  "delta_threshold": 0.05,
  "passing_early_stages": [
    "S3"
  ],
  "passing_late_stages": [],
  "interpretation": "Mechanical PASS-ML (Stages: S3); exploratory/inconclusive, not validated pre-command signal."
}
```

Numerical PASS does not establish validated early signal. The shuffled-label control outperforms the observed model, the candidate family set is incomplete, clusters are concentrated, and aggregate counters do not establish temporal availability.

Null distribution and descriptive empirical tail (not a calibrated significance test):
```json
{
  "status": "COMPLETE",
  "observed_recall": 0.2919661602320823,
  "scope": "Fixed saved-model hyperparameters; session-wise training-label shuffle only; no grid selection or official-outcome change.",
  "caveat": "Descriptive diagnostic, not a calibrated clustered permutation significance test.",
  "minimum": 0.649042308621446,
  "maximum": 0.6494942557289106,
  "mean": 0.6490978331149052,
  "median": 0.649042308621446,
  "at_or_above_observed": 200,
  "exceedance_fraction": 1.0,
  "empirical_upper_tail_plus_one": 1.0,
  "standard_deviation": 0.00014697767223174343
}
```

Score-bin and exact-budget diagnostics:
```json
{
  "estimators": {
    "official": {
      "sessions": 100793,
      "positives": 8619,
      "unique_scores": 46,
      "largest_bin": 87679,
      "selected": 10080,
      "recall": 0.2919661602320823,
      "direct_selection_recall": 0.29191321499013806
    },
    "shuffled": {
      "sessions": 100793,
      "positives": 8619,
      "unique_scores": 46,
      "largest_bin": 87679,
      "selected": 10080,
      "recall": 0.649042308621446,
      "direct_selection_recall": 0.6505395057431257
    },
    "constant_prevalence_gradient_control": {
      "sessions": 100793,
      "positives": 8619,
      "unique_scores": 46,
      "largest_bin": 87679,
      "selected": 10080,
      "recall": 0.649042308621446,
      "direct_selection_recall": 0.6505395057431257
    },
    "R6_failed_logins": {
      "sessions": 100793,
      "positives": 8619,
      "unique_scores": 15,
      "largest_bin": 100615,
      "selected": 10080,
      "recall": 0.11180411140934465,
      "direct_selection_recall": 0.11509455853347256
    },
    "R7_decision_tree": {
      "sessions": 100793,
      "positives": 8619,
      "unique_scores": 4,
      "largest_bin": 100604,
      "selected": 10080,
      "recall": 0.1127727163505002,
      "direct_selection_recall": 0.11613876319758673
    }
  },
  "training_prevalence": 0.0257,
  "shuffled_training_mean_prediction": 0.035152841239331496,
  "shuffled_weights": [
    0.0,
    -1.4182289968659478,
    -0.6749789545801937,
    -0.0031897352089822074,
    -0.05962538015322988,
    -0.18726753898661166,
    -0.00039055866459686045,
    0.0,
    -0.0017095935465809707
  ],
  "control_weights": [
    0.0,
    -1.4175297221758154,
    -0.6756178644695676,
    -0.003268089780195317,
    -0.060144371530286254,
    -0.1801949163353649,
    -0.0002453099306309723,
    0.0,
    -0.0016854207156306036
  ],
  "control_is_candidate": false
}
```

TODO(verify): optimizer convergence and a scientifically valid clustered null require a separately authorized experiment; event-level availability is evaluated separately in P4.
