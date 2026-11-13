"""Exports the trained Stage S3 Logistic Regression model artifact.

Trained strictly on train.parquet (with feature leakage guards).
Computes the 10% escalation budget threshold on validation.parquet per EXPERIMENT0.md §6.
Saves model_s3.json to models/ and results/exp0/ with full metadata for Gatekeeper inference.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.exp0_rules import PurePythonLogisticRegression, recall_at_budget
from gatekeeper.features import stage_vector
from analysis.exp0_train import STAGE_ALLOWED_FEATURES, load_parquet_as_dict_records


def export_s3_model() -> Path:
    train_pq = PROJECT_ROOT / "results" / "exp0" / "train.parquet"
    val_pq = PROJECT_ROOT / "results" / "exp0" / "val.parquet"
    test_pq = PROJECT_ROOT / "results" / "exp0" / "test.parquet"

    print("Loading datasets...")
    train_records = load_parquet_as_dict_records(train_pq, sample_limit=50000)
    val_records = load_parquet_as_dict_records(val_pq)
    test_records = load_parquet_as_dict_records(test_pq)

    features = STAGE_ALLOWED_FEATURES["S3"]
    print(f"Stage S3 features ({len(features)}): {features}")

    def get_features(records):
        X = [stage_vector("S3", r) for r in records]
        y = [int(r.get("v_full", 0)) for r in records]
        return X, y

    X_tr, y_tr = get_features(train_records)
    X_val, y_val = get_features(val_records)
    X_te, y_te = get_features(test_records)

    # C=0.01 was pre-declared in grid.json and selected on validation
    print("Fitting PurePythonLogisticRegression(C=0.01)...")
    t0 = time.time()
    model = PurePythonLogisticRegression(C=0.01, max_iter=60, lr=0.5)
    model.fit(X_tr, y_tr)
    t1 = time.time()
    print(f"Model fit complete in {t1 - t0:.2f}s")

    # Evaluate validation recall and determine 10% budget cutoff threshold
    val_scores = model.predict_proba(X_val)
    val_recall = recall_at_budget(val_scores, y_val, budget=0.10)

    k_val = max(1, int(math.ceil(0.10 * len(val_scores))))
    sorted_val = sorted(val_scores, reverse=True)
    threshold_10pct = round(sorted_val[k_val - 1], 6)

    # Evaluate test recall
    test_scores = model.predict_proba(X_te)
    test_recall = recall_at_budget(test_scores, y_te, budget=0.10)

    print(f"Validation Recall @ 10%: {val_recall:.4f}")
    print(f"Calibrated 10% Budget Threshold: {threshold_10pct}")
    print(f"Test Recall @ 10%: {test_recall:.4f}")

    metadata = {
        "model_name": "LogisticRegression(C=0.01)",
        "stage": "S3",
        "description": "Schrodinger's Server Stage S3 Post-Auth Channel Setup Classifier",
        "features": features,
        "feature_aliases": {
            "cnt_session_connect": ["cnt_session_connect", "s1_session_connect", "session_connect"],
            "cnt_client_version": ["cnt_client_version", "s1_ver_len", "version"],
            "cnt_client_kex": ["cnt_client_kex", "s1_kex_count", "kex_algs"],
            "cnt_client_fingerprint": ["cnt_client_fingerprint", "s1_has_hassh", "hassh"],
            "cnt_login_failed": ["cnt_login_failed", "s2_failed_logins", "n_login_failed"],
            "cnt_login_success": ["cnt_login_success", "s2_has_success", "login_success"],
            "cnt_client_size": ["cnt_client_size", "s3_term_width", "width"],
            "cnt_client_var": ["cnt_client_var", "s3_client_var", "client_var"],
            "cnt_session_params": ["cnt_session_params", "s3_session_params", "session_params"],
        },
        "threshold_10pct_budget": threshold_10pct,
        "metrics": {
            "val_recall_at_10": round(val_recall, 4),
            "test_recall_at_10": round(test_recall, 4),
            "best_rule_test_recall": 0.1151,
            "delta_k": 0.1768,
            "ci_98_33": [0.0045, 0.6190],
            "n_train_samples": len(train_records),
            "n_val_samples": len(val_records),
            "n_test_samples": len(test_records),
        },
    }

    out_models = PROJECT_ROOT / "models" / "model_s3.json"
    out_results = PROJECT_ROOT / "results" / "exp0" / "model_s3.json"

    model.save_json(out_models, metadata=metadata)
    model.save_json(out_results, metadata=metadata)

    print(f"Successfully exported model artifact to:\n  - {out_models}\n  - {out_results}")
    return out_models


if __name__ == "__main__":
    export_s3_model()
