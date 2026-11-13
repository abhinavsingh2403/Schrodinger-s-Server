# GEMINI_TASKS.md: tasks safe for a fast, cheaper model (Gemini Flash, high setting)

Rule of thumb: give Gemini work that has a **written spec, a visible acceptance test, and no statistical or design decision**. Anything that produces a number used in a claim, touches Cowrie internals, or changes policy logic goes to Astra/Opus (list at the end).

## PREAMBLE (paste at the top of every task)

```
Project: "Schrödinger's Server" (cost-aware adaptive SSH honeypot on Cowrie), repo branch trainmodel. Windows/PowerShell machine: use `python -m pytest -q`, not bare pytest.
Read first: AGENTS.md (all). Then only the files named in the task.
Hard rules:
1. Do not invent APIs, field names, file paths, numbers or library versions. Verify in the code or by running a command. If you cannot, write TODO(verify): <what, why> and stop on that point.
2. Never type a result by hand. Numbers in any UI, doc or report must be read from a file in results/ by code, or copied from such a file. Unknown = "NO DATA" or TBD.
3. Do not edit EXPERIMENT0.md, EVAL.md, SPEC.md, SAFETY.md, DATA.md, results/exp0/splits.json, results/exp0/grid.json, or any file under results/ unless the task says a script regenerates it.
4. No new dependencies without asking me. No network scanning; lab targets only (127.0.0.1 or RFC1918). Do not download transferred_files.zip. No secrets, no raw IPs in files.
5. Minimal changes; do not refactor unrelated code. Small commits, one concern each, message says what and why. Do NOT push, do NOT touch git tags.
6. Do not make design decisions. If a choice is not specified, write it under "QUESTIONS" in HANDOFF.md (your own section) and stop on that point.
7. Run `python -m pytest -q` before and after. Final report: files changed, commands run with real output excerpts, tests result, TODO(verify) list.
```

---

## G1. Remove fake data from the dashboard (owner C, do first)
```
[PREAMBLE]
Files: dashboard/templates/index.html, dashboard/app.py, dashboard/test_*.py.
Problem (known, verify by reading): index.html contains static "live" rows, hard-coded numbers and random simulated updates (search for Math.random, setInterval with generated values, hard-coded arrays of sessions, and numeric literals such as 38126048 or 1232570). 
Task: remove every fabricated value. Where real data is unavailable show the text "NO DATA" (no zeros that look like data). Numbers must come only from API endpoints in app.py, which read results/*.json or the decision log. Do not change what the JSON files contain.
Acceptance: (1) grep for Math.random and for the literals above in dashboard/ returns nothing; (2) page renders with results/ present and also with results/ missing (shows NO DATA); (3) tests pass.
```

## G2. Dashboard truthfulness test
```
[PREAMBLE]
Task: add dashboard/test_truthfulness.py (pytest). It must fail if any file under dashboard/ contains: Math.random, a hard-coded session array, or numeric literals that appear in results/base_rates.json (read the values from the JSON at test time and search the HTML/JS/Python for them). Also test that each API panel payload in app.py includes a `source` key with one of RECORDED, LAB, LIVE.
Acceptance: the test passes on the cleaned dashboard and fails if you temporarily re-add a hard-coded number (show this once, then revert).
```

## G3. Provenance labels RECORDED / LAB / LIVE
```
[PREAMBLE]
Files: dashboard/app.py, dashboard/templates/index.html.
Spec: every API payload gets `source`: RECORDED when the data comes from a file under results/ produced by a script; LAB when it comes from the decision log of a sensor started in lab mode; LIVE only when mode is LIVE and the log is non-empty. If a source file is missing, return `{"status":"NO DATA"}`. The UI shows the source as a small badge on every panel. Add a visible badge text "SIMULATED ORACLE (HINDSIGHT UPPER BOUND)" on the arm simulation panel and "EVAL H4 NOT YET EVALUATED" on the detector panel (both already stated in HANDOFF.md; copy the wording from there).
Acceptance: unit tests for the three source cases and the missing-file case.
```

## G4. Honest status table generator (docs only)
```
[PREAMBLE]
Files: results/exp0/progress.json (read-only), README.md, HANDOFF.md.
Task: write analysis/render_status.py that reads results/exp0/progress.json and writes docs/STATUS.md: the checklist with Done / Partial / Not done, weights, and the percentage computed by the script with the formula already used in analysis/progress_accounting.py (read that file; do not change the formula). Add one line to README.md linking to docs/STATUS.md. Do not hand-write any percentage.
Acceptance: running the script twice gives identical output; a test compares the percentage to progress_accounting's output.
```

## G5. Generated interpretation sentence in the Gate 0 report
```
[PREAMBLE]
Files: analysis/exp0_train.py (function write_exp0_result_md only), analysis/test_exp0_report_hygiene.py.
Task: in the generated EXP0_RESULT.md, keep the mechanical line "Gate 0 Outcome: <outcome from the script>" unchanged, but replace the "Status Description" sentence "ML adds significant early triage signal before any command (Stages: ...)" by EXACTLY this text for outcome PASS-ML: "Mechanical outcome of the pre-declared rule. Exploratory: aggregate-only features, transfer-labelled sessions dominate the gain, a shuffled-label diagnostic and event-order checks are unresolved; see ROBUSTNESS.md and AUDIT.md. Not validated as a pre-command signal." Keep other outcomes' text unchanged. Do not change any computation.
Acceptance: test asserts the new text appears for PASS-ML and the old claim does not. Regenerate the report only with the existing command if the data file exists; otherwise just run the tests and say so.
```

## G6. Kali attacker scripts for the demo (owner A or C)
```
[PREAMBLE]
Task: create harness/attackers/ with three scripts that talk to a lab sensor given by --host and --port. Safety guard first: refuse to run unless the host is 127.0.0.1, localhost or an RFC1918 address (reuse is_target_allowlisted from harness/detector_runner.py if it fits; read it first). 
Scenarios: (1) bot_like: connect, a few failed logins, one successful login, run at most 2 commands, disconnect. (2) transfer_like: after login run commands that make the sensor log a file download or upload attempt, using only built-in client commands (no real malware, no external URLs; use a local lab URL placeholder given by --url). (3) interactive: login, request a PTY, run 6 or more varied benign commands (ls, uname -a, cat /etc/passwd, id, whoami, ps), disconnect.
Implementation: Python standard library plus the system `ssh` client via subprocess if possible. If this cannot work without a new dependency (e.g. paramiko), STOP and ask me; do not add it yourself.
Acceptance: a --dry-run mode that prints what would be done and runs in tests without a network; unit tests for the allowlist guard (public IP must be refused).
```

## G7. Cost-measurement harness (owner A; spec given, no statistics)
```
[PREAMBLE]
Task: write analysis/measure_cost.py. Inputs: --tier {T1,T2}, --sessions N, --host, --port, --container NAME. It runs N scripted sessions with harness/attackers/bot_like (G6) one after another, samples `docker stats --no-stream --format json` for the container every second during the run into a CSV under results/cost/, then writes results/cost_model.json with: tier, N, wall time, mean and max CPU %, mean and max memory MB, and the exact command line, git commit and timestamp. No interpretation, no extrapolation to rupees (that belongs to the cost model owner).
Acceptance: a --dry-run with a fake `docker stats` output file used in tests; the JSON has all keys; failing docker call produces a clear error and no partial JSON.
```

## G8. Docker compose smoke test
```
[PREAMBLE]
Files: infra/docker-compose.yml, infra/cowrie.cfg, infra/.
Task: write infra/smoke_test.ps1 and infra/smoke_test.sh that (1) run `docker compose config` to validate the file, (2) print which ports are published and to which host address, (3) check that no service publishes a port on 0.0.0.0 unless I whitelisted it in a variable at the top of the script (default: none), (4) check that the lab network is declared internal where the compose file says it should be. Do not start any container unless I pass --up. Do not change the compose file; report suspicious settings in HANDOFF.md under QUESTIONS (known doubt: an `internal: true` network together with published ports may not behave as intended; verify by reading Docker documentation or by running, and say which).
```

## G9. Architecture diagram and glossary (docs)
```
[PREAMBLE]
Read SPEC.md sections 0 to 5 and README.md only. Create docs/ARCHITECTURE.md with a Mermaid diagram (visitor to sensor to gatekeeper to tier T1/T2, with T3 shown as DEFERRED) and a glossary (stages S1 to S5, tiers, Model V, escalation budget, Gate 0, oracle arm). Every statement must be traceable to a section of SPEC.md or README.md; add the section number in brackets. Do not describe features marked DEFERRED as implemented. No numbers.
```

## G10. Slide outline and viva question sheet (drafts; a human reviews)
```
[PREAMBLE]
Read README.md, docs/STATUS.md (G4), results/exp0/AUDIT.md, DECISIONS.md headings only.
Task: write docs/SLIDES_OUTLINE.md (10 slides, 1 to 3 bullets each, each bullet ends with the source file in brackets) and docs/VIVA_QA.md (30 likely examiner questions grouped: problem, data, Gate 0 and statistics, system, safety, limits; each with a 2 to 4 line answer that cites a file). Every claim must match AUDIT.md: Gate 0 is exploratory; S1/S2 ML did not beat rules; S4/S5 not evaluated; T3, Model A, live trial are future work. Do not copy numbers from memory: read them from the files. Mark any answer you are unsure about with [CHECK].
```

## G11. Link and claim checker
```
[PREAMBLE]
Task: write analysis/check_docs.py that scans *.md for (a) links to files that do not exist, (b) absolute Windows paths (file:///c:/ or C:\), (c) the strings "100% complete", "perfect", "flawless", "proving", "7.9/10" and prints each hit with file and line. Exit code 1 if any hit. Add a pytest that runs it. Fix only the broken links and absolute paths it finds; list the other hits in the report for a human to rewrite.
```

---

## NOT for Gemini (give to Astra or Opus)
- 200-seed permutation null, bootstrap changes, anything in analysis/exp0_*.py computing recall, CIs or p-values.
- Reading or interpreting event-level data; deciding which days to use; interpreting ROBUSTNESS/AUDIT results.
- `gatekeeper/policy.py` budget logic, `decision_api.py` scoring, offline/live feature module design.
- Cowrie internals: persona switching, session hooks, `sensor/adaptive_server.py`, `sensor/spike_s1_poc.py`.
- Final wording of scientific claims, tags (`exp0-v3`), SAFETY decisions, third-party detector licensing check.

## Suggested order for Gemini
G1, G2, G3 (dashboard, one chain) then G5, G11 (quick wins), then G6, G8, G7 (when Linux sensor runs), then G4, G9, G10 (docs, last, after results are final).
