# PROMPTS.md: Model-split prompt pack (Gemini Flash for easy work, Opus for hard work)

Version 0.2, 2026-11-11. Paste PREAMBLE at the top of every prompt. Run tasks in order. Each task ends by updating `HANDOFF.md`, because the two models do not share memory.

## Who does what

| Task | Model | Why |
|---|---|---|
| G1 repo skeleton | Gemini | mechanical |
| G2 download + MD5 verify script | Gemini | mechanical |
| G3 S3 base-rate script + tests | Gemini | simple SQL, small logic |
| O1 review of G3 (short) | Opus | catches label/logic mistakes cheaply; read-only review |
| O2 SPIKES S1: Cowrie per-session persona | Opus | reading unfamiliar code, hard to verify |
| O3 Experiment 0 implementation (later) | Opus | leakage, splits, cluster bootstrap, pre-registration |
| G4 tests, docs, dashboard, harness runners (later) | Gemini | after Opus defines the interfaces |

Rule of thumb: **Gemini writes code against a spec that already exists; Opus decides anything that involves a design choice, statistics or leakage.** If Gemini hits a design question it must stop and write it into `HANDOFF.md` under "QUESTIONS FOR OPUS".

---

## PREAMBLE (paste at the top of EVERY prompt)

```
Project: "Schrödinger's Server", a cost-aware adaptive SSH honeypot on Cowrie. The repo has planning documents; there is no result yet.

Before anything else read, in full: AGENTS.md, SAFETY.md, and the files named in the task. Reply with a summary of at most 10 lines of the rules that apply to this task, then continue.

Hard rules:
1. Do not invent APIs, config keys, event names, dataset fields, file paths or numbers. Verify in the installed package, the source, or the data file. If you cannot verify, write `TODO(verify): <what, why>` and stop on that point.
2. Every number in any output comes from a script in this repo. Never type a result by hand. Unknown = TBD.
3. Never edit EVAL.md, EXPERIMENT0.md, SPEC.md, SAFETY.md, DATA.md, CLAIMS.md. If you believe one is wrong, add a note to HANDOFF.md under "QUESTIONS FOR HUMAN" and carry on with the rest.
4. If data or code differs from what the docs say, STOP and report the exact mismatch. Do not adapt silently.
5. Do not make design decisions. If a choice is not specified, list the options in HANDOFF.md under "QUESTIONS FOR OPUS" and stop on that point.
6. Nothing network-facing. No scanning. No downloading anything not named in the task. Never download transferred_files.zip. No secrets or raw IPs in files.
7. Minimal changes. One concern per commit. Commit message says what and why.
8. At the end: update HANDOFF.md with (a) what was done, (b) files changed, (c) commands run and test outcome copied from the terminal, (d) TODO(verify) items, (e) QUESTIONS FOR OPUS / HUMAN. Then report the same in chat.
```

---

## G1 (Gemini): repo skeleton

```
[PREAMBLE]
Task G1. Create only the skeleton. No Python logic.
1. Directories with .gitkeep: analysis/ data/ results/ infra/ sensor/ gatekeeper/ router/ harness/ dashboard/
2. .gitignore: data/* (but not data/README.md), results/tmp/, __pycache__/, .venv/, *.gz, *.zip, *.parquet, .env
3. data/README.md: a markdown table, columns: file | source URL | download date UTC | size | MD5 on record page | MD5 computed | match. Pre-fill the record-page rows from DATA.md (D1 only) and leave the computed columns as TBD.
4. DECISIONS.md: header plus the template fields (date, decision, alternatives considered, why).
5. SPIKE_RESULTS.md: header plus the template from SPIKES.md ("Spike results template").
6. HANDOFF.md with sections: STATUS, DONE, FILES, COMMANDS AND OUTCOMES, TODO(verify), QUESTIONS FOR OPUS, QUESTIONS FOR HUMAN.
7. requirements.txt with PINNED versions of duckdb, pytest only. Get versions by running `pip index versions <pkg>` or `pip install` then `pip freeze`; do not guess version numbers. Record the Python version in analysis/README.md.
Acceptance: `git status` clean after commits; `ls` shows the tree; nothing else added.
```

## G2 (Gemini): download and verify

```
[PREAMBLE]
Task G2. Write analysis/verify_download.py: takes a file path and an expected MD5 as arguments, streams the file in chunks, prints "MATCH" or "MISMATCH" with both hashes, exits non-zero on mismatch. Add analysis/test_verify_download.py (pytest) using a tiny temp file created in the test.
Also add docs in analysis/README.md with the exact commands for the human to download ONLY session_aggregation.jsonl.gz from https://zenodo.org/records/21260400 (check the record page for the exact file URL; if you cannot reach it, write TODO(verify) and tell the human to copy the link from the page). Expected MD5 from DATA.md: 1f3897650fb420c97c14ff452398c3f8. Save into data/ (gitignored).
Do not download anything yourself unless the human told you to.
Acceptance: pytest passes.
```

## G3 (Gemini): S3 base-rate script

Run only after the human has downloaded and verified the file.

```
[PREAMBLE]
Task G3 (SPIKES S3, part 1). Files to read: SPIKES.md (S3), DATA.md (D1 schema), EVAL.md section 2.1.
Write analysis/s3_base_rates.py using DuckDB on data/session_aggregation.jsonl.gz:
1. Check all 25 field names listed in DATA.md exist exactly. Print missing and extra fields. If any is missing, stop and report.
2. Compute and write results/base_rates.json: total sessions; sessions with cnt_login_success > 0; with cnt_command_input > 0; distribution of cnt_command_input (0, 1-4, 5-9, 10+, and quantiles 50/90/99); share with cnt_file_upload + cnt_file_download > 0; share with cnt_direct_tcpip_request > 0.
3. Aggregate approximation of value=1, exactly as in SPIKES S3 step 3: cnt_command_input >= 5 OR file transfer (upload or download > 0) OR cnt_direct_tcpip_request > 0. Report overall and per day (day = date of first_seen, UTC). Make N_CMD a command-line argument defaulting to 5; do not change the default.
4. Print a note that cnt_command_input counts input events, not distinct commands, so this is only an approximation.
5. results/MANIFEST.json: file MD5, DuckDB version, script git commit hash, timestamp.
Write analysis/test_s3_base_rates.py: pytest on a synthetic 10-row jsonl you create in the test (include edge cases: exactly 4 and 5 commands, file upload only, direct-tcpip only, no login). Tests check the approximation logic and the schema check.
Do not interpret the numbers beyond one neutral paragraph. Do not propose a new N_CMD.
Acceptance: pytest passes; running the script on the real file writes both JSON files.
```

## O1 (Opus, short): review of G3

```
[PREAMBLE]
Task O1: READ-ONLY REVIEW. Do not edit any file except HANDOFF.md.
Review analysis/s3_base_rates.py, its test, results/base_rates.json and MANIFEST.json against SPIKES.md S3, DATA.md and EVAL.md section 2.1.
Check specifically:
(a) every field name used exists in the 25-field schema in DATA.md;
(b) the value approximation matches SPIKES S3 step 3 exactly (>= vs >, OR logic, which counters count as file transfer);
(c) per-day grouping uses first_seen in UTC, and the day boundaries do not drop or double-count sessions (check the sum of per-day counts equals the total);
(d) the tests actually exercise edge cases and would fail if the logic were wrong;
(e) any number in base_rates.json that is implausible (shares above 1, negative counts).
Output a list: PASS or FAIL per item with file and line evidence, then a list of concrete fixes. Do not apply fixes; the human will give them to Gemini.
```

## O2 (Opus): SPIKES S1, Cowrie per-session persona

```
[PREAMBLE]
Task O2 (SPIKES S1). Files to read: SPIKES.md (S1), SPEC.md sections 0, 4 and 5.1, SAFETY.md.
Goal: answer one question with evidence: can Cowrie choose the persona (fake filesystem or identity) per session, after login, from our own code, without a deep fork? 
Steps:
1. Find the latest Cowrie release tag via the project's GitHub releases page or pip index; ask the human to confirm the version to pin. Clone that exact tag into sensor/cowrie-src/ (read-only study copy). Record the tag and commit hash in DECISIONS.md.
2. Read the source (search; do not assume paths): SSH transport and banner; key exchange logging; authentication and the point where login is accepted; shell protocol creation and fake filesystem loading; command dispatch; proxy and backend pool selection.
3. For every claim you make, cite file path and line numbers from the pinned source. If you cannot cite it, label it UNVERIFIED.
4. Build a throwaway proof of concept in a lab container only (no public exposure, no outbound network): after a successful login, pick between two fake filesystems by a trivial rule (odd/even source port). Show a log or transcript where session A sees persona 1 and session B sees persona 2.
5. Write to SPIKE_RESULTS.md using the template: exact hook points, lines that must change, whether a plugin or subclass is enough, merge-pain risk, and the decision: Plan A (achieved) or Plan B (not achieved in the time box).
If the PoC fails, report what failed, do not fake success, and recommend Plan B.
Acceptance: reproducible PoC steps in the file and a decision recorded.
```

## O3 (Opus, later): Experiment 0

Do not start until G3 is reviewed and SPIKE S1 and S3 decisions are recorded. Before this task, the human tags `eval-v1` (after any N_CMD decision) and `exp0-v1`.

```
[PREAMBLE]
Task O3: implement Experiment 0 exactly as written in EXPERIMENT0.md (read it fully, plus EVAL.md sections 2, 3, 4 and 6). Do not change any design parameter. Build in this order and stop after each for human review:
1. Label construction (V_full, label window, exclusions) with unit tests.
2. Split construction: temporal and by source IP group, with leakage tests.
3. Rules R0 to R7 as defined in EXPERIMENT0.md section 7.
4. Learned models (logistic regression and gradient-boosted trees as specified), fit only on training data.
5. Cluster bootstrap by source IP, recall of V_full at 10% budget, decision rule from section 12.
Write results to results/ only via scripts; write EXP0_RESULT.md from the script output, not by hand. Report PASS-ML, PASS-LATE-ONLY or FAIL exactly per the rule, even if negative.
```

---

## Handoff protocol between models

1. After every task the model updates `HANDOFF.md`. The next model starts by reading `HANDOFF.md`, `DECISIONS.md` and `SPIKE_RESULTS.md`.
2. Opus questions listed in HANDOFF.md are answered at the start of the next Opus session, in one batch, to save limit.
3. Use Opus only for O1, O2 and O3 and for any review that touches labels, splits or statistics. Everything else goes to Gemini.
4. The human, not the model, verifies hashes, reads the result JSON files, and applies the tags.
