# Experiment 0 Result: Gate 0 Evaluation Report

**Date**: 2026-11-13  
**Outcome**: `PASS-ML`  
**Status Description**: ML adds significant early triage signal before any command (Stages: S3).  

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
| **S1** | 1.0 | 0 | 598647 | 0.0144 | `R0_random` | 0.097 | `LogisticRegression(C=0.01)` | 0.0572 | -0.0398 | [-0.0937, -0.0109] | True |
| **S2** | 0.9344 | 0 | 559399 | 0.0154 | `R7_decision_tree` | 0.5632 | `LogisticRegression(C=0.01)` | 0.5497 | -0.0135 | [-0.0418, 0.0] | True |
| **S3** | 0.1684 | 0 | 100793 | 0.0855 | `R6_failed_logins` | 0.1151 | `LogisticRegression(C=0.01)` | 0.2919 | 0.1768 | [0.0052, 0.6125] | True |
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
   - Early stage ML demonstrates statistically significant recall improvement over simple rules.
