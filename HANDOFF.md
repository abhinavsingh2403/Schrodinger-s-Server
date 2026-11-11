# HANDOFF.md: Model Handoff & Progress Ledger

## STATUS
- Branch: `aftertranning`
- Current Task: Engineering Infrastructure & Experiment 0 Pipeline Complete (Ready for Model Fitting)
- Next Task: Friend runs ML training via `analysis/exp0_train.py` per `analysis/MODEL_TRAINING_GUIDE.md`

---

## DONE

### 1. Experiment 0 Pre-Declared Splitting & Rules Infrastructure
- **`analysis/exp0_splits.py`**:
  - Implements seeded random day selection (5 train, 2 val, 2 test days) and disjoint source IP grouping.
  - Generated [`results/exp0/splits.json`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/results/exp0/splits.json) with seed `20261111`:
    - Train: `['2025-07-07', '2025-07-14', '2025-07-19', '2025-07-25', '2025-07-26']`
    - Validation: `['2025-08-03', '2025-08-06']`
    - Test: `['2025-08-09', '2025-08-15']`
  - Unit tests: [`analysis/test_exp0_splits.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/test_exp0_splits.py) (6 tests passing).
- **`analysis/exp0_rules.py`**:
  - Pre-declared rules R0 (random), R1 (login success), R2 (PTY requested), R5 (version rarity), R6 (failed logins), and recall @ 10% budget evaluator.
  - Unit tests: [`analysis/test_exp0_rules.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/analysis/test_exp0_rules.py) (7 tests passing).
- **`results/exp0/grid.json`**:
  - Pre-declared hyperparameter grid for Logistic Regression and HistGradientBoostingClassifier.
- **`analysis/exp0_train.py`**:
  - End-to-end extraction and evaluation script with DuckDB queries.
- **`analysis/MODEL_TRAINING_GUIDE.md`**:
  - Instructions and time estimates for running the ML model training.

---

### 2. Phase 1 Gatekeeper Engine & Visitor Memory
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

---

### 3. Sensor Identity Configuration
- **`sensor/identity.yaml`**:
  - Unified system identity profile (Ubuntu 22.04 LTS, Linux 5.15.0-88-generic, OpenSSH 8.9p1) ensuring cross-tier coherence per SPEC.md Section 5.1 & Risk R8.

---

### 4. Test Configuration & Global Status
- **`pytest.ini`**: Configured to include `analysis`, `gatekeeper`, and `sensor` while ignoring `sensor/cowrie-src`.
- **Unit Test Outcome**: **32 passed in 0.22s** across `analysis/` and `gatekeeper/` (plus 2 passing in `sensor/test_spike_s1_poc.py`).

---

## FILES
- `analysis/exp0_splits.py` (new)
- `analysis/test_exp0_splits.py` (new)
- `analysis/exp0_rules.py` (new)
- `analysis/test_exp0_rules.py` (new)
- `analysis/exp0_train.py` (new)
- `analysis/MODEL_TRAINING_GUIDE.md` (new)
- `gatekeeper/visitor_memory.py` (new)
- `gatekeeper/test_visitor_memory.py` (new)
- `gatekeeper/policy.py` (new)
- `gatekeeper/test_policy.py` (new)
- `gatekeeper/feature_extractor.py` (new)
- `gatekeeper/test_feature_extractor.py` (new)
- `sensor/identity.yaml` (new)
- `pytest.ini` (new)
- `results/exp0/splits.json` (new)
- `results/exp0/grid.json` (new)
- `HANDOFF.md` (modified)

---

## COMMANDS AND OUTCOMES
1. `git checkout -b aftertranning; git push -u origin aftertranning`: Created and pushed new branch.
2. `.\.venv\Scripts\python analysis/exp0_splits.py`: Generated `results/exp0/splits.json` with 5 train, 2 val, 2 test days.
3. `.\.venv\Scripts\python.exe -m pytest analysis/ gatekeeper/`: **32 passed in 0.22s**.
4. `wsl /tmp/cowrie-lab-venv/bin/python3 -m pytest sensor/test_spike_s1_poc.py`: **2 passed in 4.77s**.

---

## TODO(verify)
- When the friend runs `analysis/exp0_train.py`, record the model recall @ 10% budget and compare against best simple rule.
