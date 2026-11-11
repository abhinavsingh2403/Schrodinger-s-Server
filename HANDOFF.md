# HANDOFF.md: Model Handoff & Progress Ledger

## STATUS & PROGRESS ACCOUNTING
- **Branch**: `aftertranning` (tracking `origin/aftertranning`)
- **Rigorous Project Progress Assessment**:
  - **Engineering (Code & Tests)**: **~55–60%** (75 passing unit tests across gatekeeper, sensor, router, harness, infra, analysis, and dashboard).
  - **Science (Valid Empirical Results)**: **~15–20%** (Base rates S3 Part 1 verified, event-level schema S3 Part 2 verified; Experiment 0 and live trials remain gated).
  - **Overall MVP**: **~35–38%**.
  - **Experiment 0 Status**: **0%** (splits and baseline rules prepared; model fitting and paired cluster-bootstrap pending Gate 0 execution).

---

## CRITICAL SCIENTIFIC NOTICES ON RECENT COMMITS

1. **Arm Simulation ([`analysis/simulate_arms.py`](analysis/simulate_arms.py)) is an ORACLE HINDSIGHT UPPER BOUND**:
   - The simulation in `analysis/simulate_arms.py` uses whole-session cumulative counters (`cnt_command_input`, `cnt_file_download`, `cnt_file_upload`, `cnt_direct_tcpip_request`) from `session_aggregation.jsonl.gz`.
   - This represents a retrospective *Oracle Upper Bound* (hindsight policy), **NOT** an online early-decision gatekeeper.
   - It assumes yield is invariant to honeypot persona ($Y_{\text{observed}}$ held constant across tiers). Under this uniform-yield assumption, Arm A (Static T1) is mathematically cheapest per yield unit (₹3.98 cost $\to$ 595.7 Yield/₹ vs ₹86.70 cost $\to$ 27.4 Yield/₹ for Arm D), because cheap shells incur near-zero resource cost while ignoring persona-driven session truncation.
   - The ~30x efficiency advantage of Arm D applies exclusively when compared against unpruned static virtualization (Arm C, ₹2,564.68).
   - This simulation is labeled as `SIMULATED_ORACLE (Hindsight Upper Bound)` in [`results/arm_simulation.json`](results/arm_simulation.json) and dashboard APIs.

2. **Natural Experiment ([`analysis/natural_experiment.py`](analysis/natural_experiment.py)) Persona Evaluation is PENDING EVENT DATA**:
   - EVAL.md §5.3 mandates measuring the persona effect across the four Cowrie configurations using the configuration `group` field.
   - As verified in DATA.md and SPIKES S3 Part 2, `session_aggregation.jsonl.gz` does not contain `group`.
   - Grouping sessions by `honeypot_ip` in `session_aggregation` reflects deployment-level variance across IP addresses (which is confounded by scanner targeting and network topography), **NOT** a persona natural experiment.
   - EVAL 5.3 persona evaluation is therefore marked as `EVAL_53_PERSONA_EFFECT_PENDING_EVENT_GROUP_DATA` until event-level logs from `data_all.zip` are ingested.

---

## ENGINEERING SUBSYSTEMS COMPLETED (Branch `aftertranning`)

### 1. Data Reality Checks (Spike S3 Parts 1 & 2)
- **S3 Part 1 (Aggregate)**: [`analysis/s3_base_rates.py`](analysis/s3_base_rates.py) computed ground-truth base rates across all 38,126,048 sessions (`results/base_rates.json`): 3.23% value=1 base rate.
- **S3 Part 2 (Event Archive)**: [`analysis/s3_event_sample.py`](analysis/s3_event_sample.py) inspected `data_all.zip` via HTTP range requests without downloading 19.4 GB. Verified all 52 daily files and confirmed all 10 required fields (`ts`, `eventid`, `session`, `sensor`, `group`, `hassh`, `version`, `width`, `height`, `input`), discovering `group \in {1, 2, 3, 4}`. (Results in [`results/s3_event_schema.json`](results/s3_event_schema.json)).

### 2. Experiment 0 Pre-Declared Splitting & Rules Infrastructure
- **`analysis/exp0_splits.py`**:
  - Implements seeded random day selection (5 train, 2 val, 2 test days) and disjoint source IP grouping per `EXPERIMENT0.md §3`.
  - Generated [`results/exp0/splits.json`](results/exp0/splits.json) with seed `20261111`:
    - Train (5 days): `['2025-07-07', '2025-07-14', '2025-07-19', '2025-07-25', '2025-07-26']`
    - Validation (2 days): `['2025-08-03', '2025-08-06']`
    - Test (2 days): `['2025-08-09', '2025-08-15']`
- **`analysis/exp0_rules.py`**: Pre-declared baseline rules R0, R1, R2, R5, R6, R7, and recall @ 10% budget evaluator.
- **`results/exp0/grid.json`**: Pre-declared hyperparameter grid for Logistic Regression and HistGradientBoostingClassifier.
- **`analysis/exp0_train.py`**: Parquet extraction, rule evaluation, paired cluster bootstrap, and Gate 0 decision rule evaluator.

### 3. Gatekeeper Engine & Decision API
- **`gatekeeper/visitor_memory.py`**: SQLite WAL visitor memory with salted HMAC-SHA256 privacy masking (`vis_xxxx`), monotone upward-only tier tracking (T1 $\to$ T2 $\to$ T3), and fail-cheap defaults.
- **`gatekeeper/policy.py`**: Upward-only escalation policy engine checking current tier, model score, thresholds, and visitor memory.
- **`gatekeeper/feature_extractor.py`**: Offline/live parity module extracting cumulative stage features (S1 to S5) identically for live events and offline batch lists.
- **`gatekeeper/decision_api.py`**: Sub-millisecond in-process coordinator with SQLite WAL decision log.

### 4. Sensor & Router Architecture
- **`sensor/adaptive_server.py`**: Subclasses Twisted Conch session adapter to overlay custom filesystems and MOTDs dynamically per session, maintaining OS persona coherence (Ubuntu 22.04 LTS).
- **`router/sticky_router.py`**: Plan B standalone asyncio TCP stream splicer routing connections to tier backends based on visitor memory without mutating SSH byte streams.

### 5. Adversary Lab Harness & Hardening
- **`harness/detector_runner.py`**: Lab auditor verifying OS coherence and Cowrie giveaways. Enforces hardcoded SAFETY.md allowlist (throws `SafetyViolationError` on non-loopback targets).
- **`harness/replay/replay_engine.py`**: Replays realistic botnet attack traces (`mass_scanner_probe`, `reconnaissance_bot`, `cryptominer_dropper`, `persistence_installer`) with SAFETY.md allowlist check.
- **`infra/` Hardening Overlays**: `cowrie.cfg` (Telnet disabled, OpenSSH 8.9p1 identity), `egress_firewall.sh` (zero-trust iptables dropping all outbound internet traffic), `docker-compose.yml` (`internal: true` isolated bridge).

### 6. Read-Only Dashboard & API
- **`dashboard/app.py`**: Self-contained HTTP server serving Cyber Protocol theme (`#040711` midnight void, `#00FF41` cyber green, `#38BDF8` cyber cyan).
- Enforces cryptographic privacy masking (`vis_xxxx`) with zero raw IPs exposed.
- All panels labeled explicitly as **RECORDED**, **LAB**, or **LIVE**. Experimental arms labeled as **SIMULATED ORACLE MODEL**.

---

## TEST SUITE SUMMARY
- **Total Test Cases**: **75 passed, 1 skipped** in 0.95s.
- `analysis/`: 33 passed
- `gatekeeper/`: 17 passed
- `sensor/`: 4 passed (+1 skipped on Windows due to twisted.conch)
- `router/`: 4 passed
- `harness/`: 9 passed (5 detector runner + 4 replay engine)
- `dashboard/`: 5 passed
- `infra/`: 3 passed

---

## INSTRUCTIONS FOR FRIEND (MODEL TRAINING & GATE 0 EVALUATION)

See [`analysis/MODEL_TRAINING_GUIDE.md`](analysis/MODEL_TRAINING_GUIDE.md):
```bash
# In project root with active venv:
python analysis/exp0_train.py
```

### Pre-Registered Gate 0 Decision Rule (`EXPERIMENT0.md §12`):
Let $\delta = 0.05$ (5% absolute recall improvement at the 10% escalation budget):
$$\Delta_k = \text{Recall}_{\text{ML}}(k) - \text{Recall}_{\text{bestRule}}(k)$$
- **PASS-ML**: Stage $k \in \{S1, S2, S3\}$ achieves $\Delta_k \ge 0.05$ with the lower bound of its 95% cluster-bootstrap confidence interval $> 0$.
- **PASS-LATE-ONLY**: S1–S3 fails, but stage $k \in \{S4, S5\}$ achieves $\Delta_k \ge 0.05$ with lower CI $> 0$.
- **FAIL**: Otherwise (simple rules match or exceed learned models at pre-command stages). The project reframes as a rule-based cost-yield study per `EXPERIMENT0.md §13`.
