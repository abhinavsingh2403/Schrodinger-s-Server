"""Unit tests for analysis/s3_base_rates.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analysis.s3_base_rates import SCHEMA_25_FIELDS, run_pipeline


def make_sample_session(session_id: str, day: str, **overrides) -> dict:
    """Generate a valid 25-field session row with sensible defaults."""
    row = {
        "session": session_id,
        "src_ip": "192.0.2.1",
        "honeypot_ip": "198.51.100.1",
        "first_seen": f"{day}T12:00:00Z",
        "last_seen": f"{day}T12:05:00Z",
        "total_events": 10,
        "cnt_client_fingerprint": 1,
        "cnt_client_kex": 1,
        "cnt_client_size": 1,
        "cnt_client_var": 0,
        "cnt_client_version": 1,
        "cnt_command_failed": 0,
        "cnt_command_input": 0,
        "cnt_command_success": 0,
        "cnt_direct_tcpip_data": 0,
        "cnt_direct_tcpip_request": 0,
        "cnt_file_download": 0,
        "cnt_file_download_failed": 0,
        "cnt_file_upload": 0,
        "cnt_log_closed": 1,
        "cnt_login_failed": 0,
        "cnt_login_success": 1,
        "cnt_session_closed": 1,
        "cnt_session_connect": 1,
        "cnt_session_params": 1,
    }
    row.update(overrides)
    return row


def create_10_row_jsonl(file_path: Path) -> None:
    """Create a synthetic 10-row dataset exercising specific edge cases."""
    rows = [
        # Day 1: 2024-01-01
        # Row 1: Exactly 4 commands -> value = 0
        make_sample_session("s1", "2024-01-01", cnt_command_input=4),
        # Row 2: Exactly 5 commands -> value = 1
        make_sample_session("s2", "2024-01-01", cnt_command_input=5),
        # Row 3: File upload only, no login -> value = 1
        make_sample_session("s3", "2024-01-01", cnt_login_success=0, cnt_file_upload=1),
        # Row 4: File download only -> value = 1
        make_sample_session("s4", "2024-01-01", cnt_file_download=1),
        # Row 5: Direct-tcpip only -> value = 1
        make_sample_session("s5", "2024-01-01", cnt_direct_tcpip_request=1),

        # Day 2: 2024-01-02
        # Row 6: No login, 0 commands, probe only -> value = 0
        make_sample_session("s6", "2024-01-02", cnt_login_success=0, cnt_login_failed=3),
        # Row 7: 2 commands (bin 1-4) -> value = 0
        make_sample_session("s7", "2024-01-02", cnt_command_input=2),
        # Row 8: 8 commands (bin 5-9) -> value = 1
        make_sample_session("s8", "2024-01-02", cnt_command_input=8),
        # Row 9: 15 commands (bin 10+) -> value = 1
        make_sample_session("s9", "2024-01-02", cnt_command_input=15),
        # Row 10: Login success, but 0 commands -> value = 0
        make_sample_session("s10", "2024-01-02", cnt_command_input=0),
    ]

    with file_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_base_rates_pipeline(tmp_path: Path) -> None:
    data_file = tmp_path / "synthetic_sessions.jsonl"
    out_file = tmp_path / "base_rates.json"
    man_file = tmp_path / "MANIFEST.json"

    create_10_row_jsonl(data_file)

    results = run_pipeline(
        data_path=data_file,
        n_cmd=5,
        output_path=out_file,
        manifest_path=man_file,
    )

    # 1. Overall verification
    overall = results["overall"]
    assert overall["total_sessions"] == 10
    # Sessions with login success: all except s3 (no login) and s6 (failed login only) = 8
    assert overall["sessions_with_login_success"] == 8
    assert overall["share_login_success"] == 0.8
    # Sessions with commands: s1 (4), s2 (5), s7 (2), s8 (8), s9 (15) = 5
    assert overall["sessions_with_command_input"] == 5
    assert overall["share_command_input"] == 0.5

    # 2. Command input distribution verification
    counts = overall["command_input_distribution"]["counts"]
    assert counts["0"] == 5        # s3, s4, s5, s6, s10
    assert counts["1_to_4"] == 2   # s1 (4), s7 (2)
    assert counts["5_to_9"] == 2   # s2 (5), s8 (8)
    assert counts["10_plus"] == 1  # s9 (15)

    # 3. File transfer and direct-tcpip shares
    assert overall["file_transfer"]["count"] == 2  # s3, s4
    assert overall["file_transfer"]["share"] == 0.2
    assert overall["direct_tcpip_request"]["count"] == 1  # s5
    assert overall["direct_tcpip_request"]["share"] == 0.1

    # 4. Value=1 approximation verification
    # Rows with value=1: s2 (>=5), s3 (upload), s4 (download), s5 (tcpip), s8 (>=5), s9 (>=5) = 6
    val1 = overall["value_1_approximation"]
    assert val1["count"] == 6
    assert val1["base_rate"] == 0.6

    # 5. Daily grouping and integrity assertions
    by_day = results["by_day"]
    assert len(by_day) == 2
    assert "2024-01-01" in by_day
    assert "2024-01-02" in by_day

    day1 = by_day["2024-01-01"]
    assert day1["total_sessions"] == 5
    assert day1["value_1_count"] == 4  # s2, s3, s4, s5
    assert day1["value_1_base_rate"] == 0.8

    day2 = by_day["2024-01-02"]
    assert day2["total_sessions"] == 5
    assert day2["value_1_count"] == 2  # s8, s9
    assert day2["value_1_base_rate"] == 0.4

    # Daily sums match overall totals
    assert day1["total_sessions"] + day2["total_sessions"] == overall["total_sessions"]
    assert day1["value_1_count"] + day2["value_1_count"] == val1["count"]

    # 6. File outputs check
    assert out_file.is_file()
    assert man_file.is_file()

    with man_file.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
        assert manifest["duckdb_version"] is not None
        assert manifest["file_md5"] is not None
        assert manifest["n_cmd_threshold"] == 5


def test_missing_schema_field(tmp_path: Path) -> None:
    data_file = tmp_path / "broken_schema.jsonl"
    out_file = tmp_path / "out.json"
    man_file = tmp_path / "man.json"

    # Create row missing 'cnt_client_kex'
    row = make_sample_session("s_bad", "2024-01-01")
    del row["cnt_client_kex"]

    with data_file.open("w", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")

    with pytest.raises(ValueError, match="Missing required fields.*cnt_client_kex"):
        run_pipeline(data_path=data_file, output_path=out_file, manifest_path=man_file)
