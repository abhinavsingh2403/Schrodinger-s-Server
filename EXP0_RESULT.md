# Experiment 0 Result: Gate 0 Evaluation Report

**Date**: 2026-11-12  
**Outcome**: `PASS-ML`  
**Status Description**: ML adds significant early triage signal before any command (Stages: S2, S3).  

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
| **S1** | 1.0 | 0 | 598,647 | 0.0144 | `R0_random` | 0.0937 | `LogisticRegression(C=0.1)` | 0.6247 | 0.531 | [0.3372, 0.913] | True |
| **S2** | 0.9344 | 0 | 559,399 | 0.0154 | `R7_decision_tree` | 0.4666 | `LogisticRegression(C=0.01)` | 0.6077 | 0.1411 | [0.1042, 0.1855] | True |
| **S3** | 0.1684 | 0 | 100,793 | 0.0855 | `R6_failed_logins` | 0.121 | `HistGradientBoosting(lr=0.05,iter=100)` | 0.3243 | 0.2033 | [0.0246, 0.285] | True |
| **S4** | 0.1463 | 2734 | 87,593 | 0.001 | `R4_delay` | 1.0 | `HistGradientBoosting(lr=0.05,iter=100)` | 1.0 | 0.0 | [0.0, 0.0] | False |
| **S5** | 0.0002 | 1114 | 102 | 0.8627 | `R6_failed_logins` | 0.125 | `LogisticRegression(C=1.0)` | 0.125 | 0.0 | [0.0, 0.0] | False |

---

## 3. Pre-declared Decision Rule Criteria

From `EXPERIMENT0.md §12`:
- **PASS-ML**: There exists a stage $k \in \{S1, S2, S3\}$ where $\Delta_k \ge 0.05$, the lower bound of its Bonferroni CI is $> 0$, and positive sessions $\ge 500$.
- **PASS-LATE-ONLY**: No such stage in $S1-S3$, but a stage in $\{S4, S5\}$ meets the same criteria.
- **FAIL**: Otherwise.

---

## 4. Scientific Interpretation, Leakage Audit & Gate 0 Verdict

1. **Gate 0 Decision**: `PASS-ML`.
   - Stages **S2** (Authentication) and **S3** (Post-Auth Channel Setup) conclusively pass Gate 0:
     - Stage S2 achieves $\Delta_2 = +0.1411$ (14.1% absolute recall lift over the best rule `R7_decision_tree`) with Bonferroni $CI_{lower} = 0.1042 > 0$ and 8,614 positive sessions ($\ge 500$).
     - Stage S3 achieves $\Delta_3 = +0.2033$ (20.3% absolute recall lift over `R6_failed_logins`) with Bonferroni $CI_{lower} = 0.0246 > 0$ and 8,618 positive sessions ($\ge 500$).
   - Both S2 and S3 operate strictly **before any command is received**, demonstrating that machine learning provides high-value early triage prior to shell execution.
2. **Feature Stage Leakage Audit & Remediation**:
   - In earlier explorations, full session `duration` (`last_seen - first_seen`) was improperly passed to all stages. Because long sessions in honeypot logs strongly correlate with interactive payload downloads, `duration` acted as an oracle proxy for `v_full`, artificially inflating S1 recall.
   - Code audit in `analysis/exp0_train.py` strictly excludes `duration` from all stages. Handshake features at S1 are limited solely to client KEX counts, client version strings, and fingerprint packet sizes.
3. **Multiplicity and Delta Discrepancy Correction**:
   - In previous commit iterations, rule scoring for the bootstrap comparison fell back to `R0_random` for non-R1/R2 rules, causing reported deltas to mismatch `ML_recall - Rule_recall`.
   - The harness has been corrected so that $\Delta_k = \text{Recall}(\text{ML}) - \text{Recall}(\text{Best Rule})$ identically across all rows, comparing directly against the true chosen baseline rule (`R7` in S2, `R6` in S3, `R4` in S4).
4. **Disjoint IP Purge & Survivorship Bias**:
   - Enforcing strict disjoint source IP assignment across temporal folds purged 879,561 validation sessions and 1,022,940 test sessions (~63% of raw test sessions).
   - This prevents optimistic data leakage from persistent scanning networks, but introduces a survivorship bias where validation and test sets are skewed toward ephemeral or novel scanners. The ML models generalize despite this rigorous distributional hurdle.
5. **Stages S4 and S5 Flagging**:
   - Stage S4 has an extremely low base rate (0.001) due to prefix-determined exclusions (2,734 sessions dropped), and Stage S5 contains only 102 evaluated sessions. Both stages fail the pre-registered minimum size condition (`Min Size Met = False`) and are correctly disregarded for Gate 0.
