"""S3 Base Rates Computation Script using DuckDB.

Evaluates base rates of value=1 and feature distributions on the Cowrie
dataset session_aggregation.jsonl.gz per SPIKES S3, DATA.md, and EVAL.md §2.1.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import duckdb

try:
    from analysis.verify_download import compute_md5
except ModuleNotFoundError:
    from verify_download import compute_md5

SCHEMA_25_FIELDS: list[str] = [
    "session",
    "src_ip",
    "honeypot_ip",
    "first_seen",
    "last_seen",
    "total_events",
    "cnt_client_fingerprint",
    "cnt_client_kex",
    "cnt_client_size",
    "cnt_client_var",
    "cnt_client_version",
    "cnt_command_failed",
    "cnt_command_input",
    "cnt_command_success",
    "cnt_direct_tcpip_data",
    "cnt_direct_tcpip_request",
    "cnt_file_download",
    "cnt_file_download_failed",
    "cnt_file_upload",
    "cnt_log_closed",
    "cnt_login_failed",
    "cnt_login_success",
    "cnt_session_closed",
    "cnt_session_connect",
    "cnt_session_params",
]


def get_git_commit() -> str:
    """Retrieve current Git HEAD commit hash if available."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return "UNKNOWN"


def verify_schema(con: duckdb.DuckDBPyConnection, view_name: str) -> None:
    """Check that all 25 field names listed in DATA.md exist exactly."""
    described = con.execute(f"DESCRIBE {view_name}").fetchall()
    actual_columns = {row[0] for row in described}
    expected_columns = set(SCHEMA_25_FIELDS)

    missing = expected_columns - actual_columns
    extra = actual_columns - expected_columns

    if missing:
        print(f"SCHEMA CHECK FAILED: Missing fields ({len(missing)}): {sorted(missing)}", file=sys.stderr)
        if extra:
            print(f"Extra fields ({len(extra)}): {sorted(extra)}", file=sys.stderr)
        raise ValueError(f"Missing required fields: {sorted(missing)}")

    print("SCHEMA CHECK PASSED: All 25 fields exist exactly.")
    if extra:
        print(f"Extra fields present ({len(extra)}): {sorted(extra)}")


def compute_base_rates(
    con: duckdb.DuckDBPyConnection,
    view_name: str,
    n_cmd: int = 5,
) -> dict:
    """Compute base rates, distribution statistics, and per-day metrics."""
    # Value=1 definition per SPIKES S3 step 3:
    # cnt_command_input >= n_cmd OR (cnt_file_upload + cnt_file_download) > 0 OR cnt_direct_tcpip_request > 0
    val_expr = (
        f"(cnt_command_input >= {n_cmd} "
        f"OR (cnt_file_upload + cnt_file_download) > 0 "
        f"OR cnt_direct_tcpip_request > 0)"
    )

    query_overall = f"""
    SELECT
        COUNT(*) AS total_sessions,
        COUNT(*) FILTER (WHERE cnt_login_success > 0) AS sessions_with_login_success,
        COUNT(*) FILTER (WHERE cnt_command_input > 0) AS sessions_with_command_input,
        COUNT(*) FILTER (WHERE cnt_command_input = 0) AS cmd_dist_0,
        COUNT(*) FILTER (WHERE cnt_command_input >= 1 AND cnt_command_input <= 4) AS cmd_dist_1_to_4,
        COUNT(*) FILTER (WHERE cnt_command_input >= 5 AND cnt_command_input <= 9) AS cmd_dist_5_to_9,
        COUNT(*) FILTER (WHERE cnt_command_input >= 10) AS cmd_dist_10_plus,
        quantile_cont(cnt_command_input, 0.50) AS cmd_p50,
        quantile_cont(cnt_command_input, 0.90) AS cmd_p90,
        quantile_cont(cnt_command_input, 0.99) AS cmd_p99,
        COUNT(*) FILTER (WHERE (cnt_file_upload + cnt_file_download) > 0) AS sessions_with_file_transfer,
        COUNT(*) FILTER (WHERE cnt_direct_tcpip_request > 0) AS sessions_with_direct_tcpip,
        COUNT(*) FILTER (WHERE {val_expr}) AS sessions_with_value_1
    FROM {view_name}
    """

    res = con.execute(query_overall).fetchone()
    if res is None or res[0] == 0:
        raise ValueError("Dataset contains 0 sessions.")

    total = int(res[0])
    login_succ = int(res[1])
    cmd_inp = int(res[2])
    cmd_0 = int(res[3])
    cmd_1_4 = int(res[4])
    cmd_5_9 = int(res[5])
    cmd_10_plus = int(res[6])
    cmd_p50 = float(res[7])
    cmd_p90 = float(res[8])
    cmd_p99 = float(res[9])
    file_tx = int(res[10])
    direct_tcp = int(res[11])
    val_1 = int(res[12])

    # Per-day aggregation using UTC day from first_seen
    # DuckDB read_json_auto infers first_seen as TIMESTAMP or VARCHAR.
    # strftime(TRY_CAST(first_seen AS TIMESTAMP), '%Y-%m-%d') formats to YYYY-MM-DD.
    day_expr = "COALESCE(strftime(TRY_CAST(first_seen AS TIMESTAMP), '%Y-%m-%d'), 'UNKNOWN')"

    query_daily = f"""
    SELECT
        {day_expr} AS day_utc,
        COUNT(*) AS daily_total,
        COUNT(*) FILTER (WHERE {val_expr}) AS daily_value_1,
        COUNT(*) FILTER (WHERE cnt_login_success > 0) AS daily_login_success,
        COUNT(*) FILTER (WHERE cnt_command_input > 0) AS daily_command_input
    FROM {view_name}
    GROUP BY day_utc
    ORDER BY day_utc
    """

    daily_rows = con.execute(query_daily).fetchall()
    by_day = {}
    sum_daily_total = 0
    sum_daily_val1 = 0

    for row in daily_rows:
        d_str = str(row[0])
        d_tot = int(row[1])
        d_v1 = int(row[2])
        d_log = int(row[3])
        d_cmd = int(row[4])

        sum_daily_total += d_tot
        sum_daily_val1 += d_v1

        by_day[d_str] = {
            "total_sessions": d_tot,
            "value_1_count": d_v1,
            "value_1_base_rate": round(d_v1 / d_tot, 6) if d_tot > 0 else 0.0,
            "sessions_with_login_success": d_log,
            "share_login_success": round(d_log / d_tot, 6) if d_tot > 0 else 0.0,
            "sessions_with_command_input": d_cmd,
            "share_command_input": round(d_cmd / d_tot, 6) if d_tot > 0 else 0.0,
        }

    # Integrity assertion: sum of per-day sessions must equal total sessions
    if sum_daily_total != total:
        raise ValueError(
            f"Per-day sum mismatch: daily sum ({sum_daily_total}) != total ({total})"
        )
    if sum_daily_val1 != val_1:
        raise ValueError(
            f"Per-day value=1 mismatch: daily sum ({sum_daily_val1}) != total value=1 ({val_1})"
        )

    return {
        "metadata": {
            "n_cmd_threshold": n_cmd,
            "approximation_note": (
                "cnt_command_input counts input events, not distinct commands. "
                "Therefore, this aggregate calculation is an approximation of value=1."
            ),
        },
        "overall": {
            "total_sessions": total,
            "sessions_with_login_success": login_succ,
            "share_login_success": round(login_succ / total, 6),
            "sessions_with_command_input": cmd_inp,
            "share_command_input": round(cmd_inp / total, 6),
            "command_input_distribution": {
                "counts": {
                    "0": cmd_0,
                    "1_to_4": cmd_1_4,
                    "5_to_9": cmd_5_9,
                    "10_plus": cmd_10_plus,
                },
                "shares": {
                    "0": round(cmd_0 / total, 6),
                    "1_to_4": round(cmd_1_4 / total, 6),
                    "5_to_9": round(cmd_5_9 / total, 6),
                    "10_plus": round(cmd_10_plus / total, 6),
                },
                "quantiles": {
                    "p50": cmd_p50,
                    "p90": cmd_p90,
                    "p99": cmd_p99,
                },
            },
            "file_transfer": {
                "count": file_tx,
                "share": round(file_tx / total, 6),
            },
            "direct_tcpip_request": {
                "count": direct_tcp,
                "share": round(direct_tcp / total, 6),
            },
            "value_1_approximation": {
                "count": val_1,
                "base_rate": round(val_1 / total, 6),
            },
        },
        "by_day": by_day,
    }


def run_pipeline(
    data_path: Path | str,
    n_cmd: int = 5,
    output_path: Path | str = "results/base_rates.json",
    manifest_path: Path | str = "results/MANIFEST.json",
) -> dict:
    """Run schema verification and base rates pipeline."""
    path = Path(data_path)
    if not path.is_file():
        raise FileNotFoundError(f"Data file does not exist: {path}")

    print(f"Connecting to DuckDB and loading {path}...")
    con = duckdb.connect(database=":memory:")

    # Create view over jsonl / jsonl.gz
    view_name = "sessions_data"
    con.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_json_auto('{path.as_posix()}')")

    verify_schema(con, view_name)

    print(f"Computing base rates (N_CMD={n_cmd})...")
    results = compute_base_rates(con, view_name, n_cmd=n_cmd)

    # Print note per requirement 4
    print("\n" + "=" * 70)
    print("NOTE: cnt_command_input counts input events, not distinct commands,")
    print("so this is only an approximation of value=1.")
    print("=" * 70 + "\n")

    # Write results/base_rates.json
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with out_p.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved base rates to {out_p}")

    # Compute MD5 for manifest
    print(f"Computing MD5 checksum of {path}...")
    file_md5 = compute_md5(path)

    manifest = {
        "file_path": str(path.as_posix()),
        "file_md5": file_md5,
        "duckdb_version": duckdb.__version__,
        "git_commit": get_git_commit(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_cmd_threshold": n_cmd,
    }

    man_p = Path(manifest_path)
    man_p.parent.mkdir(parents=True, exist_ok=True)
    with man_p.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Saved manifest to {man_p}")

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute base rates on Cowrie session aggregation dataset."
    )
    parser.add_argument(
        "--data-path",
        default="data/session_aggregation.jsonl.gz",
        help="Path to session_aggregation.jsonl.gz or jsonl file (default: data/session_aggregation.jsonl.gz)",
    )
    parser.add_argument(
        "--n-cmd",
        type=int,
        default=5,
        help="Command threshold for value=1 approximation (default: 5)",
    )
    parser.add_argument(
        "--output",
        default="results/base_rates.json",
        help="Path for base rates JSON output (default: results/base_rates.json)",
    )
    parser.add_argument(
        "--manifest",
        default="results/MANIFEST.json",
        help="Path for manifest JSON output (default: results/MANIFEST.json)",
    )
    args = parser.parse_args(argv)

    try:
        run_pipeline(
            data_path=args.data_path,
            n_cmd=args.n_cmd,
            output_path=args.output,
            manifest_path=args.manifest,
        )
        return 0
    except Exception as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
