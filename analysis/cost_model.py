"""
Cost Model and Intelligence Yield Accounting Engine.
Pre-registered in SPEC.md Section 9, SPIKES.md S2, and EVAL.md Section 6.

Formulas:
- Yield:
    Y = w_cmd * min(D, 20)/20 + w_file * 1[F >= 1] + w_pivot * 1[P >= 1] + w_ttp * min(K, 8)/8
    where D = distinct commands, F = file transfers, P = pivots (direct-tcpip),
    K = distinct ATT&CK technique tags triggered.
- Cost:
    C = c_cpu * cpu_seconds + c_ram * gb_seconds + c_boot * vm_boots
    converted to Rupees (INR) using VPS infrastructure cost allocations.
"""

from __future__ import annotations

import math
import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set


# Standard ATT&CK patterns per SPEC.md Section 9.1
DEFAULT_ATTACK_PATTERNS: Dict[str, str] = {
    "T1082": r"(uname|/proc/cpuinfo|/etc/os-release|hostname|lscpu|sysctl|lsb_release)",
    "T1033": r"(whoami|id\b|\blast\b|\bw\b|/etc/passwd|/etc/shadow|logname)",
    "T1057": r"(ps\s+(-[a-zA-Z]+|aux|ef)?|top\b|htop\b|pstree\b)",
    "T1083": r"(ls\s+(-[a-zA-Z]+)?|find\s+|pwd\b|dir\b|tree\b)",
    "T1046": r"(netstat\b|ss\s+(-[a-zA-Z]+)?|lsof\s+-i|nmap\b|arp\s+-a|ip\s+addr|ifconfig\b)",
    "T1105": r"(wget\b|curl\b|tftp\b|ftpget\b|scp\b|fetch\b)",
    "T1059.004": r"(sh\s+-c|bash\s+-c|/bin/sh|/bin/bash|python\s+-c|perl\s+-e)",
    "T1053.003": r"(crontab\s+(-[elr]|/)|/etc/cron\.|/var/spool/cron)",
    "T1098.004": r"(authorized_keys|id_rsa\.pub|ssh-keygen|id_ed25519\.pub)",
    "T1070.004": r"(rm\s+(-[rf]+|--force)|unlink\b|shred\b)",
    "T1496": r"(xmrig|minerd|cryptonight|stratum\+tcp|minexmr|coinhive)",
}


@dataclass
class YieldWeights:
    """Pre-registered weights for intelligence yield computation."""
    w_cmd: float = 1.0
    w_file: float = 1.0
    w_pivot: float = 1.0
    w_ttp: float = 1.0


@dataclass
class CostParameters:
    """
    Cost allocation parameters in INR per resource-second.
    Based on standard 2 vCPU / 4 GB RAM VPS at ₹2000/month (₹0.00077/sec).
    """
    c_cpu_per_second: float = 0.00025    # Cost per vCPU core-second
    c_ram_per_gb_second: float = 0.00010 # Cost per GB-second of RAM
    c_boot_per_vm: float = 0.05000       # Cold VM boot overhead (T3)
    c_pool_idle_per_second: float = 0.00020 # Standby idle pool maintenance

    # Resource profiles per tier
    t1_ram_gb: float = 0.05
    t1_cpu_ratio: float = 0.02
    t2_ram_gb: float = 0.10
    t2_cpu_ratio: float = 0.05
    t3_ram_gb: float = 1.00
    t3_cpu_ratio: float = 0.25


def load_attack_map(config_path: Optional[str] = None) -> Dict[str, re.Pattern]:
    """Load and compile ATT&CK regex patterns from config/attack_map.yaml or default."""
    patterns = dict(DEFAULT_ATTACK_PATTERNS)
    target_path = Path(config_path) if config_path else Path(__file__).resolve().parent.parent / "config" / "attack_map.yaml"
    
    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Simple YAML parser for key/regex pairs
            current_tag = None
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.endswith(":") and not line.startswith("name:") and not line.startswith("regex:"):
                    current_tag = line[:-1].strip()
                elif "regex:" in line and current_tag:
                    m = re.search(r'regex:\s*["\']?(.*?)["\']?$', line)
                    if m:
                        patterns[current_tag] = m.group(1).replace("\\\\", "\\")
        except Exception:
            pass  # Fall back to DEFAULT_ATTACK_PATTERNS cleanly

    compiled = {}
    for tag, reg_str in patterns.items():
        try:
            compiled[tag] = re.compile(reg_str, re.IGNORECASE)
        except re.error:
            continue
    return compiled


_COMPILED_ATTACK_MAP = load_attack_map()


def classify_attack_techniques(
    commands: List[str], attack_map: Optional[Dict[str, re.Pattern]] = None
) -> Set[str]:
    """Map a sequence of commands to unique MITRE ATT&CK technique tags."""
    if not commands:
        return set()
    mapper = attack_map if attack_map is not None else _COMPILED_ATTACK_MAP
    detected: Set[str] = set()
    for cmd in commands:
        if not cmd:
            continue
        for tag, pattern in mapper.items():
            if pattern.search(cmd):
                detected.add(tag)
    return detected


def compute_session_yield(
    d_commands: int,
    f_files: int,
    p_pivots: int,
    k_ttps: int,
    weights: Optional[YieldWeights] = None,
) -> float:
    """
    Compute intelligence yield Y per SPEC.md Section 9.1:
      Y = w_cmd * min(D, 20)/20 + w_file * 1[F >= 1] + w_pivot * 1[P >= 1] + w_ttp * min(K, 8)/8
    """
    w = weights or YieldWeights()
    part_cmd = w.w_cmd * (min(max(0, d_commands), 20) / 20.0)
    part_file = w.w_file * (1.0 if f_files >= 1 else 0.0)
    part_pivot = w.w_pivot * (1.0 if p_pivots >= 1 else 0.0)
    part_ttp = w.w_ttp * (min(max(0, k_ttps), 8) / 8.0)
    return part_cmd + part_file + part_pivot + part_ttp


def compute_session_cost(
    tier: str,
    duration_seconds: float = 60.0,
    cost_params: Optional[CostParameters] = None,
) -> float:
    """
    Compute session cost C in INR per SPEC.md Section 9.2:
      C = c_cpu * cpu_seconds + c_ram * gb_seconds + c_boot * vm_boots
    """
    p = cost_params or CostParameters()
    dur = max(1.0, float(duration_seconds))
    tier_upper = tier.upper()

    if tier_upper == "T1":
        ram_gb = p.t1_ram_gb
        cpu_sec = dur * p.t1_cpu_ratio
        boots = 0
    elif tier_upper == "T2":
        ram_gb = p.t2_ram_gb
        cpu_sec = dur * p.t2_cpu_ratio
        boots = 0
    elif tier_upper == "T3":
        ram_gb = p.t3_ram_gb
        cpu_sec = dur * p.t3_cpu_ratio
        boots = 1
    else:
        # Default fallback to T1 Lite
        ram_gb = p.t1_ram_gb
        cpu_sec = dur * p.t1_cpu_ratio
        boots = 0

    cost_ram = p.c_ram_per_gb_second * (ram_gb * dur)
    cost_cpu = p.c_cpu_per_second * cpu_sec
    cost_boot = p.c_boot_per_vm * boots

    return cost_ram + cost_cpu + cost_boot


def evaluate_arm_efficiency(
    sessions_data: List[Dict],
    arm_policy: Callable[[Dict], str],
    cost_params: Optional[CostParameters] = None,
    weights: Optional[YieldWeights] = None,
) -> Dict:
    """
    Evaluate an experimental arm (A, B, C, or adaptive D) on a dataset of sessions.
    Returns total yield, total cost in INR, yield per rupee, and tier distributions.
    """
    total_yield = 0.0
    total_cost = 0.0
    tier_counts = {"T1": 0, "T2": 0, "T3": 0}

    for session in sessions_data:
        assigned_tier = arm_policy(session)
        assigned_tier = assigned_tier.upper() if assigned_tier in ("T1", "T2", "T3") else "T1"
        tier_counts[assigned_tier] = tier_counts.get(assigned_tier, 0) + 1

        cmds = session.get("commands", [])
        files = session.get("files", 0)
        pivots = session.get("pivots", 0)
        dur = session.get("duration", 60.0)

        ttps = classify_attack_techniques(cmds)
        d_cmd = len(set(cmds))
        k_ttp = len(ttps)

        y = compute_session_yield(d_cmd, files, pivots, k_ttp, weights=weights)
        c = compute_session_cost(assigned_tier, duration_seconds=dur, cost_params=cost_params)

        total_yield += y
        total_cost += c

    yield_per_rupee = (total_yield / total_cost) if total_cost > 0 else 0.0
    n_sessions = len(sessions_data)
    escalation_rate = (tier_counts["T2"] + tier_counts["T3"]) / n_sessions if n_sessions > 0 else 0.0

    return {
        "n_sessions": n_sessions,
        "total_yield": round(total_yield, 4),
        "total_cost": round(total_cost, 6),
        "yield_per_rupee": round(yield_per_rupee, 4),
        "escalation_rate": round(escalation_rate, 4),
        "tier_counts": tier_counts,
    }


def run_yield_sensitivity_analysis(
    sessions_data: List[Dict],
    n_trials: int = 100,
    seed: int = 42,
) -> Dict:
    """
    Execute sensitivity analysis over random yield weights per EVAL.md Section 6.
    Ensures conclusions are not artifacts of arbitrary weight selection.
    """
    rng = random.Random(seed)
    trial_yields: List[float] = []

    for _ in range(n_trials):
        # Sample positive random weights normalized to mean 1.0
        raw_weights = [rng.uniform(0.1, 2.0) for _ in range(4)]
        scale = 4.0 / sum(raw_weights)
        w = YieldWeights(
            w_cmd=raw_weights[0] * scale,
            w_file=raw_weights[1] * scale,
            w_pivot=raw_weights[2] * scale,
            w_ttp=raw_weights[3] * scale,
        )

        total_y = 0.0
        for session in sessions_data:
            cmds = session.get("commands", [])
            files = session.get("files", 0)
            pivots = session.get("pivots", 0)
            ttps = classify_attack_techniques(cmds)
            total_y += compute_session_yield(len(set(cmds)), files, pivots, len(ttps), weights=w)

        trial_yields.append(round(total_y, 4))

    mean_yield = sum(trial_yields) / len(trial_yields) if trial_yields else 0.0
    variance = sum((x - mean_yield) ** 2 for x in trial_yields) / len(trial_yields) if trial_yields else 0.0
    std_yield = math.sqrt(variance)

    return {
        "n_trials": n_trials,
        "mean_yield": round(mean_yield, 4),
        "std_yield": round(std_yield, 4),
        "min_yield": min(trial_yields) if trial_yields else 0.0,
        "max_yield": max(trial_yields) if trial_yields else 0.0,
        "trials": trial_yields,
    }
