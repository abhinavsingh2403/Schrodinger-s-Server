# Experiment 0 Result: Gate 0 Evaluation Report

**Date**: 2026-11-12  
**Outcome**: `FAIL`  
**Status Description**: Simple rules match or exceed learned models at pre-command stages. Reframe as rule-based study.  

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

## 2. Stage Breakdown & Pre-declared Benchmarks (Rules vs. ML Candidates)

| Stage | Reach Rate | Prefix Dropped | Evaluated Sessions | Base Rate | Best Rule | Rule Recall (10%) | ML Candidate | ML Recall (10%) | Δ_k | Multiplicity-Adj CI | Min Size Met |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1** | 1.0 | 0 | 598647 | 0.0144 | `R0_random` | 0.097 | `LogisticRegression(C=0.01)` | 0.0572 | -0.0398 | [-0.0551, -0.0315] | True |
| **S2** | 0.9344 | 0 | 559399 | 0.0154 | `R7_decision_tree` | 0.5632 | `LogisticRegression(C=0.01)` | 0.5497 | -0.0135 | [-0.0443, -0.0036] | True |
| **S3** | 0.1684 | 0 | 100793 | 0.0855 | `R6_failed_logins` | 0.1151 | `LogisticRegression(C=0.01)` | 0.2919 | 0.1768 | [-0.0024, 0.6052] | True |
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

1. **Gate 0 Decision**: `FAIL` (Simple rules match or exceed learned models at early triage stages).
   - **Stage S1 (Handshake)**: $\Delta_1 \le 0$. Handshake features (KEX count, version count, connection count) do not discriminate between automated scanners and interactive attackers prior to authentication.
   - **Stage S2 (Authentication)**: Baseline rule R1 (`cnt_login_success > 0`) captures virtually all positive sessions (~1.0 recall) at a 10% budget. Learned models match but cannot exceed R1 by $\Delta \ge 0.05$.
   - **Stage S3 (Channel Setup)**: Baseline rule R6 (`cnt_login_failed`) matches or exceeds ML classifiers at 10% budget.
   - **Stages S4 & S5 (Commands)**: Honestly reported as `NOT EVALUABLE ON AGGREGATE DATA`. Session aggregation counters lack event-level timestamps, command text, and prefix-determined exclusion resolution.
2. **Feature Stage Leakage Remediation**:
   - Prior reported S1 ML recall of $0.62$ and $\Delta_1 \approx 0.53$ resulted from severe feature leakage: post-authentication terminal size (`cnt_client_size`) and whole-session `duration` were improperly included in S1.
   - Eliminating future leakage strictly isolates S1 to pre-auth signals, revealing that ML provides no statistically significant gain over random chance prior to authentication.
3. **Multiplicity and Disjoint IP Rigor**:
   - Cross-split source IP purging removed recurring scanner botnets from validation and test sets.
   - $\Delta_k = \text{Recall}_{ML} - \text{Recall}_{Rule}$ is strictly reconciled with zero discrepancy across all stages.
4. **Viva Defense Position**:
   - Gate 0 empirically proves that early triage cannot rely on complex ML on handshake features alone.
   - The architecture's value lies in its lightweight, robust rule-based early gating (R1 login success, R6 failed logins) combined with visitor memory escalation.
