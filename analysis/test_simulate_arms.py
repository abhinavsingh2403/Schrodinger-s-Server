"""
Tests for Empirical Arm Simulation Pipeline (analysis/simulate_arms.py).
Pre-registered in EVAL.md Section 5.1 and SPEC.md Section 9.
"""

from __future__ import annotations

import json
import os
import tempfile
import pytest
from analysis.simulate_arms import run_arm_simulation_on_records, summarize_simulation_results


def test_arm_simulation_on_records():
    """Verify simulation logic across all 4 experimental arms."""
    mock_records = [
        {"session_id": "s1", "cnt_command_input": 0, "cnt_file_download": 0, "cnt_file_upload": 0, "cnt_direct_tcpip_request": 0, "duration": 5.0, "login_success": False, "has_pty": False},
        {"session_id": "s2", "cnt_command_input": 12, "cnt_file_download": 1, "cnt_file_upload": 0, "cnt_direct_tcpip_request": 0, "duration": 120.0, "login_success": True, "has_pty": True},
        {"session_id": "s3", "cnt_command_input": 2, "cnt_file_download": 0, "cnt_file_upload": 0, "cnt_direct_tcpip_request": 0, "duration": 15.0, "login_success": True, "has_pty": False},
        {"session_id": "s4", "cnt_command_input": 0, "cnt_file_download": 0, "cnt_file_upload": 0, "cnt_direct_tcpip_request": 0, "duration": 3.0, "login_success": False, "has_pty": False},
        {"session_id": "s5", "cnt_command_input": 25, "cnt_file_download": 0, "cnt_file_upload": 1, "cnt_direct_tcpip_request": 1, "duration": 200.0, "login_success": True, "has_pty": True},
    ]

    results = run_arm_simulation_on_records(mock_records)

    assert "Arm A (Static T1)" in results
    assert "Arm B (Static T2)" in results
    assert "Arm C (Static T3)" in results
    assert "Arm D (Adaptive)" in results

    # Verify Arm A: all sessions served T1
    arm_a = results["Arm A (Static T1)"]
    assert arm_a["tier_counts"]["T1"] == 5
    assert arm_a["tier_counts"]["T2"] == 0

    # Verify Arm C: all sessions served T3
    arm_c = results["Arm C (Static T3)"]
    assert arm_c["tier_counts"]["T3"] == 5
    assert arm_c["total_cost"] > arm_a["total_cost"]

    # Verify Arm D (Adaptive): selective escalation
    arm_d = results["Arm D (Adaptive)"]
    assert arm_d["tier_counts"]["T1"] > 0
    assert (arm_d["tier_counts"]["T2"] + arm_d["tier_counts"]["T3"]) > 0
    # Yield per Rupee efficiency of Adaptive > Static T3
    assert arm_d["yield_per_rupee"] > arm_c["yield_per_rupee"]


def test_summarize_simulation_results():
    """Verify summary metrics calculation, disclaimers, and formatting."""
    sim_data = {
        "Arm A (Static T1)": {"total_yield": 10.0, "total_cost": 2.0, "yield_per_rupee": 5.0, "tier_counts": {"T1": 10, "T2": 0, "T3": 0}},
        "Arm C (Static T3)": {"total_yield": 10.0, "total_cost": 20.0, "yield_per_rupee": 0.5, "tier_counts": {"T1": 0, "T2": 0, "T3": 10}},
        "Arm D (Adaptive)": {"total_yield": 18.0, "total_cost": 1.2, "yield_per_rupee": 15.0, "tier_counts": {"T1": 8, "T2": 2, "T3": 0}},
    }
    summary = summarize_simulation_results(sim_data)
    assert summary["status"] == "SIMULATION_COMPLETE_ORACLE_BOUND"
    assert "scientific_disclaimers" in summary
    assert summary["efficiency_ratios"]["yield_per_rupee_ratio_arm_d_vs_arm_a"] == 3.0  # 15.0 / 5.0
    assert summary["efficiency_ratios"]["yield_per_rupee_ratio_arm_d_vs_arm_c"] == 30.0  # 15.0 / 0.5
