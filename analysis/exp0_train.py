"""
exp0_train.py: Experiment 0 model training, validation tuning, and evaluation harness.

Designed for modular execution:
1. Feature extraction & dataset splitting via DuckDB
2. Baseline rule evaluation (R0 to R7)
3. Model fitting (Logistic Regression & HistGradientBoosting) using pre-declared grid (grid.json)
4. Recall at 10% budget evaluation on validation & test sets
5. Decision rule evaluation: PASS-ML / PASS-LATE-ONLY / FAIL (EXPERIMENT0.md Section 12)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import duckdb

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.exp0_rules import (
    recall_at_budget,
    score_r0_random,
    score_r1_login_success,
    score_r6_failed_logins,
)


def extract_split_features(
    data_path: Path,
    splits_path: Path,
    output_dir: Path,
    n_cmd: int = 5,
) -> dict[str, int]:
    """
    Extracts features for train, val, and test days from session_aggregation.jsonl.gz using DuckDB.
    Enforces disjoint source IP grouping.
    """
    with open(splits_path, "r", encoding="utf-8") as f:
        splits_cfg = json.load(f)["splits"]

    train_days = splits_cfg["train"]
    val_days = splits_cfg["validation"]
    test_days = splits_cfg["test"]

    output_dir.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect()

    val_expr = (
        f"(cnt_command_input >= {n_cmd} "
        f"OR (cnt_file_upload + cnt_file_download) > 0 "
        f"OR cnt_direct_tcpip_request > 0)"
    )

    day_expr = "COALESCE(strftime(TRY_CAST(first_seen AS TIMESTAMP), '%Y-%m-%d'), 'UNKNOWN')"

    print("Querying dataset with DuckDB to create disjoint IP temporal splits...")

    # Load view
    conn.execute(
        f"""
        CREATE VIEW sessions AS
        SELECT
            session,
            src_ip,
            {day_expr} AS day,
            cnt_login,
            cnt_login_success,
            cnt_login_failed,
            cnt_command_input,
            cnt_command_failed,
            cnt_file_download,
            cnt_file_upload,
            cnt_direct_tcpip_request,
            longest_command_length,
            duration,
            CASE WHEN {val_expr} THEN 1 ELSE 0 END AS v_full
        FROM read_ndjson_objects('{data_path.as_posix()}')
        """
    )

    # Export splits ensuring disjoint IP allocation (earliest period wins)
    # 1. Train
    train_days_sql = ", ".join(f"'{d}'" for d in train_days)
    conn.execute(
        f"""
        CREATE TABLE train_set AS
        SELECT * FROM sessions
        WHERE day IN ({train_days_sql})
        """
    )

    # 2. Validation (excluding IPs in train)
    val_days_sql = ", ".join(f"'{d}'" for d in val_days)
    conn.execute(
        f"""
        CREATE TABLE val_set AS
        SELECT * FROM sessions
        WHERE day IN ({val_days_sql})
          AND src_ip NOT IN (SELECT DISTINCT src_ip FROM train_set)
        """
    )

    # 3. Test (excluding IPs in train and val)
    test_days_sql = ", ".join(f"'{d}'" for d in test_days)
    conn.execute(
        f"""
        CREATE TABLE test_set AS
        SELECT * FROM sessions
        WHERE day IN ({test_days_sql})
          AND src_ip NOT IN (SELECT DISTINCT src_ip FROM train_set)
          AND src_ip NOT IN (SELECT DISTINCT src_ip FROM val_set)
        """
    )

    counts = {
        "train_rows": conn.execute("SELECT COUNT(*) FROM train_set").fetchone()[0],
        "val_rows": conn.execute("SELECT COUNT(*) FROM val_set").fetchone()[0],
        "test_rows": conn.execute("SELECT COUNT(*) FROM test_set").fetchone()[0],
    }

    # Save to parquet
    conn.execute(f"COPY train_set TO '{(output_dir / 'train.parquet').as_posix()}' (FORMAT PARQUET)")
    conn.execute(f"COPY val_set TO '{(output_dir / 'val.parquet').as_posix()}' (FORMAT PARQUET)")
    conn.execute(f"COPY test_set TO '{(output_dir / 'test.parquet').as_posix()}' (FORMAT PARQUET)")

    print(f"Extraction complete: Train={counts['train_rows']:,}, Val={counts['val_rows']:,}, Test={counts['test_rows']:,}")
    return counts


def evaluate_rules_on_table(
    table_path: Path,
    budget: float = 0.10,
) -> dict[str, float]:
    """Evaluates pre-declared rules on a parquet table at the given budget."""
    conn = duckdb.connect()
    df = conn.execute(
        f"SELECT cnt_login_success, cnt_login_failed, v_full FROM '{table_path.as_posix()}'"
    ).fetchdf()

    labels = df["v_full"].tolist()
    n = len(labels)

    # R0 Random
    r0_scores = score_r0_random(n, seed=42)
    rec_r0 = recall_at_budget(r0_scores, labels, budget=budget)

    # R1 Login success
    r1_scores = score_r1_login_success(df["cnt_login_success"].tolist())
    rec_r1 = recall_at_budget(r1_scores, labels, budget=budget)

    # R6 Failed logins
    r6_scores = score_r6_failed_logins(df["cnt_login_failed"].tolist(), sign=1)
    rec_r6 = recall_at_budget(r6_scores, labels, budget=budget)

    return {
        "R0_random": rec_r0,
        "R1_login_success": rec_r1,
        "R6_failed_logins": rec_r6,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 0 Training & Evaluation Runner")
    parser.add_argument("--data", type=Path, default=Path("data/session_aggregation.jsonl.gz"))
    parser.add_argument("--splits", type=Path, default=Path("results/exp0/splits.json"))
    parser.add_argument("--grid", type=Path, default=Path("results/exp0/grid.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/exp0"))
    parser.add_argument("--extract-only", action="store_true", help="Only extract datasets without training")
    args = parser.parse_args()

    if not args.data.is_file():
        raise FileNotFoundError(f"Missing dataset at {args.data}")

    counts = extract_split_features(
        data_path=args.data,
        splits_path=args.splits,
        output_dir=args.output_dir,
    )

    val_rules = evaluate_rules_on_table(args.output_dir / "val.parquet", budget=0.10)
    test_rules = evaluate_rules_on_table(args.output_dir / "test.parquet", budget=0.10)

    print("\n--- Baseline Rule Recall @ 10% Budget ---")
    print(f"Validation: {val_rules}")
    print(f"Test      : {test_rules}")

    best_val_rule = max(val_rules.items(), key=lambda x: x[1])
    print(f"\nBest Simple Rule on Validation: {best_val_rule[0]} (Recall = {best_val_rule[1]:.4f})")
    print(f"Corresponding Test Recall       : {test_rules[best_val_rule[0]]:.4f}")

    # Save rule evaluation summary
    rules_summary = {
        "counts": counts,
        "validation_recall_10pct": val_rules,
        "test_recall_10pct": test_rules,
        "best_validation_rule": best_val_rule[0],
    }
    with open(args.output_dir / "rules_summary.json", "w", encoding="utf-8") as f:
        json.dump(rules_summary, f, indent=2)

    print(f"\nSaved rules summary to: {args.output_dir / 'rules_summary.json'}")
    print("\nParquet datasets are ready for ML training in results/exp0/ (train.parquet, val.parquet, test.parquet).")


if __name__ == "__main__":
    main()
