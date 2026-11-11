# WEEK1.md: First-Week Plan and Gate 0 Decision Matrix

Version 0.2, 2026-11-11. Goal of week 1: **learn whether the central premise holds before building anything else.** Nothing in week 1 is Internet-facing.

## Plan

| Day | Who | Task | Output |
|---|---|---|---|
| 0 | All | Create repo, add the docs, pin Python and library versions, set up `data/` (gitignored) and `results/`. Read `SAFETY.md`, the `EVAL.md` freeze rule, `AGENTS.md` | Repo skeleton, `DECISIONS.md` started |
| 1 | P2 | **S3:** download `session_aggregation.jsonl.gz` only, verify MD5, load in DuckDB, compute base rates; download 2 to 3 event-level days, confirm fields; read the dataset descriptor and the companion repo license | `results/base_rates.json`, S3 entry in `SPIKE_RESULTS.md` |
| 1 | P1 | Clone the pinned Cowrie release for study; map the code paths listed in SPIKES S1 | Notes |
| 2 | P1 | **S1:** proof of concept for per-session persona selection at login stage | S1 entry: Plan A or Plan B |
| 2 | P2 | Write the feature-extraction function and its "later events do not change features" test; draw the day sample with a seed; write `splits.json` | Tests green, `splits.json` |
| 2 | P3 | Prepare the dashboard shell for offline results (no invented numbers); read the third-party detector's docs | Skeleton |
| 3 | P2 | Tag `exp0-v1`. Implement rules R0 to R7 and ML candidates; run training and validation only | `rules.json`, validation metrics |
| 4 | P2 (P3 reviews) | Run the test evaluation once; run sanity checks; write `EXP0_RESULT.md` | `results/exp0/*` |
| 5 | All | **Gate review meeting.** Apply the decision matrix below; record the scope decision in `DECISIONS.md` | Scope decision |

Ground rules: do not look at test-set metrics before day 4; do not change rules or thresholds after seeing test data; if a task overruns its time box, record that as the result and move on.

## Decision matrix after Gate 0

| Experiment 0 | SPIKES S1 | Scope that follows |
|---|---|---|
| PASS-ML | Plan A works | Build the gatekeeper models; T1/T2 personas; shadow-mode live gatekeeper once the SAFETY checklist is done; consider adaptive serving later |
| PASS-ML | Only Plan B | Build the gatekeeper models; decisions are pre-command and **cross-session**; state this limitation in the report; keep live work in shadow mode |
| PASS-LATE-ONLY | Plan A works | Design mid-session escalation; keep Model V at stages S4 and S5; same safety gating |
| PASS-LATE-ONLY | Only Plan B | Keep the analysis **offline only**; report the late-stage finding and why it cannot be acted on with Plan B |
| FAIL | any | Reframe: cost-yield analysis of rule-based triage plus T1/T2 persona comparison on D1. Drop Model A, T3 and the adaptive arm. Report the negative ML result prominently |

Deferred under every row until the MVP is done: T3 real-VM tier, Model A, human blind study, live adaptive arm C.

## Week-1 deliverables checklist

- [ ] Repo with docs; `DECISIONS.md` has a day-0 entry
- [ ] `results/base_rates.json` and S3 summary
- [ ] S1 result with a reproducible PoC or a clear "not feasible in the time box"
- [ ] `exp0-v1` tag exists **before** any model training
- [ ] `results/exp0/` complete; `EXP0_RESULT.md` written
- [ ] Scope decision recorded

## Why not write more spec first

The spec is a draft contingent on Gate 0. Expanding it before the gate risks detailed documentation for a design that may change. Keep it as is, and update it only when the gate decision is recorded.
