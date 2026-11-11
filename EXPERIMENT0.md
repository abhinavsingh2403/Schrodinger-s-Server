# EXPERIMENT0.md: Gate 0 Experiment

Version 0.2, 2026-11-11. Pre-declared design. Tag the repository `exp0-v1` before any model is trained; changes after that need a `DECISIONS.md` entry and a new tag. No result exists yet.

---

## 1. Question

At each decision stage of an SSH session, can a learned model predict **future session value** better than the best **simple rule**, at the same escalation budget?

## 2. Why this comes first

1. After the first command, predicting that a session will keep interacting is easy; any rule does it. The ML premise is only interesting **before any command** (stages S1 to S3), where information is scarce and an early decision is valuable.
2. If simple rules match the models, the project's ML story collapses. That is better learned in week 1 than in week 8.
3. The experiment is fully offline on public data: no public exposure, no safety risk.

## 3. Data and sample

- Dataset D1 (`DATA.md`). Event-level files are needed (hassh, client version, terminal size, command text, timestamps, configuration `group`). Verify field availability in SPIKES S3 first.
- **Day sample** (the event-level archive has one file per day; confirm names and ordering in S3): 5 training days spread over the first 35 days, 2 validation days from days 36 to 42, 2 test days from days 43 to 50. Choose the specific days **by a seeded random draw, written to `results/exp0/splits.json` before looking at any outcome.**
- **Grouping:** every source IP (as anonymized in the dataset) belongs to exactly one fold. A source IP that appears in more than one period is assigned to the earliest period's fold and removed from later folds.
- **Configuration handling:** primary analysis = sessions from the Enhanced and persistence configurations (`group` field). Secondary = Baseline. Tertiary = all configurations with `group` as a feature. Do **not** use sensor id or honeypot IP as features.
- **Minimum size:** the test set must contain at least 500 positive sessions per evaluated stage. If not, add more test days (chosen by the same seeded procedure) before looking at results; if still not reachable, report the stage as underpowered.

## 4. Unit and stages

Unit = one SSH session (Cowrie session id). Stages as in `SPEC.md` 7.3:

| Stage | Information available |
|---|---|
| S1 | After key exchange: client version string, hassh, algorithm counts |
| S2 | After authentication: failed-login count, time to first success, distinct usernames tried, success flag |
| S3 | Session start: exec vs interactive (if distinguishable), PTY present, terminal width/height, forwarded env var count |
| S4 | After first command: command length, tokens, chaining operators, delay after login |
| S5 | After first three commands: gap statistics, distinct ratio, failure ratio |

For each stage, the evaluation set contains only sessions that **reach** that stage. Report the reach rate (share of all sessions) per stage.

## 5. Label and exclusions

- Whole-session label `V_full = 1` if the session has at least one of: at least 5 distinct commands; at least one file download or upload; at least one direct-tcpip request (`EVAL.md` 2.1). If only the aggregate approximation is available for some analysis, label it as such.
- **Prefix-determined exclusion:** for stage k, drop sessions whose events up to stage k already satisfy `V_full` (for example a download in the first command). Count and report how many are dropped per stage.
- Features for stage k use only events up to and including stage k. This is enforced by one feature-extraction function with a unit test that appends later events and checks that the features do not change.

## 6. Features

As in `SPEC.md` 7.3, per stage, cumulative (stage k includes all earlier-stage features). No raw credentials. No sensor or instance identifiers.

## 7. Simple-rule baselines (all pre-declared; each is a ranking score; ties broken at random with a fixed seed)

| ID | Rule (score) | Valid from | Direction / parameters |
|---|---|---|---|
| R0 | Random score | S1 | none |
| R1 | 1 if login succeeded, else 0 | S2 | none |
| R2 | 1 if a PTY / terminal size was requested, else 0 | S3 | none |
| R3 | 1 if the session is an interactive shell rather than a single exec command, else 0 | S3 | needs the distinction to be derivable from events; if not, drop R3 and say so |
| R4 | Seconds from login success to first command | S4 | sign (larger = more or less valuable) chosen on training data |
| R5 | Rarity of the client version string (negative log of its training-set frequency) | S1 | sign chosen on training data; a hassh-rarity variant R5b is also reported |
| R6 | Number of failed logins before success | S2 | sign chosen on training data |
| R7 | A depth-3 decision tree trained on the simple features used by R1 to R6 | S2 and later | trained on training data only |

**Best simple rule at stage k** = the rule valid at k with the highest **validation** recall at the 10% budget; its **test** performance is what ML is compared against. Selecting on validation and reporting on test avoids optimistic bias for the rules.

## 8. Learned candidates

- L2-regularized logistic regression on the stage features.
- Gradient-boosted trees (scikit-learn `HistGradientBoostingClassifier` or LightGBM) with a small, pre-declared hyperparameter grid (written to `results/exp0/grid.json` before training), tuned on validation only.
- A GRU over event sequences is **not** part of Experiment 0.
- "Best ML at stage k" = the candidate with the highest validation recall at the 10% budget; report its test performance.

## 9. Budgets and metrics

- Budget b = fraction of **sessions that reach stage k** that may be escalated: 1%, 5%, 10%, 20%.
- Primary metric: **recall of `V_full = 1` at the 10% budget**. Also report recall and precision at all budgets, and PR-AUC.
- Report the base rate of `V_full` per stage so numbers can be read against random.

## 10. Statistics

- Cluster bootstrap by source IP, 10,000 resamples, paired (the same resample for ML and best rule), for Delta_k = recall_ML(k) minus recall_bestRule(k) at the 10% budget.
- Multiplicity: stages S1 to S3 form one family (3 tests); S4 and S5 another (2 tests). Use Bonferroni-adjusted two-sided intervals (about 98.3% for S1 to S3, 97.5% for S4 and S5).

## 11. Sanity and leakage checks (all must be reported)

1. Permute labels in training; test PR-AUC must be close to the base rate.
2. Compare a random (non-grouped) split with the grouped split; report the gap (it shows how much leakage would have flattered results).
3. Feature-importance review: no identifier-like features (sensor, instance, IP, port) may be present or dominant.
4. Duplicate check: the same session id must not appear in two folds.
5. The feature-extraction unit test (section 5) passes.
6. Re-run with a different seed for the day draw and report the stability of Delta_k.

## 12. Pre-declared decision rule

Let delta = 0.05 absolute recall (the smallest improvement we would care about; fixed before seeing data).

- **PASS-ML:** there is a stage k in {S1, S2, S3} where Delta_k >= delta and the lower bound of its adjusted CI is above 0, with the minimum-size condition met.
- **PASS-LATE-ONLY:** no such stage in S1 to S3, but a stage in {S4, S5} meets the same condition.
- **FAIL:** otherwise.

## 13. What each outcome changes

| Outcome | Meaning | Project consequence |
|---|---|---|
| PASS-ML | ML adds signal before any command | Continue to gatekeeper models. Decisions can be made at pre-command stages; Plan B (cross-session routing) becomes more valuable |
| PASS-LATE-ONLY | ML adds signal only after commands | Value requires mid-session escalation; continue only if SPIKES S1 shows Plan A is feasible. Otherwise keep the analysis offline |
| FAIL | Simple rules are as good as learned models | **Reframe, do not abandon.** The contribution becomes a cost-yield analysis of rule-based triage on a 38-million-session dataset plus the persona comparison. Drop Model A, T3 and the adaptive live arm. Report the negative ML result prominently |

## 14. Outputs

`results/exp0/`: `splits.json`, `grid.json`, `rules.json` (chosen directions and best rule per stage), `ml.json`, `table.csv` (per stage: reach rate, base rate, best-rule recall, ML recall, Delta, CI), `curves.png`, `checks.json`, `MANIFEST.json` (commit, data hashes, library versions, seeds), and a short human-written `EXP0_RESULT.md` stating the outcome (PASS-ML / PASS-LATE-ONLY / FAIL), the evidence, and the scope decision.

## 15. Time box and ownership

- Owner: P2 (ML/Analysis); P3 reviews the feature-extraction test and the checks; P1 is not blocked.
- Time box: 3 to 4 working days after SPIKES S3 is done.
- A result that disagrees with expectations is a result. Do not tune rules or the decision threshold after seeing test data.
