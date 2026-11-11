# Experiment 0 Result: Gate 0 Evaluation Report

**Date**: 2026-11-12  
**Outcome**: `PENDING_ML_TRAINING`  
**Status Description**: Baseline simple rules frozen across all stages. Awaiting friend's ML model training execution.  

---

## 1. Executive Summary

Per `EXPERIMENT0.md` Section 12, Gate 0 evaluates whether learned ML models (Logistic Regression or HistGradientBoosting)
can improve triage recall over pre-declared simple baseline rules (R0 to R7) by at least $\Delta_k \ge 0.05$ (5% absolute recall)
at a 10% escalation budget, with a lower Bonferroni-adjusted confidence interval strictly greater than 0, on sessions meeting the
minimum size condition ($\ge 500$ positive sessions).

- **Train Sessions**: 10,000  
- **Validation Sessions**: 10,000 (Disjoint IP Purged: 1,695,382)  
- **Test Sessions**: 10,000 (Disjoint IP Purged: 1,611,587)  

---

## 2. Stage Breakdown & Pre-declared Rule Benchmarks

| Stage | Reach Rate | Prefix Dropped | Evaluated Sessions | Base Rate | Best Validation Rule | Val Recall (10%) | Test Recall (10%) | Bonferroni Alpha | Min Size Met |
|---|---|---|---|---|---|---|---|---|---|
| **S1** | 1.0 | 0 | 10000 | 0.0207 | `R0_random` | 0.119 | 0.0676 | 0.0167 | False |
| **S2** | 0.9409 | 0 | 9409 | 0.022 | `R1_login_success` | 1.0 | 1.0 | 0.0167 | False |
| **S3** | 0.0756 | 0 | 756 | 0.2738 | `R6_failed_logins` | 0.2095 | 0.1111 | 0.0167 | False |
| **S4** | 0.0385 | 173 | 385 | 0.0078 | `R4_delay` | 1.0 | 1.0 | 0.025 | False |
| **S5** | 0.0003 | 56 | 3 | 1.0 | `R0_random` | 0.5 | 0.3333 | 0.025 | False |

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
