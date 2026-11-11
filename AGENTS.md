# AGENTS.md: Rules for AI Coding Agents (Codex, Antigravity, and similar)

This file is written for coding agents working in this repository. Humans must also follow it. Codex reads a file named `AGENTS.md` by convention. For Antigravity, check its current documentation for how to load project rules, and paste the "Rules" section below into its rules/instructions mechanism **[U: mechanism not verified]**.

---

## Rules

### Truthfulness (highest priority)
1. **Do not invent.** Do not guess library APIs, Cowrie configuration keys, event names, dataset fields or file paths. Verify against the pinned source code, the installed package, or the data file itself. If you cannot verify, write `TODO(verify): <what and why>` and stop; do not fabricate.
2. **No fabricated results.** Never write numbers, metrics, plots or table values by hand. Every number in `results/`, reports and the dashboard must come from a script in this repo. If a result does not exist yet, show `TBD`.
3. **Do not weaken the evaluation.** `EVAL.md` is pre-registered once the `eval-v1` tag exists. Do not change hypotheses, labels, splits, metrics or success criteria. If you think a change is needed, open a note in `DECISIONS.md` and ask a human.
4. **Sources:** any external fact you add to a document must be added to `CLAIMS.md` with a URL and a verification status ([V]/[S]/[U]). Never present [S] or [U] items as verified.

### Safety (non-negotiable)
5. Read `SAFETY.md` before writing any network-facing, scanning, agent or deployment code.
6. Never write code that scans, probes or attacks anything except the allowlisted lab targets. Never add outbound connections from the honeypot or T3 guests. Never execute captured payloads. Never commit secrets (HMAC salt, API keys, SSH keys). Never put raw attacker IPs in committed files.
7. Do not download `transferred_files.zip` (DATA.md).

### Engineering discipline
8. **Spikes first.** Do not build features before **Gate 0** is recorded: `SPIKE_RESULTS.md` has decisions for S1 and S3, and `EXP0_RESULT.md` holds the Experiment 0 outcome (`EXPERIMENT0.md`). S2, S4 and S5 start only after Gate 0 passes.
9. **Tests before features** for: feature extraction (same code path offline and live), label computation, split construction (group and temporal leakage tests), policy (monotone upward-only tiers), decision API contract.
10. **Offline/live parity.** Feature code is one module used by both the offline pipeline and the live gatekeeper. Add a test that feeds the same events through both and compares features.
11. **Small commits, one concern each.** Commit message states what and why. Do not mix refactors with behavior changes.
12. **Minimal changes.** When editing existing code, change only what is needed; do not rewrite files wholesale.
13. **Pin everything:** Cowrie version and hash, Python version, library versions (lock file), data file hashes (DATA.md), container image digests.
14. **Determinism:** seed every random process; log seeds in `results/MANIFEST.json`.
15. **Leakage guards:** splits by time and by source group are code, with tests. Never fit scalers/encoders/thresholds on validation or test data.
16. **Decisions:** record every non-trivial design decision and its reason in `DECISIONS.md` (date, decision, alternatives considered, why).
17. **Explainability for the viva:** every module gets a short docstring describing what it does and why; keep the code understandable by a student who must defend it.

### Output hygiene
18. Notebooks are for exploration only; final analysis lives in scripts under `analysis/`.
19. The dashboard must label every panel LIVE, LAB or RECORDED, and mask identifiers.
20. When you finish a task, report: what changed, which tests ran and their outcome, and anything unverified left as `TODO(verify)`.

---

## Task prompt template (for humans giving tasks to agents)

```
Context files to read first: SPEC.md section <n>, EVAL.md section <n>, SAFETY.md, AGENTS.md.
Task: <one concern>.
Acceptance: <tests/commands that must pass>.
Constraints: no new dependencies without asking; do not edit EVAL.md; do not invent APIs (read the pinned source).
Report: files changed, tests run, any TODO(verify).
```

## Definition of done (any task)

- [ ] Tests exist and pass; leakage/parity tests included where relevant
- [ ] No hand-typed results; no secrets; no raw IPs
- [ ] `CLAIMS.md` updated if an external fact was added
- [ ] `DECISIONS.md` updated if a design decision was made
- [ ] `TODO(verify)` items listed in the report
