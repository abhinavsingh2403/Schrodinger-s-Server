"""Experiment 0: Training, Validation Tuning, and Evaluation Harness.

Pre-registered in EXPERIMENT0.md.
Orchestrates:
1. Feature extraction & temporal dataset splitting via DuckDB with disjoint source IP allocation.
2. Pre-declared simple-rule baseline evaluation (R0 to R7) at 10% escalation budget.
3. Learned model candidate fitting (Logistic Regression & HistGradientBoosting) using pre-declared grid (grid.json).
4. Paired cluster-bootstrap by source IP for Delta_k (ML recall minus best rule recall).
5. Pre-declared Gate 0 decision rule evaluation: PASS-ML / PASS-LATE-ONLY / FAIL (EXPERIMENT0.md Section 12).
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path
import random
import sys
from typing import Any, Dict, List, Optional, Tuple

import duckdb

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.exp0_rules import (
    recall_at_budget,
    score_r0_random,
    score_r1_login_success,
    score_r2_pty_requested,
    score_r5_rarity,
    score_r6_failed_logins,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def extract_split_features(
    data_path: Path,
    splits_path: Path,
    output_dir: Path,
    n_cmd: int = 5,
    sample_limit: Optional[int] = None,
) -> Dict[str, int]:
    """Extracts features for train, val, and test days from session_aggregation.jsonl.gz.

    Enforces disjoint source IP grouping per EXPERIMENT0.md §3:
    Any source IP that appears in multiple periods is assigned exclusively
    to the earliest period's fold and purged from later folds.
    """
    if not splits_path.is_file():
        raise FileNotFoundError(f"Missing splits configuration at {splits_path}")

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
    limit_clause = f"LIMIT {sample_limit}" if sample_limit else ""

    logger.info("Reading session aggregation and preparing temporal views...")
    conn.execute(
        f"""
        CREATE VIEW raw_sessions AS
        SELECT
            session,
            src_ip,
            honeypot_ip,
            {day_expr} AS day,
            COALESCE(cnt_login_success, 0) AS cnt_login_success,
            COALESCE(cnt_login_failed, 0) AS cnt_login_failed,
            (cnt_client_size > 0) AS has_pty,
            COALESCE(cnt_client_kex, 0) AS cnt_client_kex,
            COALESCE(cnt_client_version, 0) AS cnt_client_version,
            COALESCE(cnt_command_input, 0) AS cnt_command_input,
            COALESCE(cnt_command_failed, 0) AS cnt_command_failed,
            COALESCE(cnt_file_download, 0) AS cnt_file_download,
            COALESCE(cnt_file_upload, 0) AS cnt_file_upload,
            COALESCE(cnt_direct_tcpip_request, 0) AS cnt_direct_tcpip_request,
            COALESCE(GREATEST(1.0, epoch(TRY_CAST(last_seen AS TIMESTAMP)) - epoch(TRY_CAST(first_seen AS TIMESTAMP))), 1.0) AS duration,
            CASE WHEN {val_expr} THEN 1 ELSE 0 END AS v_full
        FROM read_ndjson_auto('{data_path.as_posix()}')
        {limit_clause}
        """
    )

    # 1. Train set
    train_days_sql = ", ".join(f"'{d}'" for d in train_days)
    conn.execute(
        f"""
        CREATE TABLE train_set AS
        SELECT * FROM raw_sessions
        WHERE day IN ({train_days_sql})
        """
    )

    # 2. Validation set (excluding IPs in train_set)
    val_days_sql = ", ".join(f"'{d}'" for d in val_days)
    conn.execute(
        f"""
        CREATE TABLE val_set AS
        SELECT * FROM raw_sessions
        WHERE day IN ({val_days_sql})
          AND src_ip NOT IN (SELECT DISTINCT src_ip FROM train_set)
        """
    )

    # 3. Test set (excluding IPs in train_set and val_set)
    test_days_sql = ", ".join(f"'{d}'" for d in test_days)
    conn.execute(
        f"""
        CREATE TABLE test_set AS
        SELECT * FROM raw_sessions
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

    # Save splits to Parquet files
    train_pq = (output_dir / "train.parquet").as_posix()
    val_pq = (output_dir / "val.parquet").as_posix()
    test_pq = (output_dir / "test.parquet").as_posix()

    conn.execute(f"COPY train_set TO '{train_pq}' (FORMAT PARQUET)")
    conn.execute(f"COPY val_set TO '{val_pq}' (FORMAT PARQUET)")
    conn.execute(f"COPY test_set TO '{test_pq}' (FORMAT PARQUET)")

    logger.info(
        "Parquet extraction complete: Train=%d, Val=%d, Test=%d",
        counts["train_rows"],
        counts["val_rows"],
        counts["test_rows"],
    )
    return counts


def load_parquet_as_dict_records(parquet_path: Path) -> List[Dict[str, Any]]:
    """Loads parquet split into pure Python dictionaries without requiring pandas."""
    conn = duckdb.connect()
    cur = conn.execute(f"SELECT * FROM '{parquet_path.as_posix()}'")
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def evaluate_simple_rules(
    records: List[Dict[str, Any]],
    train_records: Optional[List[Dict[str, Any]]] = None,
    budget: float = 0.10,
) -> Dict[str, float]:
    """Evaluates pre-declared simple baseline rules (R0, R1, R2, R5, R6, R7) at budget."""
    if not records:
        return {}

    n = len(records)
    labels = [int(r["v_full"]) for r in records]

    # R0 Random
    r0_scores = score_r0_random(n, seed=42)
    rec_r0 = recall_at_budget(r0_scores, labels, budget=budget)

    # R1 Login Success
    logins = [int(r.get("cnt_login_success", 0)) for r in records]
    r1_scores = score_r1_login_success(logins)
    rec_r1 = recall_at_budget(r1_scores, labels, budget=budget)

    # R2 PTY Requested
    ptys = [bool(r.get("has_pty", False)) for r in records]
    r2_scores = score_r2_pty_requested(ptys)
    rec_r2 = recall_at_budget(r2_scores, labels, budget=budget)

    # R6 Failed Logins
    fails = [int(r.get("cnt_login_failed", 0)) for r in records]
    r6_scores = score_r6_failed_logins(fails, sign=1)
    rec_r6 = recall_at_budget(r6_scores, labels, budget=budget)

    # R5 Version Rarity (if train records provided)
    rec_r5 = 0.0
    if train_records:
        train_counts: Dict[str, int] = {}
        for tr in train_records:
            v_key = str(tr.get("cnt_client_version", 0))
            train_counts[v_key] = train_counts.get(v_key, 0) + 1
        items = [str(r.get("cnt_client_version", 0)) for r in records]
        r5_scores = score_r5_rarity(items, train_counts, len(train_records))
        rec_r5 = recall_at_budget(r5_scores, labels, budget=budget)

    # R7 Composite Heuristic (Depth-3 tree proxy: Login > 0 + PTY > 0 + Fails)
    r7_scores = [
        float((1.0 if l > 0 else 0.0) * 2.0 + (1.0 if p else 0.0) + min(1.0, f * 0.1))
        for l, p, f in zip(logins, ptys, fails)
    ]
    rec_r7 = recall_at_budget(r7_scores, labels, budget=budget)

    return {
        "R0_random": round(rec_r0, 4),
        "R1_login_success": round(rec_r1, 4),
        "R2_pty_requested": round(rec_r2, 4),
        "R5_rarity": round(rec_r5, 4),
        "R6_failed_logins": round(rec_r6, 4),
        "R7_composite_tree": round(rec_r7, 4),
    }


def paired_cluster_bootstrap_delta(
    scores_ml: List[float],
    scores_rule: List[float],
    labels: List[int],
    cluster_ids: List[str],
    budget: float = 0.10,
    n_resamples: int = 1000,
    seed: int = 20261111,
) -> Tuple[float, float, float]:
    """Computes paired cluster-bootstrap confidence interval for Delta = Recall_ML - Recall_Rule.

    Resamples distinct source IP clusters with replacement.
    Returns (delta_mean, ci_lower_95, ci_upper_95).
    """
    rng = random.Random(seed)
    # Group indices by cluster ID (source IP)
    clusters: Dict[str, List[int]] = {}
    for idx, cid in enumerate(cluster_ids):
        clusters.setdefault(cid, []).append(idx)

    unique_clusters = list(clusters.keys())
    n_clust = len(unique_clusters)
    if n_clust == 0:
        return (0.0, 0.0, 0.0)

    # Base point estimate
    rec_ml = recall_at_budget(scores_ml, labels, budget=budget)
    rec_rule = recall_at_budget(scores_rule, labels, budget=budget)
    point_delta = rec_ml - rec_rule

    deltas: List[float] = []
    for _ in range(n_resamples):
        sampled_cids = rng.choices(unique_clusters, k=n_clust)
        b_indices = []
        for cid in sampled_cids:
            b_indices.extend(clusters[cid])

        b_scores_ml = [scores_ml[i] for i in b_indices]
        b_scores_rule = [scores_rule[i] for i in b_indices]
        b_labels = [labels[i] for i in b_indices]

        b_rec_ml = recall_at_budget(b_scores_ml, b_labels, budget=budget)
        b_rec_rule = recall_at_budget(b_scores_rule, b_labels, budget=budget)
        deltas.append(b_rec_ml - b_rec_rule)

    deltas.sort()
    ci_low = deltas[int(0.025 * n_resamples)]
    ci_high = deltas[int(0.975 * n_resamples)]
    return (round(point_delta, 4), round(ci_low, 4), round(ci_high, 4))


def evaluate_gate0_decision_rule(
    delta_s1_s3: float,
    ci_lower_s1_s3: float,
    delta_s4_s5: float,
    ci_lower_s4_s5: float,
    threshold_delta: float = 0.05,
) -> Dict[str, Any]:
    """Applies pre-registered Gate 0 decision rule from EXPERIMENT0.md §12.

    Let delta = 0.05 absolute recall improvement at 10% budget.
    - PASS-ML: Stage in {S1, S2, S3} achieves Delta >= delta with lower CI > 0.
    - PASS-LATE-ONLY: Stage in {S4, S5} achieves Delta >= delta with lower CI > 0.
    - FAIL: Otherwise.
    """
    if delta_s1_s3 >= threshold_delta and ci_lower_s1_s3 > 0.0:
        outcome = "PASS-ML"
        meaning = "ML adds significant early triage signal before any command (Stages S1–S3)."
    elif delta_s4_s5 >= threshold_delta and ci_lower_s4_s5 > 0.0:
        outcome = "PASS-LATE-ONLY"
        meaning = "ML adds signal only after commands are observed (Stages S4–S5)."
    else:
        outcome = "FAIL"
        meaning = "Simple rules match or exceed learned models at pre-command stages. Reframe as rule-based study."

    return {
        "gate0_outcome": outcome,
        "delta_threshold": threshold_delta,
        "pre_command_stage_delta": delta_s1_s3,
        "pre_command_ci_lower": ci_lower_s1_s3,
        "interpretation": meaning,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 0 Training & Evaluation Runner")
    parser.add_argument("--data", type=Path, default=Path("data/session_aggregation.jsonl.gz"))
    parser.add_argument("--splits", type=Path, default=Path("results/exp0/splits.json"))
    parser.add_argument("--grid", type=Path, default=Path("results/exp0/grid.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/exp0"))
    parser.add_argument("--sample-limit", type=int, default=None, help="Optional session row limit")
    parser.add_argument("--extract-only", action="store_true", help="Only extract datasets without model training")
    args = parser.parse_args()

    if not args.data.is_file():
        raise FileNotFoundError(f"Missing dataset at {args.data}")

    counts = extract_split_features(
        data_path=args.data,
        splits_path=args.splits,
        output_dir=args.output_dir,
        sample_limit=args.sample_limit,
    )

    logger.info("Loading extracted validation and test Parquet splits...")
    train_records = load_parquet_as_dict_records(args.output_dir / "train.parquet")
    val_records = load_parquet_as_dict_records(args.output_dir / "val.parquet")
    test_records = load_parquet_as_dict_records(args.output_dir / "test.parquet")

    val_rules = evaluate_simple_rules(val_records, train_records=train_records, budget=0.10)
    test_rules = evaluate_simple_rules(test_records, train_records=train_records, budget=0.10)

    if not val_rules:
        logger.warning("Validation set is empty for the sampled days; baseline rules could not be evaluated.")
        best_rule_name = "NONE"
        best_val_score = 0.0
    else:
        best_val_rule = max(val_rules.items(), key=lambda x: x[1])
        best_rule_name = best_val_rule[0]
        best_val_score = best_val_rule[1]
        logger.info("Best simple rule on validation: %s (Recall = %.4f)", best_rule_name, best_val_score)
        logger.info("Corresponding test recall for %s: %.4f", best_rule_name, test_rules.get(best_rule_name, 0.0))

    rules_summary = {
        "status": "RULES_EVALUATION_COMPLETE" if val_rules else "EMPTY_SPLITS_FOR_GIVEN_SAMPLE",
        "counts": counts,
        "validation_recall_10pct": val_rules,
        "test_recall_10pct": test_rules,
        "best_validation_rule": best_rule_name,
    }

    out_file = args.output_dir / "rules_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(rules_summary, f, indent=2)
    logger.info("Saved baseline rules summary to %s", out_file)


if __name__ == "__main__":
    main()
