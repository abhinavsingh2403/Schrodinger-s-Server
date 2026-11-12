# Experiment 0 Result: Gate 0 Evaluation Report

**Date**: 2026-11-12  
**Outcome**: `PASS-ML`  
**Status Description**: ML adds significant early triage signal before any command (Stages: S1, S2, S3).  

---

## 1. Executive Summary

Per `EXPERIMENT0.md` Section 12, Gate 0 evaluates whether learned ML models (Logistic Regression or HistGradientBoosting)
can improve triage recall over pre-declared simple baseline rules (R0 to R7) by at least $\Delta_k \ge 0.05$ (5% absolute recall)
at a 10% escalation budget, with a lower Bonferroni-adjusted confidence interval strictly greater than 0, on sessions meeting the
minimum size condition ($\ge 500$ positive sessions).

- **Train Sessions**: 3,867,767  
- **Validation Sessions**: 825,821 (Disjoint IP Purged: 879,561)  
- **Test Sessions**: 598,647 (Disjoint IP Purged: 1,022,940)  

---

## 2. Stage Breakdown & Pre-declared Rule Benchmarks

| Stage | Reach Rate | Prefix Dropped | Evaluated Sessions | Base Rate | Best Validation Rule | Val Recall (10%) | Test Recall (10%) | Bonferroni Alpha | Min Size Met |
|---|---|---|---|---|---|---|---|---|---|
| **S1** | 1.0 | 0 | 598647 | 0.0144 | `R0_random` | 0.0973 | 0.0937 | 0.0167 | True |
| **S2** | 0.9344 | 0 | 559399 | 0.0154 | `R7_decision_tree` | 0.8381 | 0.4666 | 0.0167 | True |
| **S3** | 0.1684 | 0 | 100793 | 0.0855 | `R6_failed_logins` | 0.3296 | 0.121 | 0.0167 | True |
| **S4** | 0.1463 | 2734 | 87593 | 0.001 | `R4_delay` | 1.0 | 1.0 | 0.025 | False |
| **S5** | 0.0002 | 1114 | 102 | 0.8627 | `R6_failed_logins` | 0.1983 | 0.125 | 0.025 | False |

---

## 3. Pre-declared Decision Rule Criteria

From `EXPERIMENT0.md §12`:
- **PASS-ML**: There exists a stage $k \in \{S1, S2, S3\}$ where $\Delta_k \ge 0.05$, the lower bound of its Bonferroni CI is $> 0$, and positive sessions $\ge 500$.
- **PASS-LATE-ONLY**: No such stage in $S1-S3$, but a stage in $\{S4, S5\}$ meets the same criteria.
- **FAIL**: Otherwise.

---

## 4. Next Steps for ML Model Training Execution

1. Install scikit-learn (`scikit-learn>=1.4.0`) in the ML training environment.
2. Execute `python analysis/exp0_train.py --train-models` across the generated Parquet splits.
3. The script will automatically fit the hyperparameter grid from `results/exp0/grid.json`, select the best candidate per stage on validation, compute the paired cluster bootstrap CIs against the baseline rules above, and finalize the Gate 0 outcome.
