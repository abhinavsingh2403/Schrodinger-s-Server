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

### S1 Per-session persona / escalation in Cowrie
- **Date / owner**: 2026-11-11 / P1 (Honeypot Lead)
- **What was done (commands, versions, commit)**:
  - Pinned Cowrie release tag `v3.1.6` (commit hash `ea9513eda9ea0dac05f6ace7db84ca95e0571501`) from `https://github.com/cowrie/cowrie.git`.
  - Cloned read-only copy into `sensor/cowrie-src/` for source audit and verified against PyPI package.
  - Audited code paths across Cowrie subsystems: SSH transport & version banner (`src/cowrie/ssh/transport.py`, `src/cowrie/ssh/factory.py`), key exchange & HASSH logging (`src/cowrie/ssh/transport.py`), userauth & login acceptance (`src/cowrie/ssh/userauth.py`, `src/cowrie/shell/realm.py`), shell protocol creation & fake filesystem loading (`src/cowrie/shell/session.py`, `src/cowrie/shell/fs.py`, `src/cowrie/core/honeyfs.py`), command dispatch (`src/cowrie/shell/honeypot.py`, `src/cowrie/shell/protocol.py`), and proxy/pool backends (`src/twisted/plugins/cowrie_plugin.py`).
  - Built throwaway lab proof-of-concept in `sensor/spike_s1_poc.py` demonstrating odd/even client port persona switching post-login (odd port -> `web-srv-01` Ubuntu 22.04 T2 persona; even port -> `generic-srv-02` Debian 12 T1 persona).
  - Added unit test suite `sensor/test_spike_s1_poc.py` (2 pytest test cases passing).
- **Evidence (paths in results/ or logs)**:
  - Source code citations with exact line numbers in pinned release `v3.1.6`.
  - `sensor/spike_s1_poc.py` (execution output verified via Python & Twisted).
  - `sensor/test_spike_s1_poc.py` (2 passed in 4.77s under pytest).
  - Transcript showing Session A on odd port receiving `web-srv-01` + `PERSONA_1` + Ubuntu motd, while Session B on even port receives `generic-srv-02` + `PERSONA_2` + Debian motd.
- **Result**:
  - **Hook Point Identified**: Twisted Conch session adapter boundary (`components.registerAdapter` on `CowrieUser` to `ISession`, subclassing `cowrie.shell.session.SSHSessionForCowrieUser`).
  - **Lines of Cowrie core that must change**: **0 lines**. No fork required.
  - **Subclass / plugin sufficiency**: A subclass of `SSHSessionForCowrieUser` or a custom realm/session adapter registered in the application runner is completely sufficient.
  - **Merge-pain risk**: **Extremely Low / None**. Because adaptation is done by subclassing/adapter registration outside Cowrie's internal package, upstream releases of Cowrie can be upgraded cleanly without merge conflicts.
- **Decision (Plan A/B, go/no-go, fallback taken)**:
  - **Plan A (achieved)**: In-process hook confirmed. Cowrie can cleanly switch persona (filesystem, hostname, banners, identity) per-session after login.
- **What this changes in SPEC/EVAL**:
  - Validates SPEC Section 4 Architecture (Plan A in-process hook is selected; Plan B fallback sticky routing is not required for T1/T2).
  - Gate 0 requirement for S1 is fully satisfied.

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

### S3 Data Reality Check (Part 2: Event-level Archive Verification)
- **Date / owner**: 2026-11-11 / P2 (ML/Analysis)
- **What was done**:
  - Implemented `analysis/s3_event_sample.py` using HTTP Range requests against Zenodo Record 21260400 `data_all.zip` (19.37 GB).
  - Located Zip64 End of Central Directory locator and extracted the 5,800-byte Central Directory table without downloading the full 19.4 GB archive.
  - Parsed all 52 daily file entries (`../logs_by_day/2025-06-27.json.gz` to `../logs_by_day/2025-08-17.json.gz`).
  - Streamed initial compressed DEFLATE chunks and decompressed gzip event records from `2025-06-27.json.gz`.
  - Added unit test suite `analysis/test_s3_event_sample.py` (2 tests passing).
- **Evidence**:
  - `results/s3_event_schema.json`
  - `analysis/s3_event_sample.py`
  - `analysis/test_s3_event_sample.py`
- **Result**:
  - **Archive Contents**: Exactly 52 daily files covering continuous observation period 2025-06-27 through 2025-08-17.
  - **Event Schema**: 57 unique fields discovered. All 10 required fields present: `ts`, `eventid`, `session`, `sensor`, `group`, `hassh`, `version`, `width`, `height`, `input`. Zero missing fields.
  - **Configuration Group**: Confirmed present as an integer field `group \in {1, 2, 3, 4}` corresponding to the 4 configurations (Default Baseline, Enhanced hardened, and two persistence variants).
  - **Selective Sampling**: Proved that daily event logs can be accessed on demand via HTTP range requests for Experiment 0 event-level feature extraction.
- **Decision**:
  - S3 Spike is **100% complete** across both aggregation and event-level tiers.
  - Event-level features (HASSH, client version, terminal dimensions, command text, and configuration group) are verified present.
- **What this changes in SPEC/EVAL**:
  - Unblocks EVAL.md §5.3 (Persona effect natural experiment using the `group` field).
  - Confirms data feasibility for Experiment 0 early features (S1 to S5). Gate 0 data preconditions fully verified.
