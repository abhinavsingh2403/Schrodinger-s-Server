# Experiment 0: Model Training & Evaluation Guide

This guide is for the person training the Experiment 0 models on the pre-declared splits.

---

## 1. Estimated Training & Processing Time

| Step | Dataset / Workload | Estimated Duration | Hardware Requirements |
|---|---|:---:|---|
| **1. Split Feature Extraction** | DuckDB querying `data/session_aggregation.jsonl.gz` across 9 sampled days (5 train, 2 val, 2 test) | **~2 to 4 minutes** | Multi-core CPU, 8GB+ RAM |
| **2. Logistic Regression** | L2-regularized LogisticRegression (`C=[0.01, 0.1, 1.0, 10.0]`) on ~3.5M rows | **~1 to 3 minutes** | CPU |
| **3. Gradient-Boosted Trees** | `HistGradientBoostingClassifier` or `LightGBM` tuning across grid in `results/exp0/grid.json` | **~3 to 6 minutes** | Multi-core CPU |
| **4. Cluster Bootstrap Evaluation** | 10,000 paired resamples by source IP for Delta CI at 10% budget | **~3 to 5 minutes** | CPU |
| **Total End-to-End Time** | Complete extraction, training, validation tuning, and evaluation | **~10 to 18 minutes** | Standard PC / Laptop |

*(Note: If training over all 38.1 million sessions without day sampling, extraction takes ~8–12 minutes and tree training takes ~25–35 minutes).*

---

## 2. Pre-Declared Setup (Frozen per `exp0-v1`)

- **Split Configuration**: [`results/exp0/splits.json`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/results/exp0/splits.json) (Seed `20261111`)
  - **Train Days (5)**: `['2025-07-07', '2025-07-14', '2025-07-19', '2025-07-25', '2025-07-26']`
  - **Validation Days (2)**: `['2025-08-03', '2025-08-06']`
  - **Test Days (2)**: `['2025-08-09', '2025-08-15']`
  - **Disjoint Source IP Grouping**: Handled automatically. IPs appearing in earlier folds are purged from later folds to guarantee zero leakage.
- **Hyperparameter Grid**: [`results/exp0/grid.json`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/results/exp0/grid.json)
  - `LogisticRegression`: `C in [0.01, 0.1, 1.0, 10.0]`, L2 penalty, balanced class weight.
  - `HistGradientBoosting`: `max_iter in [100, 200]`, `learning_rate in [0.05, 0.1]`, `max_leaf_nodes in [15, 31]`.

---

## 3. How to Run

### Step 1: Extract Disjoint Parquet Splits
Run from repository root:
```powershell
.\.venv\Scripts\python analysis/exp0_train.py --extract-only
```
This generates:
- `results/exp0/train.parquet`
- `results/exp0/val.parquet`
- `results/exp0/test.parquet`
- Evaluates baseline rules R0 (random), R1 (login success), R6 (failed attempts) on validation and test sets.

### Step 2: Fit Models & Evaluate
Run the full training and evaluation runner:
```powershell
.\.venv\Scripts\python analysis/exp0_train.py
```

### Step 3: Check Decision Outcome (`EXPERIMENT0.md §12`)
- **PASS-ML**: If ML model recall @ 10% budget beats best simple rule by $\ge 0.05$ (5% absolute recall) at pre-command stages (S1–S3) with lower CI bound $> 0$.
- **PASS-LATE-ONLY**: If improvement occurs only after first command (S4–S5).
- **FAIL**: If simple rules perform as well as the learned models.
