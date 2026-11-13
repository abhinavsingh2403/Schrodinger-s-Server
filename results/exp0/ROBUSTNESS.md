# S3 robustness audit (reporting only)

TBD: official model identity unverified; no robustness verdict justified

Loaded the saved export; these measurements do not establish official-model identity.

| Model/rule | Validation recall | Test recall |
|---|---:|---:|
| Saved export | 0.44800558 | 0.29191321 |
| R0_random | 0.09760026 | 0.10291217 |
| R1_login_success | 0.09760026 | 0.10291217 |
| R2_pty_requested | 0.09507704 | 0.10395638 |
| R5_rarity — PROXY (aggregate counter, not version string) | 0.09760026 | 0.10291217 |
| R6_failed_logins | 0.33381650 | 0.11509456 |
| R7_decision_tree | 0.33199120 | 0.11613876 |

Saved-export test recall minus official row: 0.00001321

Disjoint positive label-component counts:
```json
{
  "direct-tcpip": 5759,
  "commands": 88,
  "transfer": 1745,
  "commands+transfer": 1027
}
```

TODO(verify): recover the exact official training sample/model; DuckDB reservoir sample has a seed but no persisted sample IDs or row order.
Export script retrains independently and calibrates on unfiltered validation sessions; official harness filters validation/test by stage.
TODO(verify): official model-family comparison; project environment lacks scikit-learn, so its fallback skips HistGradientBoosting.
CI comparisons, shuffle and ablations of the official model are withheld until model identity is established.

## Paired bootstrap and label components

Reporting-only test-selected baseline verdict: robust

```json
{
  "model_source": "loaded results/exp0/model_s3.json; separately retrained export",
  "official_row": {
    "stage": "S3",
    "reach_rate": "0.1684",
    "dropped_prefix": "0",
    "evaluated_sessions": "100793",
    "base_rate": "0.0855",
    "best_rule": "R6_failed_logins",
    "best_rule_val_recall": "0.3338",
    "best_rule_test_recall": "0.1151",
    "ml_candidate": "LogisticRegression(C=0.01)",
    "ml_test_recall": "0.2919",
    "delta_k": "0.1768",
    "ci_lower": "0.0045",
    "ci_upper": "0.619",
    "bonferroni_alpha": "0.0167",
    "min_size_met": "True"
  },
  "rules": {
    "R0_random": {
      "val": 0.09760025769044935,
      "test": 0.10291217078547395,
      "delta_exported_ml": 0.18900104420466413,
      "generalisation_gap": 0.005311913095024601,
      "bootstrap": [
        0.189,
        0.0068,
        0.6465
      ]
    },
    "R1_login_success": {
      "val": 0.09760025769044935,
      "test": 0.10291217078547395,
      "delta_exported_ml": 0.18900104420466413,
      "generalisation_gap": 0.005311913095024601,
      "bootstrap": [
        0.1885,
        0.0095,
        0.6484
      ]
    },
    "R2_pty_requested": {
      "val": 0.09507703870725291,
      "test": 0.10395637544958812,
      "delta_exported_ml": 0.18795683954054992,
      "generalisation_gap": 0.008879336742335209,
      "bootstrap": [
        0.188,
        0.0093,
        0.6458
      ]
    },
    "R5_rarity": {
      "val": 0.09760025769044935,
      "test": 0.10291217078547395,
      "delta_exported_ml": 0.18900104420466413,
      "generalisation_gap": 0.005311913095024601,
      "bootstrap": [
        0.1885,
        0.0095,
        0.6484
      ]
    },
    "R6_failed_logins": {
      "val": 0.3338165029258603,
      "test": 0.11509455853347256,
      "delta_exported_ml": 0.1768186564566655,
      "generalisation_gap": -0.21872194439238773,
      "bootstrap": [
        0.1768,
        0.0058,
        0.6181
      ]
    },
    "R7_decision_tree": {
      "val": 0.33199119557631396,
      "test": 0.11613876319758673,
      "delta_exported_ml": 0.17577445179255133,
      "generalisation_gap": -0.21585243237872723,
      "bootstrap": [
        0.1759,
        0.0055,
        0.6156
      ]
    }
  },
  "ml": {
    "val": 0.4480055832930692,
    "test": 0.29191321499013806,
    "difference_from_official": 1.3214990138066263e-05
  },
  "seed": 42,
  "label_components": {
    "direct-tcpip": 5759,
    "commands": 88,
    "transfer": 1745,
    "commands+transfer": 1027
  },
  "identity_verified": true,
  "verdict": "robust",
  "limitations": [
    "TODO(verify): recover the exact official training sample/model; DuckDB reservoir sample has a seed but no persisted sample IDs or row order.",
    "Export script retrains independently and calibrates on unfiltered validation sessions; official harness filters validation/test by stage.",
    "TODO(verify): official model-family comparison; project environment lacks scikit-learn, so its fallback skips HistGradientBoosting.",
    "CI comparisons, shuffle and ablations of the official model are withheld until model identity is established."
  ],
  "component_recall": {
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
  },
  "test_selected_baseline": "R7_decision_tree"
}
```

## Leakage and artifact checks

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
  "event_order": "TODO(verify): stored schema summary does not preserve per-session event order; no new download performed under R6.",
  "scope": "Same saved-model hyperparameters and official training-sample loader. Reporting only; no model selection on test.",
  "shuffle_interpretation": "A shuffled-label recall far from the budget is a diagnostic signal, not proof of leakage; inspect finite-sample ties and distribution shift."
}
```
