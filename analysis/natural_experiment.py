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
    "Findings are reported strictly as empirical associations with no causal language, "
    "per pre-registered EVAL.md Section 5.3. Configuration assignment across instances and "
    "regions may be confounded by scanner targeting patterns, Autonomous System topography, "
    "and IP space probing biases. Causal validation is reserved for randomized live trials."
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

    # Sort instances by observed value rate
    sorted_by_val = sorted(instances, key=lambda x: x["value_1_rate"])

    # Split into observed lower and upper quartiles
    q_size = max(1, n_instances // 4)
    low_quartile = sorted_by_val[:q_size]
    high_quartile = sorted_by_val[-q_size:]

    def agg_quartile(inst_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        tot_s = sum(x.get("total_sessions", 0) for x in inst_list)
        tot_v = sum(x.get("value_1_count", 0) for x in inst_list)
        tot_l = sum(x.get("login_count", int(x.get("login_rate", 0.0) * x.get("total_sessions", 0))) for x in inst_list)
        avg_cmd = sum(x.get("mean_commands", 0.0) * x.get("total_sessions", 0) for x in inst_list) / max(1, tot_s)
        avg_dur = sum(x.get("mean_duration", 0.0) * x.get("total_sessions", 0) for x in inst_list) / max(1, tot_s)
        v_rate = tot_v / max(1, tot_s)
        ci_low, ci_high = wilson_score_interval(tot_v, tot_s)
        return {
            "instances_in_group": len(inst_list),
            "total_sessions": tot_s,
            "value_1_rate": round(v_rate, 6),
            "value_1_ci_95": [ci_low, ci_high],
            "login_rate": round(tot_l / max(1, tot_s), 6),
            "mean_commands_per_session": round(avg_cmd, 4),
            "mean_duration_seconds": round(avg_dur, 2),
        }

    q1_summary = agg_quartile(low_quartile)
    q4_summary = agg_quartile(high_quartile)

    val_rates = [x["value_1_rate"] for x in instances]
    overall_mean_val = sum(val_rates) / n_instances
    min_val = min(val_rates)
    max_val = max(val_rates)

    return {
        "status": "NATURAL_EXPERIMENT_COMPLETE",
        "caveat_disclaimer": EVAL_53_CAVEAT,
        "n_instances_evaluated": n_instances,
        "aggregate_association": {
            "mean_instance_value_rate": round(overall_mean_val, 6),
            "min_instance_value_rate": round(min_val, 6),
            "max_instance_value_rate": round(max_val, 6),
            "lower_interaction_quartile": q1_summary,
            "higher_interaction_quartile": q4_summary,
            "observed_value_rate_ratio_q4_to_q1": round(
                q4_summary["value_1_rate"] / max(1e-6, q1_summary["value_1_rate"]), 2
            ),
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
