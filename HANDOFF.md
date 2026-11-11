# HANDOFF.md: Model Handoff & Progress Ledger

## STATUS
- Current Task: O1 (Complete — Opus Read-Only Review of G3)
- Next Task: O2 (SPIKES S1: Cowrie per-session persona)

---

## DONE
### Task O1: Read-Only Review of G3 (Opus)

Review of `analysis/s3_base_rates.py`, `analysis/test_s3_base_rates.py`, `results/base_rates.json`, and `results/MANIFEST.json` against `SPIKES.md` S3, `DATA.md` D1, and `EVAL.md` §2.1.

---

### (a) Field names match the 25-field schema in DATA.md: **PASS**

- **Evidence**: `SCHEMA_25_FIELDS` in [s3_base_rates.py lines 23–49](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/s3_base_rates.py#L23-L49) contains exactly 25 fields.
- Verified programmatically: both set equality and list equality (preserving order) confirmed against the comma-separated list in [DATA.md line 32](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/DATA.md#L32).
- `verify_schema()` at [line 66](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/s3_base_rates.py#L66-L83) checks actual columns from DuckDB against this list and raises `ValueError` on any missing field. Real dataset run confirmed: "SCHEMA CHECK PASSED: All 25 fields exist exactly."
- No invented or misspelled field names.

### (b) Value approximation matches SPIKES S3 step 3 exactly: **PASS**

- **SPIKES.md S3 step 3** (line 49): `cnt_command_input >= 5 or file transfer or pivot`
- **EVAL.md §2.1** (line 25): `value = 1` if (a) at least 5 distinct commands; (b) at least one file download or upload; (c) at least one direct-tcpip request.
- **EVAL.md §2.1** (line 28): for aggregate approximation, use `cnt_command_input >= 5`.
- **Code** [s3_base_rates.py lines 92–98](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/s3_base_rates.py#L92-L98):
  ```python
  val_expr = (
      f"(cnt_command_input >= {n_cmd} "
      f"OR (cnt_file_upload + cnt_file_download) > 0 "
      f"OR cnt_direct_tcpip_request > 0)"
  )
  ```
- **Operator correctness**: `>=` for command threshold (correct per ≥5), `>` for file transfer and pivot counts (correct: "at least one" means > 0).
- **Field correctness**: Uses `cnt_file_upload` and `cnt_file_download` (correct per EVAL.md which says "file download or upload"). Does NOT use `cnt_file_download_failed` (correct — that field counts failed downloads, not successful ones). Does NOT use `cnt_direct_tcpip_data` (correct — that field counts data events, not requests).
- **OR logic**: Three-way OR, matching all three specs.
- **N_CMD parameterization**: Defaults to 5, exposed as `--n-cmd` CLI argument. Does not change the default.

### (c) Per-day grouping uses first_seen in UTC; no drop or double-count: **PASS**

- **Code** [s3_base_rates.py line 139](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/s3_base_rates.py#L139):
  ```python
  day_expr = "COALESCE(strftime(TRY_CAST(first_seen AS TIMESTAMP), '%Y-%m-%d'), 'UNKNOWN')"
  ```
  Uses `first_seen` cast to `TIMESTAMP` and formatted to `%Y-%m-%d` (UTC date). `TRY_CAST` prevents exceptions on malformed values; `COALESCE` to `'UNKNOWN'` catches any that fail to parse.
- **Integrity assertions** [lines 178–186](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/s3_base_rates.py#L178-L186): Code explicitly checks that `sum(daily_total) == total` and `sum(daily_val1) == total_val1`, raising `ValueError` on mismatch. This guarantees no sessions are dropped or double-counted.
- **Verified on real data**: Validation script confirmed `Day total sum: 38126048, matches overall: True` and `Day val1 sum: 1232570, matches overall: True`.
- **Day span**: 52 days from 2025-06-27 to 2025-08-17. DATA.md says "50 continuous days". The 52-day count likely reflects the dataset spanning slightly beyond 50 calendar days, or partial first/last days. This is **not a bug** — it reflects the actual data. The script does not impose a 50-day filter (nor should it).

### (d) Tests exercise edge cases and would fail if logic were wrong: **PASS**

- **[test_s3_base_rates.py](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/test_s3_base_rates.py)** creates a synthetic 10-row JSONL with specifically targeted edge cases:
  - **s1**: Exactly 4 commands → value=0 (boundary: N_CMD-1). Would catch off-by-one in `>=` vs `>`.
  - **s2**: Exactly 5 commands → value=1 (boundary: N_CMD). Would catch `>` instead of `>=`.
  - **s3**: File upload only, no login success → value=1. Tests file-upload-only path.
  - **s4**: File download only → value=1. Tests file-download-only path.
  - **s5**: Direct-tcpip only → value=1. Tests pivot-only path.
  - **s6**: No login, 0 commands, probe only → value=0. Tests pure probe.
  - **s7**: 2 commands → value=0 (bin 1–4). Tests below-threshold.
  - **s8**: 8 commands → value=1 (bin 5–9). Tests mid-range.
  - **s9**: 15 commands → value=1 (bin 10+). Tests high range.
  - **s10**: Login success, 0 commands → value=0. Tests login-only.
- Assertions at [lines 117–120](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/test_s3_base_rates.py#L117-L120) check that exactly 6 sessions have value=1 (`s2, s3, s4, s5, s8, s9`). An off-by-one on `>=` would make this 5 (failing). Wrong OR logic (AND instead) would reduce it further.
- Daily sum assertions at [lines 138–140](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/test_s3_base_rates.py#L138-L140) verify per-day totals equal overall.
- `test_missing_schema_field` at [lines 153–166](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/test_s3_base_rates.py#L153-L166) confirms schema validation catches a missing field.

### (e) Numbers in base_rates.json are plausible: **PASS**

- **Total sessions**: 38,126,048. DATA.md says "38 million SSH sessions". ✓
- **Login success share**: 11.47% (4.37M of 38.1M). Plausible — most SSH probes fail authentication.
- **Command input share**: 8.75%. Slightly less than login success, which makes sense (some sessions log in but issue no commands).
- **Distribution bins**: Sum to exactly 38,126,048. ✓ Shares sum to exactly 1.0. ✓ The heavy concentration at 0 (91.25%) aligns with the published observation that >99% of sessions in another deployment were non-interactive (CLAIMS P2 — different dataset, different deployment, so the exact rate differs but the qualitative finding is consistent).
- **Quantiles**: p50=0, p90=0, p99=2. Consistent with 91.25% at zero.
- **File transfer share**: 1.98% (755K). Plausible for a large honeypot deployment.
- **Direct-tcpip share**: 1.23% (468K). Plausible.
- **Value=1 base rate**: 3.23% (1.23M). This is higher than the non-interactive rate from P2 (which was ~0.1% interactive), but that deployment used LLMs and had different configuration. The 3.23% here includes sessions with ≥5 input events OR file transfers OR pivots across 160 instances with 4 configurations including persistence-enabled variants. Plausible and not degenerate.
- All shares are in [0, 1]. No negative counts. No day has an invalid base rate. ✓

---

### Summary: ALL FIVE CHECKS PASS

| Check | Result | Key Evidence |
|---|---|---|
| (a) Field names match DATA.md 25-field schema | **PASS** | Programmatic set+list equality; real data schema check passed |
| (b) Value approximation matches SPIKES S3 step 3 | **PASS** | `>=5` / `>0` / `>0` with correct fields and OR logic |
| (c) Per-day grouping: first_seen UTC, no drop/double-count | **PASS** | Integrity assertions in code; verified sums on real data |
| (d) Tests exercise edge cases; would catch logic errors | **PASS** | Boundary tests at N_CMD-1/N_CMD, single-trigger paths, daily sums |
| (e) Numbers plausible | **PASS** | 38.1M sessions, 3.23% value=1, all shares ∈ [0,1], bins sum exactly |

### Concrete Fixes Required: **NONE**

No logic, schema, or statistical errors found. The implementation is correct.

---

## FILES
- `HANDOFF.md` (modified — this update)

---

## COMMANDS AND OUTCOMES
1. Numerical validation script: All checks passed (bin sums, share ranges, daily sums, field counts).
2. Schema field-name check: Exact match (25/25, content and order).

---

## TODO(verify)
- The dataset spans 52 calendar days (2025-06-27 to 2025-08-17) while DATA.md says "50 continuous days". This is not a code bug — it reflects the actual data. The human should note this in `DECISIONS.md` after confirming with the dataset descriptor.

---

## QUESTIONS FOR OPUS
*(None — O1 is complete. Next Opus task is O2: SPIKES S1.)*

---

## QUESTIONS FOR HUMAN
- The 52-day span vs. documented "50 days" should be checked against the dataset descriptor when it is read in S3 Part 2. No action needed now; just record the observation.
- Ready for **Task O2** (SPIKES S1: Cowrie per-session persona investigation).
