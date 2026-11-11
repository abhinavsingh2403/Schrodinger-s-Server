# SPIKE_RESULTS.md: Go/No-Go Technical Spike Outcomes

This ledger records the outcomes and decisions from the time-boxed technical spikes (S1 to S5) defined in `SPIKES.md`.
Gate 0 requires S1 and S3 outcomes to be recorded here before downstream development proceeds.

---

## Spike Results Template

```markdown
### S<n> <title>
Date / owner:
What was done (commands, versions, commit):
Evidence (paths in results/ or logs):
Result:
Decision (Plan A/B, go/no-go, fallback taken):
What this changes in SPEC/EVAL:
```

---

## Results Log

### S3 Data Reality Check and Base Rates (Part 1: session_aggregation)
- **Date / owner**: 2026-11-11 / P2 (ML/Analysis)
- **What was done**:
  - Downloaded `session_aggregation.jsonl.gz` (1,328,104,319 bytes) from Zenodo Record 21260400.
  - Verified MD5 checksum `1f3897650fb420c97c14ff452398c3f8` via streaming chunked verifier `analysis/verify_download.py` (`MATCH`).
  - Implemented `analysis/s3_base_rates.py` using DuckDB (v2.0.0) with unit tests in `analysis/test_s3_base_rates.py` (5 tests passing).
  - Executed `s3_base_rates.py` over the full 38,126,048 sessions.
- **Evidence**:
  - `data/session_aggregation.jsonl.gz` (MD5: `1f3897650fb420c97c14ff452398c3f8`)
  - `results/base_rates.json`
  - `results/MANIFEST.json`
- **Result**:
  - **Schema Validation**: All 25 fields listed in `DATA.md` exist exactly in the dataset. Zero missing fields.
  - **Total Sessions**: 38,126,048 across 52 days (2025-06-27 to 2025-08-17).
  - **Login Success**: 4,374,446 sessions (11.47%).
  - **Command Input**: 3,335,870 sessions (8.75%). Over 91.25% of sessions have 0 commands; p50=0, p90=0, p99=2 commands.
  - **File Transfers**: 755,225 sessions (1.98%).
  - **Direct-TCPIP Requests (Pivot)**: 467,551 sessions (1.23%).
  - **Value=1 Approximation (`N_CMD=5` OR file transfer OR pivot)**: 1,232,570 sessions (base rate = **3.23%**).
  - Note: `cnt_command_input` counts input events, not distinct commands, so this aggregate figure is an approximation.
- **Decision**:
  - Base rate of value=1 is 3.23% (~1.23M positive sessions). This is a solid, non-degenerate class imbalance well-suited for early stage gatekeeper triage and PR-AUC evaluation. No adjustment to `N_CMD=5` needed for the aggregate level.
- **What this changes in SPEC/EVAL**:
  - Confirms feasibility of Experiment 0 sampling and base-rate tracking. Ready for Opus read-only review (Task O1).
