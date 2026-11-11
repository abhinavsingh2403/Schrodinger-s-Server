"""Tests for Natural Experiment Persona Effect Analysis (EVAL 5.3).

Pre-registered in EVAL.md Section 5.3 and DATA.md Section D1.
Ensures association-only evaluation across honeypot instances without causal assertions.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import pytest

from analysis.natural_experiment import (
    wilson_score_interval,
    analyze_honeypot_instances,
    summarize_natural_experiment,
    run_natural_experiment_pipeline,
)


def test_wilson_score_interval_properties():
    """Verify statistical correctness of Wilson 95% confidence intervals."""
    # Degenerate case: 0 total
    low, high = wilson_score_interval(0, 0)
    assert low == 0.0 and high == 0.0

    # Rare event: 0 out of 100
    low_0, high_0 = wilson_score_interval(0, 100)
    assert low_0 == 0.0
    assert 0.03 < high_0 < 0.04  # ~0.036

    # Symmetric case: 50 out of 100
    low_50, high_50 = wilson_score_interval(50, 100)
    assert 0.40 < low_50 < 0.41
    assert 0.59 < high_50 < 0.60
    assert abs((low_50 + high_50) / 2.0 - 0.5) < 0.01


def test_analyze_honeypot_instances_associations():
    """Verify metrics per honeypot instance and guarantee association-only output."""
    mock_records = [
        # Instance HP_A: High interaction
        {"honeypot_ip": "hp_a", "cnt_command_input": 10, "cnt_file_download": 1, "cnt_file_upload": 0, "cnt_direct_tcpip_request": 0, "cnt_login_success": 1, "duration": 120.0},
        {"honeypot_ip": "hp_a", "cnt_command_input": 6, "cnt_file_download": 0, "cnt_file_upload": 0, "cnt_direct_tcpip_request": 0, "cnt_login_success": 1, "duration": 60.0},
        # Instance HP_B: Low interaction / scanner drop
        {"honeypot_ip": "hp_b", "cnt_command_input": 0, "cnt_file_download": 0, "cnt_file_upload": 0, "cnt_direct_tcpip_request": 0, "cnt_login_success": 0, "duration": 2.0},
        {"honeypot_ip": "hp_b", "cnt_command_input": 0, "cnt_file_download": 0, "cnt_file_upload": 0, "cnt_direct_tcpip_request": 0, "cnt_login_success": 0, "duration": 1.0},
    ]

    results = analyze_honeypot_instances(mock_records, n_cmd=5)

    assert "hp_a" in results
    assert "hp_b" in results

    hp_a = results["hp_a"]
    assert hp_a["total_sessions"] == 2
    assert hp_a["value_1_count"] == 2
    assert hp_a["value_1_rate"] == 1.0
    assert hp_a["mean_commands"] == 8.0
    assert hp_a["login_rate"] == 1.0

    hp_b = results["hp_b"]
    assert hp_b["total_sessions"] == 2
    assert hp_b["value_1_count"] == 0
    assert hp_b["value_1_rate"] == 0.0
    assert hp_b["mean_commands"] == 0.0
    assert hp_b["login_rate"] == 0.0

    # Ensure Wilson interval bounds exist and are within [0, 1]
    assert 0.0 <= hp_a["value_1_ci_95"][0] <= hp_a["value_1_ci_95"][1] <= 1.0
    assert 0.0 <= hp_b["value_1_ci_95"][0] <= hp_b["value_1_ci_95"][1] <= 1.0


def test_summarize_natural_experiment_disclaimer_and_no_causality():
    """Verify pre-registered EVAL 5.3 non-causal language constraints."""
    mock_instance_data = {
        "hp_a": {
            "total_sessions": 100,
            "value_1_count": 25,
            "value_1_rate": 0.25,
            "value_1_ci_95": [0.175, 0.343],
            "mean_commands": 4.5,
            "login_rate": 0.30,
            "mean_duration": 45.0,
        },
        "hp_b": {
            "total_sessions": 100,
            "value_1_count": 2,
            "value_1_rate": 0.02,
            "value_1_ci_95": [0.005, 0.07],
            "mean_commands": 0.1,
            "login_rate": 0.05,
            "mean_duration": 5.0,
        },
    }

    summary = summarize_natural_experiment(mock_instance_data)

    # Required EVAL 5.3 scientific caveat
    assert "caveat_disclaimer" in summary
    disclaimer = summary["caveat_disclaimer"].lower()
    assert "association" in disclaimer
    assert "confound" in disclaimer or "scanner targeting" in disclaimer

    # Verify no causal keys
    summary_str = json.dumps(summary).lower()
    assert "causal" not in summary_str or "no causal language" in summary_str
    assert "proved impact" not in summary_str


def test_run_natural_experiment_pipeline_with_tempfile():
    """Verify full end-to-end execution of pipeline saving JSON report."""
    mock_records = [
        {"honeypot_ip": "hp_1", "cnt_command_input": 5, "cnt_file_download": 0, "cnt_file_upload": 0, "cnt_direct_tcpip_request": 0, "cnt_login_success": 1, "duration": 10.0},
        {"honeypot_ip": "hp_2", "cnt_command_input": 0, "cnt_file_download": 0, "cnt_file_upload": 0, "cnt_direct_tcpip_request": 0, "cnt_login_success": 0, "duration": 1.0},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "natural_experiment.json"
        run_natural_experiment_pipeline(
            records=mock_records,
            output_path=str(out_path),
        )

        assert out_path.exists()
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["status"] == "EVAL_53_PERSONA_EFFECT_PENDING_EVENT_GROUP_DATA"
        assert "instances" in data
        assert "instance_variance_distribution" in data
