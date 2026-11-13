# S3 robustness audit (reporting only)

Test-selected baseline sensitivity: **robust**.

Saved export reproduces the official S3 point recall after stage filtering. Official outcome is unchanged.

| Rule | Validation recall | Test recall | ML minus rule | Adjusted CI |
|---|---:|---:|---:|---|
| R0_random | 0.09760026 | 0.10291217 | 0.18900104 | [0.0064, 0.6416] |
| R1_login_success | 0.09760026 | 0.10291217 | 0.18900104 | [0.0091, 0.6434] |
| R2_pty_requested | 0.09507704 | 0.10395638 | 0.18795684 | [0.0088, 0.6401] |
| R5_rarity — PROXY (aggregate counter, not version string) | 0.09760026 | 0.10291217 | 0.18900104 | [0.0091, 0.6434] |
| R6_failed_logins | 0.33381650 | 0.11509456 | 0.17681866 | [0.0052, 0.6125] |
| R7_decision_tree | 0.33199120 | 0.11613876 | 0.17577445 | [0.0049, 0.61] |

ML measurements: `{"val": 0.4480055832930692, "test": 0.29191321499013806, "difference_from_official": 1.3214990138066263e-05, "generalisation_gap": -0.15609236830293116}`

Baseline chosen on test for sensitivity only: R7_decision_tree

Model-family comparison: HistGradientBoosting NOT RUN (absent in the manifest-matching environment).
The stored winning C is the lowest declared grid value; no grid expansion was performed.

Component capture:
```json
{
  "direct-tcpip": {
    "positives": 5759,
    "captured": 0,
    "recall": 0.0
  },
  "commands": {
    "positives": 88,
    "captured": 5,
    "recall": 0.056818181818181816
  },
  "transfer": {
    "positives": 1745,
    "captured": 1520,
    "recall": 0.8710601719197708
  },
  "commands+transfer": {
    "positives": 1027,
    "captured": 991,
    "recall": 0.9649464459591042
  }
}
```

Captured positives are overwhelmingly transfer-labelled; this does not establish interactive-attacker prediction.

## Bootstrap interpretation

There was a reproducibility bug: unordered cluster iteration made fixed-seed draws change between processes. Sorting cluster IDs fixes it; the wide S3 interval remains.
At S3, the largest 13 clusters contain 83.99% of sessions and 53.05% of positives. Drawing these clusters repeatedly or omitting them substantially changes both the available budget and the positive denominator. This concentration explains why the distribution is broad and asymmetric.
S2 has exact equal-recall draws, so its upper endpoint can be zero without identical score vectors.

| Stage | Full CI | Excluding largest clusters CI | Weight cap | Capped CI | Median delta | Draws below zero | Above 0.3 | Above 0.5 | Exact zero |
|---|---|---|---:|---|---:|---:|---:|---:|---:|
| S2 | [-0.0418, 0.0] | [0.0, 0.0] | 6149 | [-0.0384, 0.0] | -0.01256295 | 8808 | 0 | 0 | 1192 |
| S3 | [0.0052, 0.6125] | [0.1961, 0.3966] | 362 | [0.2371, 0.5105] | 0.18820693 | 50 | 3716 | 1761 | 0 |

Weight caps use the nearest-rank percentile of cluster size; each cluster contribution is scaled proportionally. These sensitivities change the population weighting and are not alternate official outcomes.
Official bootstrap averages capture within tied score bins, while reported point recall uses fixed random tie-breaking. This audit retains that statistic; it is not an exact bootstrap of the fixed-tie point estimator.

## Artifact interpretation

The shuffled-label model has recall 0.65053951, which fails the requested near-budget sanity check. This is a leakage/bug signal requiring investigation; it is not sufficient by itself to identify its cause.
Removing session parameters reduces recall to 0.10256410. The sampled log contains parameter events after commands; whole-session counters therefore cannot be assumed to represent only a pre-command prefix.
The positive gain comes from transfer-only sessions and command/transfer overlaps. Performance is worse than the baseline on command-only and direct-tcpip-only positives.

## Leakage and ablations

```json
{
  "seed": 20261111,
  "model": "PurePythonLogisticRegression",
  "checks": {
    "refit": {
      "dropped": [],
      "test_recall": 0.29191321499013806
    },
    "shuffle": {
      "dropped": [],
      "test_recall": 0.6505395057431257
    },
    "cnt_client_size": {
      "dropped": [
        "cnt_client_size"
      ],
      "test_recall": 0.29191321499013806
    },
    "cnt_client_var": {
      "dropped": [
        "cnt_client_var"
      ],
      "test_recall": 0.29191321499013806
    },
    "cnt_session_params": {
      "dropped": [
        "cnt_session_params"
      ],
      "test_recall": 0.10256410256410256
    },
    "all_three": {
      "dropped": [
        "cnt_client_size",
        "cnt_client_var",
        "cnt_session_params"
      ],
      "test_recall": 0.10175194338090265
    }
  },
  "event_order": "See event_order.json for the separately executed bounded single-day range check; aggregate prefix validity remains unverified.",
  "scope": "Same saved-model hyperparameters and official training-sample loader. Reporting only; no model selection on test.",
  "shuffle_interpretation": "A shuffled-label recall far from the budget is a diagnostic signal, not proof of leakage; inspect finite-sample ties and distribution shift.",
  "component_gain": {
    "commands": {
      "positives": 88,
      "share_of_positives": 0.010210001160227404,
      "ml_captured": 5,
      "rule_captured": 84,
      "ml_recall": 0.056818181818181816,
      "delta_contribution_to_overall_recall": -0.009165796496113238
    },
    "commands+transfer": {
      "positives": 1027,
      "share_of_positives": 0.1191553544494721,
      "ml_captured": 991,
      "rule_captured": 141,
      "ml_recall": 0.9649464459591042,
      "delta_contribution_to_overall_recall": 0.09861932938856016
    },
    "direct-tcpip": {
      "positives": 5759,
      "share_of_positives": 0.6681749622926093,
      "ml_captured": 0,
      "rule_captured": 600,
      "ml_recall": 0.0,
      "delta_contribution_to_overall_recall": -0.06961364427427776
    },
    "transfer": {
      "positives": 1745,
      "share_of_positives": 0.20245968209769113,
      "ml_captured": 1520,
      "rule_captured": 167,
      "ml_recall": 0.8710601719197708,
      "delta_contribution_to_overall_recall": 0.15697876783849635
    }
  }
}
```

## Observed event order

```json
{
  "sampled_day": "../logs_by_day/2025-06-27.json.gz",
  "sample_events": 679,
  "order": {
    "cowrie.client.size": {
      "before_first_command": 0,
      "after_first_command": 0,
      "sessions_with_command_and_feature": 0
    },
    "cowrie.client.var": {
      "before_first_command": 0,
      "after_first_command": 0,
      "sessions_with_command_and_feature": 0
    },
    "cowrie.session.params": {
      "before_first_command": 37,
      "after_first_command": 2,
      "sessions_with_command_and_feature": 37
    }
  },
  "limitation": "Partial one-day stream; ordering is stored log order, not independently timestamp-validated chronology. It is not a guarantee that whole-session counters are prefix-only. TODO(verify): complete per-session prefix comparison."
}
```

## Bootstrap diagnostics

```json
{
  "seed": 20261111,
  "stages": {
    "S2": {
      "clusters": 1643,
      "concentration": {
        "top_1": {
          "clusters": 1,
          "sessions": 31314,
          "positives": 0,
          "session_share": 0.05597793346073197,
          "positive_share": 0.0
        },
        "top_10": {
          "clusters": 10,
          "sessions": 205049,
          "positives": 0,
          "session_share": 0.3665523177553052,
          "positive_share": 0.0
        },
        "top_one_percent": {
          "clusters": 17,
          "sessions": 258482,
          "positives": 4572,
          "session_share": 0.4620709010920649,
          "positive_share": 0.5304559693699965
        }
      },
      "full": {
        "point_delta": -0.0133,
        "ci": [
          -0.0418,
          0.0
        ],
        "median": -0.012562953402765031,
        "draws": 10000,
        "below_zero": 8808,
        "above_point_three": 0,
        "above_point_five": 0,
        "exact_zero": 1192
      },
      "exclude_top_one_percent": {
        "point_delta": 0.0,
        "ci": [
          0.0,
          0.0
        ],
        "median": 0.0,
        "draws": 10000,
        "below_zero": 0,
        "above_point_three": 0,
        "above_point_five": 0,
        "exact_zero": 10000
      },
      "weight_cap": 6149,
      "capped": {
        "point_delta": -0.0133,
        "ci": [
          -0.0384,
          0.0
        ],
        "median": -0.006661497827850027,
        "draws": 10000,
        "below_zero": 6074,
        "above_point_three": 0,
        "above_point_five": 0,
        "exact_zero": 3924,
        "point_delta_note": "Point delta is the original unweighted point; CI and median use capped cluster weights."
      }
    },
    "S3": {
      "clusters": 1213,
      "concentration": {
        "top_1": {
          "clusters": 1,
          "sessions": 31313,
          "positives": 0,
          "session_share": 0.31066641532646116,
          "positive_share": 0.0
        },
        "top_10": {
          "clusters": 10,
          "sessions": 83480,
          "positives": 4572,
          "session_share": 0.8282321192939985,
          "positive_share": 0.5304559693699965
        },
        "top_one_percent": {
          "clusters": 13,
          "sessions": 84654,
          "positives": 4572,
          "session_share": 0.8398797535543143,
          "positive_share": 0.5304559693699965
        }
      },
      "full": {
        "point_delta": 0.1768,
        "ci": [
          0.0052,
          0.6125
        ],
        "median": 0.18820693168474606,
        "draws": 10000,
        "below_zero": 50,
        "above_point_three": 3716,
        "above_point_five": 1761,
        "exact_zero": 0
      },
      "exclude_top_one_percent": {
        "point_delta": 0.2802,
        "ci": [
          0.1961,
          0.3966
        ],
        "median": 0.2798524396699166,
        "draws": 10000,
        "below_zero": 0,
        "above_point_three": 3161,
        "above_point_five": 0,
        "exact_zero": 0
      },
      "weight_cap": 362,
      "capped": {
        "point_delta": 0.1768,
        "ci": [
          0.2371,
          0.5105
        ],
        "median": 0.35437619002470727,
        "draws": 10000,
        "below_zero": 0,
        "above_point_three": 8449,
        "above_point_five": 109,
        "exact_zero": 0,
        "point_delta_note": "Point delta is the original unweighted point; CI and median use capped cluster weights."
      }
    }
  },
  "bug": "Fixed process-dependent cluster ordering by sorting cluster IDs. Regression test failed before fix.",
  "method_caveat": "Official bootstrap averages capture within tied score bins, while reported point recall uses fixed random tie-breaking. This audit retains that statistic; it is not an exact bootstrap of the fixed-tie point estimator."
}
```

## Candidate family comparison

```json
{
  "implementation": "PurePythonLogisticRegression fallback, not sklearn LogisticRegression",
  "candidates": [
    {
      "C": 0.01,
      "validation_recall": 0.4480055832930692,
      "test_recall": 0.29191321499013806
    },
    {
      "C": 0.1,
      "validation_recall": 0.4480055832930692,
      "test_recall": 0.29191321499013806
    },
    {
      "C": 1.0,
      "validation_recall": 0.4480055832930692,
      "test_recall": 0.29191321499013806
    },
    {
      "C": 10.0,
      "validation_recall": 0.4480055832930692,
      "test_recall": 0.29191321499013806
    }
  ],
  "best_lr": {
    "C": 0.01,
    "validation_recall": 0.4480055832930692,
    "test_recall": 0.29191321499013806
  },
  "boundary": true,
  "hist_gradient_boosting": "NOT RUN: absent in manifest-matching environment; no historical family winner recoverable for the current result",
  "grid_audit": "The sklearn branch ignores max_leaf_nodes and min_samples_leaf grid dimensions. Not changed: pre-registered candidate changes require human review."
}
```
