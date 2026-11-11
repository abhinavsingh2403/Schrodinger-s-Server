# HANDOFF.md: Model Handoff & Progress Ledger

## STATUS
- Branch: `aftertranning`
- Current Status: **All Non-Training Engineering Subsystems 100% Complete & Verified**
- Ready For: Friend executes ML model training via `analysis/exp0_train.py` per [`analysis/MODEL_TRAINING_GUIDE.md`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/MODEL_TRAINING_GUIDE.md)

---

## DONE ON BRANCH `aftertranning`

### 1. Experiment 0 Pre-Declared Splitting & Rules Infrastructure
- **`analysis/exp0_splits.py`**:
  - Implements seeded random day selection (5 train, 2 val, 2 test days) and disjoint source IP grouping per `EXPERIMENT0.md §3`.
  - Generated [`results/exp0/splits.json`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/results/exp0/splits.json) with seed `20261111`:
    - Train (5 days): `['2025-07-07', '2025-07-14', '2025-07-19', '2025-07-25', '2025-07-26']`
    - Validation (2 days): `['2025-08-03', '2025-08-06']`
    - Test (2 days): `['2025-08-09', '2025-08-15']`
  - Unit tests: [`analysis/test_exp0_splits.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/test_exp0_splits.py) (6 tests passing).
- **`analysis/exp0_rules.py`**:
  - Pre-declared baseline rules R0 (random), R1 (login success), R2 (PTY requested), R5 (version rarity), R6 (failed logins), and recall @ 10% budget evaluator.
  - Unit tests: [`analysis/test_exp0_rules.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/test_exp0_rules.py) (7 tests passing).
- **`results/exp0/grid.json`**:
  - Pre-declared hyperparameter grid for Logistic Regression and HistGradientBoostingClassifier.
- **`analysis/exp0_train.py`**:
  - End-to-end extraction and evaluation script with DuckDB queries.
- **`analysis/MODEL_TRAINING_GUIDE.md`**:
  - Step-by-step instructions and timing estimates (~10–18 min for 9-day sample, ~35–50 min for full 38.1M sessions) for running the ML model training.

---

### 2. Phase 1 Gatekeeper Engine & Decision API
- **`gatekeeper/visitor_memory.py`**:
  - SQLite database in WAL mode tracking visitors via salted HMAC-SHA256 (`derive_visitor_id`, `get_masked_id`).
  - Monotone upward-only tier tracking (`highest_tier_served`: T1 -> T2 -> T3, never downgraded).
  - Fail-cheap rule: Never drops connections or crashes on DB lock/error (defaults safely to T1).
  - Unit tests: [`gatekeeper/test_visitor_memory.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/gatekeeper/test_visitor_memory.py) (4 tests passing).
- **`gatekeeper/policy.py`**:
  - Upward-only escalation policy engine checking current tier, model score, thresholds, and visitor memory.
  - Unit tests: [`gatekeeper/test_policy.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/gatekeeper/test_policy.py) (7 tests passing).
- **`gatekeeper/feature_extractor.py`**:
  - Offline / live parity module (AGENTS.md Rule 10): Extracts cumulative stage features (S1 to S5) identically for live events and offline batch lists.
  - Temporal leakage guard: Future events do not mutate earlier stage features.
  - Unit tests: [`gatekeeper/test_feature_extractor.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/gatekeeper/test_feature_extractor.py) (3 tests passing).
- **`gatekeeper/decision_api.py`**:
  - Core in-process and API coordinator integrating visitor memory, feature extraction, scoring, policy, and SQLite WAL decision log.
  - Sub-millisecond latency (<0.5 ms p95 in local memory).
  - Unit tests: [`gatekeeper/test_decision_api.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/gatekeeper/test_decision_api.py) (3 tests passing).

---

### 3. Specifications & Configuration Subsystem (`config/`)
Created canonical configuration files per `SPEC.md §10`:
- **`config/attack_map.yaml`**: MITRE ATT&CK technique tags and regex triggers (T1082, T1033, T1057, T1083, T1046, T1105, T1059.004, T1053.003, T1098.004, T1070.004, T1496).
- **`config/identity.yaml`**: Master system identity profile (Ubuntu 22.04 LTS, kernel 5.15.0-88-generic, OpenSSH 8.9p1).
- **`config/policy.yaml`**: Pre-declared decision thresholds ($\tau_{V2}$, $\tau_{V3}$, $\tau_A$) and escalation budgets.
- **`config/arms.yaml`**: RCT arm definitions (Arm A: T1 static, Arm B: T2 static, Arm C: T3 static, Arm D: Schrödinger adaptive).
- **`config/stages.yaml`**: Stage definitions and feature availability (S0 through S5).

---

### 4. Cost & Intelligence Yield Accounting Engine (`analysis/cost_model.py`)
- Pre-registered in `SPEC.md §9` and `EVAL.md §6`:
  - Session Yield: $Y = w_{\text{cmd}} \cdot \frac{\min(D, 20)}{20} + w_{\text{file}} \cdot 1[F \ge 1] + w_{\text{pivot}} \cdot 1[P \ge 1] + w_{\text{ttp}} \cdot \frac{\min(K, 8)}{8}$
  - Session Cost: $C = c_{\text{cpu}} \cdot \text{cpu\_seconds} + c_{\text{ram}} \cdot \text{gb\_seconds} + c_{\text{boot}} \cdot \text{vm\_boots}$
  - Metric: $\text{Yield per Rupee} = \sum Y / \sum C$.
  - ATT&CK Technique Classifier: Regex extraction from command streams.
  - EVAL 6 Sensitivity Analysis: Monte Carlo sampling over random weight distributions.
- Unit tests: [`analysis/test_cost_model.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/test_cost_model.py) (7 tests passing).

---

### 5. Sensor Production Adaptive Adapter (`sensor/adaptive_server.py`)
- Integrates Spike S1 PoC with `gatekeeper.decision_api.DecisionEngine`:
  - `PersonaManager`: Generates filesystem overlays and MOTD maintaining strict OS identity coherence (Ubuntu 22.04) across all tiers (SPEC Risk R8).
  - `AdaptiveSessionAdapter`: Ties Cowrie events (`on_kex_completed`, `on_auth_completed`, `on_command_received`) to the decision engine, executing upward-only tier escalation with fail-cheap defaults to T1.
- Unit tests: [`sensor/test_adaptive_server.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/sensor/test_adaptive_server.py) (4 tests passing).

---

### 6. Sticky Multi-Instance TCP Router Fallback (`router/sticky_router.py`)
- Pre-registered in `SPEC.md §5.3` (Plan B fallback):
  - Asyncio TCP stream splicing to internal tier backends based on visitor memory lookup at accept time.
  - Preserves pure byte-for-byte fidelity without touching or modifying the SSH byte stream.
  - Invariant: Sticky, monotone upward routing, fail-cheap fallback to T1.
- Unit tests: [`router/test_sticky_router.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/router/test_sticky_router.py) (4 tests passing).

---

### 7. Adversary Lab Detector Audit Runner (`harness/detector_runner.py`)
- Pre-registered in `SPEC.md §5.4`, `SAFETY.md`, and `SPIKES.md` S4:
  - Automated detectability and OS-coherence audits against honeypot instances.
  - **Strict SAFETY.md Enforcement**: Hardcoded `is_target_allowlisted` check. Throws `SafetyViolationError` if any non-loopback or non-lab target is specified.
  - Probes OS coherence, filesystem giveaways (default Cowrie traces like `/home/richard`), and SSH banner compliance (RFC 4253).
- Unit tests: [`harness/test_detector_runner.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/harness/test_detector_runner.py) (5 tests passing).

---

### 8. Read-Only Results Dashboard (`dashboard/app.py`)
- Pre-registered in `SPEC.md §4` and `AGENTS.md` Rule 19:
  - Self-contained HTTP server serving executive dark-mode dashboard with zero npm or external pip dependencies.
  - Cyber Protocol color palette (`#040711` midnight void, `#00FF41` cyber green, `#0B111E` slate card, `#38BDF8` cyan).
  - Explicitly labels every panel as **RECORDED**, **LAB**, or **LIVE**.
  - Enforces cryptographic privacy masking: all attacker IPs displayed as `vis_xxxx` with zero raw IPs committed or displayed.
  - JSON API endpoints: `/api/stats`, `/api/decisions`, `/api/arms`.
- Unit tests: [`dashboard/test_dashboard.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/dashboard/test_dashboard.py) (4 tests passing).

---

### 9. Botnet Trace Replay Engine (`harness/replay/replay_engine.py`)
- Pre-registered in `SPEC.md §8` and `EVAL.md §5.5`:
  - Lab replay harness simulating 4 realistic botnet trace archetypes (`mass_scanner_probe`, `reconnaissance_bot`, `cryptominer_dropper`, `persistence_installer`).
  - Strict `SAFETY.md` allowlist enforcement: refuses non-loopback / non-lab targets with `SafetyViolationError`.
- Unit tests: [`harness/replay/test_replay_engine.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/harness/replay/test_replay_engine.py) (4 tests passing).

---

### 10. Infrastructure Isolation & Hardened Overlays (`infra/`)
- Pre-registered in `SPEC.md §10` and `SAFETY.md`:
  - `infra/cowrie.cfg`: Telnet disabled, SSH on 127.0.0.1:2222, OpenSSH 8.9p1 identity, JSON event logging enabled.
  - `infra/egress_firewall.sh`: Zero-trust iptables policy dropping all outbound internet traffic while permitting loopback IPC.
  - `infra/docker-compose.yml`: Fully isolated stack with internal-only bridge network (`internal: true`).
- Unit tests: [`infra/test_infra_configs.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/infra/test_infra_configs.py) (3 tests passing).

---

### 11. Empirical Arm Simulation Pipeline (`analysis/simulate_arms.py`)
- Pre-registered in `EVAL.md §5.1` and `SPEC.md §9`:
  - Evaluates yield, INR cost, and yield-per-rupee across 50,000 real-world Cowrie sessions via DuckDB streaming.
  - Generated [`results/arm_simulation.json`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/results/arm_simulation.json):
    - Arm A (Static T1): 50,000 T1 sessions, cost 3.98 INR, yield-per-rupee 595.73.
    - Arm B (Static T2): 50,000 T2 sessions, cost 8.96 INR, yield-per-rupee 264.77.
    - Arm C (Static T3): 50,000 T3 sessions, cost 2564.68 INR, yield-per-rupee 0.92.
    - Arm D (Adaptive): 48,377 T1, 48 T2, 1,575 T3 sessions (3.25% escalation rate), cost 86.70 INR (96.6% cost reduction vs Arm C), yield-per-rupee 27.35 (29.6x higher efficiency than Arm C).
- Unit tests: [`analysis/test_simulate_arms.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/test_simulate_arms.py) (2 tests passing).

---

### 12. Natural Experiment Observational Associations (`analysis/natural_experiment.py`)
- Pre-registered in `EVAL.md §5.3` and `DATA.md D1`:
  - Analyzes observational session outcomes across the 160 honeypot instances via DuckDB streaming.
  - Computes two-sided Wilson 95% confidence intervals for binomial value rates.
  - Generated [`results/natural_experiment.json`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/results/natural_experiment.json):
    - 160 instances evaluated across 100,000 sessions.
    - Mean instance value rate: 4.85% (range: 0.0% to 27.56%).
    - Lower quartile (40 instances, 34,195 sessions): value rate 1.11% (Wilson 95% CI: [1.01%, 1.23%]), login rate 3.52%, 0.086 cmds/session.
    - Higher quartile (40 instances, 16,888 sessions): value rate 11.17% (Wilson 95% CI: [10.71%, 11.66%]), login rate 33.06%, 0.416 cmds/session.
    - Observed value rate ratio (Q4 to Q1): 10.03x.
    - Embeds strict scientific caveat: "Findings are reported strictly as empirical associations with no causal language...".
- Unit tests: [`analysis/test_natural_experiment.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/test_natural_experiment.py) (4 tests passing).

---

## TEST SUITE SUMMARY
- **Total Test Cases**: **72 passed, 1 skipped** in 0.83s.
- `analysis/`: 31 passed
- `gatekeeper/`: 17 passed
- `sensor/`: 4 passed (adaptive) + 1 skipped (twisted conch on Windows, runs in WSL)
- `router/`: 4 passed
- `harness/`: 9 passed (5 detector + 4 replay)
- `dashboard/`: 4 passed
- `infra/`: 3 passed

---

## INSTRUCTIONS FOR FRIEND (MODEL TRAINING)
See [`analysis/MODEL_TRAINING_GUIDE.md`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/MODEL_TRAINING_GUIDE.md):
```bash
# In project root with active venv:
python analysis/exp0_train.py --sample-days
# Optional full run on all 52 days:
python analysis/exp0_train.py --full
```
The script will output `results/exp0/results.json`, compare validation recall @ 10% budget against baseline rules (R0, R1, R2, R5, R6), evaluate against Gate 0 criterion (Recall $\ge 50\%$), and write `EXP0_RESULT.md`.
