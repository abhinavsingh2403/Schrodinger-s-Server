"""Natural Experiment Persona Effect Analysis (EVAL 5.3).

Analyzes observational session outcomes across the 160 Cowrie honeypot instances
in the public 50-day dataset (DATA.md D1, EVAL.md §5.3).
Computes session duration, command counts, login rates, and value rate variations.

SCIENTIFIC REPORTING MANDATE (EVAL.md §5.3):
All findings are reported as observational associations only with NO CAUSAL LANGUAGE.
Scanner targeting patterns and network topography confound instance assignment.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure mini project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EVAL_53_CAVEAT: str = (
    "SCIENTIFIC NOTICE: EVAL.md §5.3 mandates measuring the persona effect across the four Cowrie configurations "
    "using the configuration 'group' field. However, 'session_aggregation.jsonl.gz' does not contain 'group'. "
    "As established in DATA.md and SPIKES S3 Part 2, 'group' is only available in event-level logs (data_all.zip) "
    "or external descriptor mapping. Therefore, analyzing session_aggregation by honeypot_ip reflects observational "
    "variance across IP deployments, which is confounded by scanner targeting patterns, network topology, and IP probing biases. "
    "Findings are descriptive associations only with no causal language; no causal claims regarding honeypot configuration "
    "or persona can be drawn from this file."
)


def wilson_score_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> Tuple[float, float]:
    """Computes two-sided Wilson score confidence interval for a binomial proportion.

    Args:
        successes: Number of positive events (e.g., value=1).
        total: Total trials / sessions.
        confidence: Confidence level (default 0.95 corresponds to z=1.95996).

    Returns:
        (lower_bound, upper_bound) rounded to 6 decimal places.
    """
    if total <= 0:
        return (0.0, 0.0)

    # Standard normal quantile for two-sided interval
    # For 0.95 confidence, z ~= 1.95996398454
    z = 1.95996398454 if abs(confidence - 0.95) < 1e-4 else 1.96

    p_hat = float(successes) / float(total)
    z_sq = z * z
    denom = 1.0 + z_sq / total
    center = (p_hat + z_sq / (2.0 * total)) / denom
    margin = (z / denom) * math.sqrt((p_hat * (1.0 - p_hat) / total) + (z_sq / (4.0 * total * total)))

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return (round(lower, 6), round(upper, 6))


def analyze_honeypot_instances(
    records: List[Dict[str, Any]],
    n_cmd: int = 5,
) -> Dict[str, Dict[str, Any]]:
    """Aggregates sessions by honeypot instance, computing outcome associations.

    Args:
        records: List of session records with keys:
                 `honeypot_ip`, `cnt_command_input`, `cnt_file_download`,
                 `cnt_file_upload`, `cnt_direct_tcpip_request`, `cnt_login_success`, `duration`.
        n_cmd: Command input threshold for value=1 approximation.

    Returns:
        Dictionary mapping honeypot_ip to computed summary statistics.
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        hp = str(r.get("honeypot_ip", "unknown"))
        grouped.setdefault(hp, []).append(r)

    instance_stats: Dict[str, Dict[str, Any]] = {}

    for hp, sessions in grouped.items():
        n = len(sessions)
        if n == 0:
            continue

        val_1_count = 0
        login_count = 0
        cmd_total = 0
        dur_total = 0.0

        for s in sessions:
            cmds = int(s.get("cnt_command_input", 0) or 0)
            files = int(s.get("cnt_file_download", 0) or 0) + int(s.get("cnt_file_upload", 0) or 0)
            pivots = int(s.get("cnt_direct_tcpip_request", 0) or 0)
            login = int(s.get("cnt_login_success", 0) or 0) > 0
            dur = float(s.get("duration", 1.0) or 1.0)

            is_val_1 = (cmds >= n_cmd) or (files > 0) or (pivots > 0)
            if is_val_1:
                val_1_count += 1
            if login:
                login_count += 1
            cmd_total += cmds
            dur_total += dur

        val_rate = val_1_count / n
        ci_low, ci_high = wilson_score_interval(val_1_count, n, confidence=0.95)

        instance_stats[hp] = {
            "total_sessions": n,
            "value_1_count": val_1_count,
            "value_1_rate": round(val_rate, 6),
            "value_1_ci_95": [ci_low, ci_high],
            "login_count": login_count,
            "login_rate": round(login_count / n, 6),
            "mean_commands": round(cmd_total / n, 4),
            "mean_duration": round(dur_total / n, 2),
        }

    return instance_stats


def summarize_natural_experiment(
    instance_stats: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Computes cross-instance variance, quartile comparisons, and reports associations."""
    instances = list(instance_stats.values())
    n_instances = len(instances)

    if n_instances == 0:
        return {
            "status": "NATURAL_EXPERIMENT_NO_DATA",
            "caveat_disclaimer": EVAL_53_CAVEAT,
            "n_instances": 0,
        }

    # Descriptive statistics across instances
    val_rates = sorted([x["value_1_rate"] for x in instances])
    overall_mean_val = sum(val_rates) / n_instances
    min_val = min(val_rates)
    max_val = max(val_rates)
    p25_val = val_rates[int(n_instances * 0.25)]
    p50_val = val_rates[int(n_instances * 0.50)]
    p75_val = val_rates[int(n_instances * 0.75)]

    total_sessions_all = sum(x["total_sessions"] for x in instances)
    total_val_all = sum(x["value_1_count"] for x in instances)
    pooled_val_rate = total_val_all / max(1, total_sessions_all)
    pooled_ci = wilson_score_interval(total_val_all, total_sessions_all)

    return {
        "status": "EVAL_53_PERSONA_EFFECT_PENDING_EVENT_GROUP_DATA",
        "scientific_notice": (
            "EVAL 5.3 persona evaluation requires the 'group' configuration field, which is absent from "
            "session_aggregation.jsonl.gz. The data below documents empirical heterogeneity across the "
            "160 honeypot IP deployments (unstratified by configuration)."
        ),
        "caveat_disclaimer": EVAL_53_CAVEAT,
        "n_instances_evaluated": n_instances,
        "instance_variance_distribution": {
            "pooled_value_rate": round(pooled_val_rate, 6),
            "pooled_value_rate_95_ci": list(pooled_ci),
            "mean_instance_value_rate": round(overall_mean_val, 6),
            "p25_instance_value_rate": round(p25_val, 6),
            "median_instance_value_rate": round(p50_val, 6),
            "p75_instance_value_rate": round(p75_val, 6),
            "min_instance_value_rate": round(min_val, 6),
            "max_instance_value_rate": round(max_val, 6),
        },
        "instances": instance_stats,
    }


def run_natural_experiment_pipeline(
    data_path: Optional[str] = "data/session_aggregation.jsonl.gz",
    output_path: str = "results/natural_experiment.json",
    sample_limit: int = 100000,
    records: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Runs observational association analysis across 160 honeypot instances."""
    if records is None:
        import duckdb

        p = Path(data_path or "")
        if not p.exists():
            logger.warning("Dataset %s not found. Pipeline cannot run.", data_path)
            return

        logger.info("Querying %d sessions across instances via DuckDB...", sample_limit)
        con = duckdb.connect()
        query = f"""
            SELECT 
                honeypot_ip,
                cnt_command_input,
                cnt_file_download,
                cnt_file_upload,
                cnt_direct_tcpip_request,
                (cnt_login_success > 0) AS cnt_login_success,
                COALESCE(GREATEST(1.0, epoch(TRY_CAST(last_seen AS TIMESTAMP)) - epoch(TRY_CAST(first_seen AS TIMESTAMP))), 1.0) AS duration
            FROM read_ndjson_auto('{data_path}')
            LIMIT {sample_limit}
        """
        cur = con.execute(query)
        cols = [c[0] for c in cur.description]
        records = [dict(zip(cols, row)) for row in cur.fetchall()]

    instance_stats = analyze_honeypot_instances(records)
    summary = summarize_natural_experiment(instance_stats)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("Natural experiment association analysis saved to %s", output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Natural Experiment Persona Associations (EVAL 5.3)")
    parser.add_argument("--data", default="data/session_aggregation.jsonl.gz", help="Path to aggregation file")
    parser.add_argument("--out", default="results/natural_experiment.json", help="Output path")
    parser.add_argument("--limit", type=int, default=100000, help="Sample session limit")
    args = parser.parse_args()

    run_natural_experiment_pipeline(
        data_path=args.data,
        output_path=args.out,
        sample_limit=args.limit,
    )
