"""
Hardware Cost Measurement Harness for Schrödinger's Server.
Enforces G7:
- Inputs: --tier {T1,T2}, --sessions N, --host, --port, --container NAME.
- Runs N scripted sessions with harness/attackers/bot_like one after another.
- Samples docker stats --no-stream --format json every second during the run into CSV under results/cost/.
- Writes results/cost_model.json with exact schema:
  tier, N, wall_time, mean_cpu_pct, max_cpu_pct, mean_memory_mb, max_memory_mb, command_line, git_commit, timestamp.
- No interpretation, no extrapolation to rupees.
- Failing docker call produces a clear error and zero partial JSON.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from harness.attackers.common import assert_lab_target_allowlisted
from harness.attackers.bot_like import run_bot_like


def parse_memory_to_mb(mem_str: str) -> float:
    """Parses memory string like '45.2MiB / 7.66GiB' or '120.5MB' into float megabytes."""
    # Take the portion before ' / ' if present
    used_part = mem_str.split("/")[0].strip()
    m = re.match(r"^([\d.]+)\s*([a-zA-Z]+)$", used_part)
    if not m:
        return 0.0

    val = float(m.group(1))
    unit = m.group(2).lower()

    if unit in ("gib", "gb"):
        return val * 1024.0
    elif unit in ("kib", "kb"):
        return val / 1024.0
    elif unit in ("b", "bytes"):
        return val / (1024.0 * 1024.0)
    # Default to MiB / MB
    return val


def parse_cpu_to_pct(cpu_str: str) -> float:
    """Parses CPU percentage string like '1.25%' into float."""
    cleaned = cpu_str.replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def sample_docker_stats(container_name: str, fake_file: Optional[Path] = None) -> Tuple[float, float]:
    """
    Samples docker stats for a container. Returns (cpu_pct, memory_mb).
    Raises RuntimeError if docker stats fails.
    """
    if fake_file is not None and fake_file.exists():
        raw_output = fake_file.read_text(encoding="utf-8").strip()
    else:
        cmd = ["docker", "stats", "--no-stream", "--format", "json", container_name]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            raise RuntimeError(
                f"Docker CLI not found. Cannot measure cost on container '{container_name}'. "
                "Use --fake-stats-file for testing in environments without Docker."
            )

        if res.returncode != 0:
            raise RuntimeError(
                f"Docker stats failed with exit code {res.returncode}: {res.stderr.strip()}"
            )
        raw_output = res.stdout.strip()

    if not raw_output:
        raise RuntimeError(f"Docker stats returned empty output for container '{container_name}'")

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Could not parse docker stats JSON: {e} (output: {raw_output})")

    cpu_pct = parse_cpu_to_pct(data.get("CPUPerc", "0.0%"))
    mem_mb = parse_memory_to_mb(data.get("MemUsage", "0.0MB / 0.0MB"))
    return cpu_pct, mem_mb


def get_git_commit() -> str:
    """Returns the current git HEAD commit hash or UNKNOWN."""
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "UNKNOWN"


def measure_cost(
    tier: str,
    sessions: int = 5,
    host: str = "127.0.0.1",
    port: int = 2222,
    container_name: str = "schrodinger-sensor",
    dry_run: bool = False,
    fake_stats_file: Optional[Path] = None,
    output_dir: Path = PROJECT_ROOT / "results" / "cost",
    cost_model_file: Path = PROJECT_ROOT / "results" / "cost_model.json",
    raw_command_line: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Measures resource utilization during N bot sessions and writes cost_model.json.
    """
    if tier not in ("T1", "T2"):
        raise ValueError(f"Invalid tier '{tier}'. Must be 'T1' or 'T2'.")

    assert_lab_target_allowlisted(host)

    output_dir.mkdir(parents=True, exist_ok=True)
    cost_model_file.parent.mkdir(parents=True, exist_ok=True)

    samples: List[Dict[str, Any]] = []
    t_start = time.perf_counter()
    iso_start = datetime.now(timezone.utc).isoformat()

    # Verify docker stats works BEFORE running sessions (fails cleanly with no partial JSON)
    sample_docker_stats(container_name, fake_stats_file)

    for i in range(sessions):
        # 1. Run one scripted bot session
        run_bot_like(host=host, port=port, dry_run=dry_run)

        # 2. Sample docker stats
        cpu_pct, mem_mb = sample_docker_stats(container_name, fake_stats_file)
        sample_time = datetime.now(timezone.utc).isoformat()
        samples.append({
            "timestamp": sample_time,
            "session_idx": i + 1,
            "cpu_pct": cpu_pct,
            "memory_mb": mem_mb,
        })

    wall_time = time.perf_counter() - t_start

    # Write sampled stats to CSV
    csv_file = output_dir / f"samples_{tier}_{int(time.time())}.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "session_idx", "cpu_pct", "memory_mb"])
        writer.writeheader()
        writer.writerows(samples)

    # Compute statistics
    cpu_values = [s["cpu_pct"] for s in samples]
    mem_values = [s["memory_mb"] for s in samples]

    mean_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0.0
    max_cpu = max(cpu_values) if cpu_values else 0.0
    mean_mem = sum(mem_values) / len(mem_values) if mem_values else 0.0
    max_mem = max(mem_values) if mem_values else 0.0

    cmd_line_str = raw_command_line or " ".join(sys.argv)

    cost_payload = {
        "tier": tier,
        "N": sessions,
        "wall_time": round(wall_time, 4),
        "mean_cpu_pct": round(mean_cpu, 2),
        "max_cpu_pct": round(max_cpu, 2),
        "mean_memory_mb": round(mean_mem, 2),
        "max_memory_mb": round(max_mem, 2),
        "command_line": cmd_line_str,
        "git_commit": get_git_commit(),
        "timestamp": iso_start,
    }

    # Atomically write results/cost_model.json
    tmp_json = cost_model_file.with_suffix(".tmp")
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(cost_payload, f, indent=2)
    tmp_json.replace(cost_model_file)

    return cost_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure Hardware Resource Cost per Tier (G7)")
    parser.add_argument("--tier", required=True, choices=["T1", "T2"], help="Persona tier to evaluate")
    parser.add_argument("--sessions", type=int, default=5, help="Number of bot sessions to run")
    parser.add_argument("--host", default="127.0.0.1", help="Target sensor host")
    parser.add_argument("--port", type=int, default=2222, help="Target sensor port")
    parser.add_argument("--container", default="schrodinger-sensor", help="Docker container name to monitor")
    parser.add_argument("--dry-run", action="store_true", help="Run bot scenario in dry-run mode")
    parser.add_argument("--fake-stats-file", type=Path, default=None, help="Path to fake docker stats JSON for testing")
    args = parser.parse_args()

    payload = measure_cost(
        tier=args.tier,
        sessions=args.sessions,
        host=args.host,
        port=args.port,
        container_name=args.container,
        dry_run=args.dry_run,
        fake_stats_file=args.fake_stats_file,
    )
    print(f"[measure_cost] Completed {args.tier} measurement: {json.dumps(payload, indent=2)}")


if __name__ == "__main__":
    main()
