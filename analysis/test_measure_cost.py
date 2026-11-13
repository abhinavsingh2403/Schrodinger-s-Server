"""
Tests for Cost-Measurement Harness (analysis/measure_cost.py).
Enforces G7 acceptance criteria:
1. --dry-run with a fake docker stats output file.
2. Output JSON has all required keys.
3. Failing docker call produces a clear error and no partial JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from harness.detector_runner import SafetyViolationError
from analysis.measure_cost import measure_cost, sample_docker_stats, parse_memory_to_mb, parse_cpu_to_pct


def test_parse_memory_and_cpu():
    """Verify parsing of docker stats formatted strings."""
    assert parse_cpu_to_pct("1.25%") == 1.25
    assert parse_cpu_to_pct("0.0%") == 0.0
    assert parse_cpu_to_pct("invalid") == 0.0

    assert parse_memory_to_mb("45.2MiB / 7.66GiB") == 45.2
    assert parse_memory_to_mb("1.5GiB / 8.0GiB") == 1.5 * 1024.0
    assert parse_memory_to_mb("512KiB / 1GiB") == 512.0 / 1024.0


def test_measure_cost_dry_run_with_fake_stats(tmp_path: Path):
    """G7 Acceptance: dry-run with fake docker stats produces JSON with all keys."""
    fake_stats_file = tmp_path / "fake_docker_stats.json"
    fake_stats = {
        "Name": "schrodinger-sensor",
        "CPUPerc": "2.40%",
        "MemUsage": "48.5MiB / 8.00GiB",
    }
    fake_stats_file.write_text(json.dumps(fake_stats), encoding="utf-8")

    out_dir = tmp_path / "cost_csvs"
    cost_json = tmp_path / "cost_model.json"

    payload = measure_cost(
        tier="T1",
        sessions=3,
        host="127.0.0.1",
        port=2222,
        dry_run=True,
        fake_stats_file=fake_stats_file,
        output_dir=out_dir,
        cost_model_file=cost_json,
    )

    required_keys = [
        "tier",
        "N",
        "wall_time",
        "mean_cpu_pct",
        "max_cpu_pct",
        "mean_memory_mb",
        "max_memory_mb",
        "command_line",
        "git_commit",
        "timestamp",
    ]
    for k in required_keys:
        assert k in payload, f"Missing key '{k}' in payload"

    assert payload["tier"] == "T1"
    assert payload["N"] == 3
    assert payload["mean_cpu_pct"] == 2.4
    assert payload["mean_memory_mb"] == 48.5

    # Check file on disk
    assert cost_json.exists()
    disk_data = json.loads(cost_json.read_text(encoding="utf-8"))
    assert disk_data == payload

    # Check CSV samples created
    csv_files = list(out_dir.glob("*.csv"))
    assert len(csv_files) == 1


def test_failing_docker_call_produces_clear_error_and_no_partial_json(tmp_path: Path):
    """G7 Acceptance: Failing docker call produces a clear error and zero partial JSON."""
    cost_json = tmp_path / "cost_model.json"
    out_dir = tmp_path / "cost_csvs"

    # Container that does not exist and no fake stats file -> should raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        measure_cost(
            tier="T2",
            sessions=2,
            host="127.0.0.1",
            port=2222,
            container_name="nonexistent_container_xyz_999",
            dry_run=True,
            output_dir=out_dir,
            cost_model_file=cost_json,
        )

    # Must produce a clear error mentioning container or docker
    assert "nonexistent_container_xyz_999" in str(exc_info.value) or "Docker" in str(exc_info.value)

    # Must NOT produce any partial or corrupt JSON file
    assert not cost_json.exists(), "Failing docker call must not create partial JSON"


def test_measure_cost_safety_guard_public_ip(tmp_path: Path):
    """Verify measure_cost obeys safety allowlist and refuses public IPs."""
    cost_json = tmp_path / "cost_model.json"
    with pytest.raises(SafetyViolationError):
        measure_cost(
            tier="T1",
            host="8.8.8.8",
            cost_model_file=cost_json,
        )
    assert not cost_json.exists()
