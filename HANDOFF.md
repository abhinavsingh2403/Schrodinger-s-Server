# HANDOFF.md: Model Handoff & Progress Ledger

## STATUS
- Current Task: G3 (Complete)
- Next Task: O1 (Opus Read-Only Review of G3)

---

## DONE
1. Downloaded Zenodo D1 primary dataset `data/session_aggregation.jsonl.gz` (1,328,104,319 bytes).
2. Verified MD5 digest via `analysis/verify_download.py` (`1f3897650fb420c97c14ff452398c3f8` -> `MATCH`).
3. Updated `data/README.md` record table reflecting download date, size, and MD5 match.
4. Executed `analysis/s3_base_rates.py` on the complete 38,126,048 session dataset using DuckDB.
5. Successfully validated all 25 schema fields per `DATA.md`.
6. Generated `results/base_rates.json` (overall distribution, command bins, quantiles, and 52 daily breakdowns with strict sum consistency).
7. Generated `results/MANIFEST.json` with commit hash, file MD5, DuckDB version, and timestamp.
8. Recorded Spike S3 Part 1 findings in `SPIKE_RESULTS.md`.

---

## FILES
- `data/README.md` (modified)
- `analysis/s3_base_rates.py` (modified)
- `results/base_rates.json` (created)
- `results/MANIFEST.json` (created)
- `SPIKE_RESULTS.md` (modified)
- `HANDOFF.md` (modified)

---

## COMMANDS AND OUTCOMES
1. Checksum verification:
   ```powershell
   > .\.venv\Scripts\python.exe analysis/verify_download.py data/session_aggregation.jsonl.gz 1f3897650fb420c97c14ff452398c3f8
   MATCH: computed=1f3897650fb420c97c14ff452398c3f8 expected=1f3897650fb420c97c14ff452398c3f8
   ```
2. Base rates execution:
   ```powershell
   > .\.venv\Scripts\python.exe analysis/s3_base_rates.py --data-path data/session_aggregation.jsonl.gz
   Connecting to DuckDB and loading data\session_aggregation.jsonl.gz...
   SCHEMA CHECK PASSED: All 25 fields exist exactly.
   Computing base rates (N_CMD=5)...

   ======================================================================
   NOTE: cnt_command_input counts input events, not distinct commands,
   so this is only an approximation of value=1.
   ======================================================================

   Saved base rates to results\base_rates.json
   Computing MD5 checksum of data\session_aggregation.jsonl.gz...
   Saved manifest to results\MANIFEST.json
   ```
3. Pytest suite:
   ```powershell
   > .\.venv\Scripts\python.exe -m pytest analysis/ -v
   ============================== 5 passed in 0.18s ==============================
   ```

---

## SUMMARY OF RESULTS (`results/base_rates.json`)
- Total Sessions: 38,126,048 (52 days)
- Login Success: 4,374,446 (11.47%)
- Command Input: 3,335,870 (8.75%)
- Command Input Distribution:
  - 0 commands: 34,790,178 (91.25%)
  - 1–4 commands: 3,115,939 (8.17%)
  - 5–9 commands: 58,543 (0.15%)
  - 10+ commands: 161,388 (0.42%)
  - Quantiles: p50 = 0.0, p90 = 0.0, p99 = 2.0
- File Transfers: 755,225 (1.98%)
- Direct-TCPIP (Port-forward/Pivot): 467,551 (1.23%)
- Approximate Value=1 (N_CMD>=5 OR file transfer OR pivot): 1,232,570 (**3.23%** base rate)

---

## TODO(verify)
*(None. Checksums and schema match verified).*

---

## QUESTIONS FOR OPUS
**Task O1 (Opus Short Review)**:
Please review `analysis/s3_base_rates.py`, `analysis/test_s3_base_rates.py`, `results/base_rates.json`, and `results/MANIFEST.json` against `SPIKES.md` S3, `DATA.md` D1, and `EVAL.md` §2.1.
Check specifically:
(a) every field name used exists in the 25-field schema in `DATA.md`;
(b) the value approximation matches `SPIKES.md` S3 step 3 exactly (`>=` vs `>`, OR logic, counters used);
(c) per-day grouping uses `first_seen` in UTC, and the day boundaries do not drop or double-count sessions;
(d) unit tests exercise edge cases;
(e) numbers in `base_rates.json` are plausible.
Output a list of PASS / FAIL per item with file and line evidence.

---

## QUESTIONS FOR HUMAN
Task G3 is complete. The next step in the prompt schedule is **Task O1** (Opus read-only review). Switch model to **Claude 3.7 Sonnet / Opus** to run Task O1, or let me know if you would like me to proceed.
