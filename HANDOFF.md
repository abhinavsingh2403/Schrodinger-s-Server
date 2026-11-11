# HANDOFF.md: Model Handoff & Progress Ledger

## STATUS
- Current Task: G1 (Complete)
- Next Task: G2 (Download + MD5 verify script)

---

## DONE
1. Created skeleton directories with `.gitkeep`: `analysis/`, `data/`, `results/`, `infra/`, `sensor/`, `gatekeeper/`, `router/`, `harness/`, `dashboard/`.
2. Updated `.gitignore` to ignore `data/*` (while preserving `data/README.md` and `data/.gitkeep`), `results/tmp/`, `__pycache__/`, `.venv/`, `*.gz`, `*.zip`, `*.parquet`, and `.env`.
3. Created `data/README.md` with pre-filled table of Zenodo D1 datasets per `DATA.md`, with computed columns marked `TBD` and `transferred_files.zip` marked `DO NOT DOWNLOAD`.
4. Created `DECISIONS.md` with decision template and Day 0 repo initialization record.
5. Created `SPIKE_RESULTS.md` with spike template from `SPIKES.md`.
6. Created `requirements.txt` with pinned versions (`duckdb==2.0.0`, `pytest==9.2.0`) verified via `python -m pip index versions`.
7. Created `analysis/README.md` recording Python version `3.12.10`.
8. Tracked `PROMPTS.md` model-split task pack.

---

## FILES
- `.gitignore` (modified)
- `PROMPTS.md` (created)
- `requirements.txt` (created)
- `DECISIONS.md` (created)
- `SPIKE_RESULTS.md` (created)
- `HANDOFF.md` (created)
- `analysis/.gitkeep` (created)
- `analysis/README.md` (created)
- `data/.gitkeep` (created)
- `data/README.md` (created)
- `results/.gitkeep` (created)
- `infra/.gitkeep` (created)
- `sensor/.gitkeep` (created)
- `gatekeeper/.gitkeep` (created)
- `router/.gitkeep` (created)
- `harness/.gitkeep` (created)
- `dashboard/.gitkeep` (created)

---

## COMMANDS AND OUTCOMES
1. `python --version; pip --version`:
   - Output: `Python 3.12.10`, pip not in PATH directly.
2. `python -m pip --version`:
   - Output: `pip 25.0.1 from ... (python 3.12)` (Exit Code 0).
3. `python -m pip index versions duckdb; python -m pip index versions pytest`:
   - Output: `duckdb (2.0.0)`, `pytest (9.2.0)` (Exit Code 0).
4. Directory and `.gitkeep` creation:
   - Output: All 9 directories and `.gitkeep` files created (Exit Code 0).

---

## TODO(verify)
*(None for Task G1; versions were confirmed against PyPI index).*

---

## QUESTIONS FOR OPUS
*(None for Task G1).*

---

## QUESTIONS FOR HUMAN
*(None for Task G1).*
