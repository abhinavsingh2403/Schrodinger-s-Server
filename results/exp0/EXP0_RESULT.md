# Experiment 0 Result: Gate 0 Evaluation Report

**Date**: 2026-11-13  
**Outcome**: `PASS-ML`  
**Status Description**: Mechanical outcome of the pre-declared rule. Exploratory: aggregate-only features, transfer-labelled sessions dominate the gain, a shuffled-label diagnostic and event-order checks are unresolved; see ROBUSTNESS.md and AUDIT.md. Not validated as a pre-command signal.  

---

R5_rarity (and R3_interactive where present): PROXY (aggregate counter, not version string). Version-string and hassh rarity were not evaluated.
This aggregate-only result follows analysis changes made with test results visible; present it as exploratory-confirmatory. See ROBUSTNESS.md for reporting-only diagnostics.

## 1. Executive Summary

Per `EXPERIMENT0.md` Section 12, Gate 0 evaluates whether learned ML models (Logistic Regression or HistGradientBoosting)
can improve triage recall over pre-declared simple baseline rules (R0 to R7) by at least $\Delta_k \ge 0.05$ (5% absolute recall)
at a 10% escalation budget, with a lower Bonferroni-adjusted confidence interval strictly greater than 0, on sessions meeting the
minimum size condition ($\ge 500$ positive sessions).

- **Train Sessions**: 3,867,767  
- **Validation Sessions**: 825,821 (Disjoint IP Purged: 879,561)  
- **Test Sessions**: 598,647 (Disjoint IP Purged: 1,022,940)  

---

## 2. Stage Breakdown & Pre-declared Benchmarks (Rules vs. ML Candidates)

| Stage | Reach Rate | Prefix Dropped | Evaluated Sessions | Base Rate | Best Rule | Rule Recall (10%) | ML Candidate | ML Recall (10%) | Δ_k | Multiplicity-Adj CI | Min Size Met |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1** | 1.0 | 0 | 598647 | 0.0144 | `R0_random` | 0.097 | `LogisticRegression(C=0.01)` | 0.0596 | -0.0374 | [-0.0937, -0.0109] | True |
| **S2** | 0.9344 | 0 | 559399 | 0.0154 | `R7_decision_tree` | 0.5609 | `LogisticRegression(C=0.01)` | 0.5477 | -0.0132 | [-0.0418, 0.0] | True |
| **S3** | 0.1684 | 0 | 100793 | 0.0855 | `R6_failed_logins` | 0.1118 | `LogisticRegression(C=0.01)` | 0.292 | 0.1802 | [0.0052, 0.6125] | True |
| **S4** | N/A | N/A | N/A | N/A | `NOT_EVALUABLE (Requires event-level data_all)` | N/A | `NOT_EVALUABLE (Requires event-level data_all)` | N/A | NOT_EVALUABLE | N/A | False |
| **S5** | N/A | N/A | N/A | N/A | `NOT_EVALUABLE (Requires event-level data_all)` | N/A | `NOT_EVALUABLE (Requires event-level data_all)` | N/A | NOT_EVALUABLE | N/A | False |

---

## 3. Pre-declared Decision Rule Criteria

From `EXPERIMENT0.md §12`:
- **PASS-ML**: There exists a stage $k \in \{S1, S2, S3\}$ where $\Delta_k \ge 0.05$, the lower bound of its Bonferroni CI is $> 0$, and positive sessions $\ge 500$.
- **PASS-LATE-ONLY**: No such stage in $S1-S3$, but a stage in $\{S4, S5\}$ meets the same criteria.
- **FAIL**: Otherwise.

---

## 4. Scientific Interpretation, Leakage Audit & Gate 0 Verdict

1. **Gate 0 Decision**: `PASS-ML` (Stages: S3).
   - The numeric rule passes; scientific interpretation remains exploratory/inconclusive. Aggregate timing, permutation controls, cluster concentration and incomplete model families prevent a validated pre-command claim.


## Complete Escalation-Budget Evaluation Metrics (Stage S3)

Comparison of Stage S3 ML Classifier (`LogisticRegression(C=0.01)`) against pre-declared baseline rules across 1%, 5%, 10%, and 20% escalation budgets on identical held-out test sessions ($N=100,793$, $P=8,619$).

| Escalation Budget | Method | Precision | Recall | F1-Score | FPR | Confusion Matrix (TP / FP / FN / TN) | PR-AUC |
|---|---|---:|---:|---:|---:|---|---:|
| **1%** (1,008 sessions) | **ML: LogisticRegression** | **0.8433** | **0.0986** | **0.1766** | **0.0017** | `850 / 158 / 7769 / 92016` | **0.2584** |
| 1% | Rule: R7 Decision Tree | 0.1280 | 0.0150 | 0.0268 | 0.0095 | `129 / 879 / 8490 / 91295` | 0.1013 |
| 1% | Rule: R6 Failed Logins | 0.1071 | 0.0125 | 0.0224 | 0.0098 | `108 / 900 / 8511 / 91274` | 0.0984 |
| 1% | Baseline: R0 Uniform Random | 0.0855 | 0.0100 | 0.0179 | 0.0100 | `86 / 922 / 8533 / 91252` | 0.0855 |
| **5%** (5,040 sessions) | **ML: LogisticRegression** | **0.4266** | **0.2495** | **0.3148** | **0.0314** | `2150 / 2890 / 6469 / 89284` | **0.2584** |
| 5% | Rule: R7 Decision Tree | 0.1042 | 0.0609 | 0.0769 | 0.0490 | `525 / 4515 / 8094 / 87659` | 0.1013 |
| 5% | Rule: R6 Failed Logins | 0.0990 | 0.0579 | 0.0731 | 0.0493 | `499 / 4541 / 8120 / 87633` | 0.0984 |
| 5% | Baseline: R0 Uniform Random | 0.0855 | 0.0500 | 0.0631 | 0.0500 | `431 / 4609 / 8188 / 87565` | 0.0855 |
| **10%** (10,080 sessions) | **ML: LogisticRegression** | **0.2496** | **0.2920** | **0.2692** | **0.0821** | `2516 / 7564 / 6103 / 84610` | **0.2584** |
| 10% | Rule: R7 Decision Tree | 0.0964 | 0.1128 | 0.1040 | 0.0988 | `972 / 9108 / 7647 / 83066` | 0.1013 |
| 10% | Rule: R6 Failed Logins | 0.0956 | 0.1118 | 0.1031 | 0.0989 | `964 / 9116 / 7655 / 83058` | 0.0984 |
| 10% | Baseline: R0 Uniform Random | 0.0855 | 0.1000 | 0.0922 | 0.1000 | `862 / 9218 / 7757 / 82956` | 0.0855 |
| **20%** (20,159 sessions) | **ML: LogisticRegression** | **0.1596** | **0.3734** | **0.2237** | **0.1838** | `3218 / 16941 / 5401 / 75233` | **0.2584** |
| 20% | Rule: R7 Decision Tree | 0.0946 | 0.2213 | 0.1325 | 0.1980 | `1907 / 18252 / 6712 / 73922` | 0.1013 |
| 20% | Rule: R6 Failed Logins | 0.0934 | 0.2185 | 0.1309 | 0.1983 | `1883 / 18276 / 6736 / 73898` | 0.0984 |
| 20% | Baseline: R0 Uniform Random | 0.0855 | 0.2000 | 0.1198 | 0.2000 | `1724 / 18435 / 6895 / 73739` | 0.0855 |

### Key metric observations (descriptive, exploratory)
1. At 1%, ML selected 1,008 sessions including 850 positives (precision 0.8433). R7 selected 129 positives and R6 selected 108.
2. At 10%, recall was ML 0.2920, R7 0.1128, R6 0.1118 and random 0.1000.
3. PR-AUC was ML 0.2584, R7 0.1013, R6 0.0984 and random 0.0855.
4. Precision-recall curves: [`curves.png`](curves.png).

Exploratory. The shuffled-label control recall (0.649, see results/exp0/PERMUTATION_NULL.md) exceeds the observed ML recall (0.292), and the gain is concentrated in transfer-labelled sessions (see results/exp0/ROBUSTNESS.md). This table does not establish a validated pre-command signal.
