"""
populate_demo_db.py: Pre-populates SQLite decision_log with authentic lab decisions.

Executes the genuine DecisionEngine with lab mode thresholds (config/policy_lab.yaml)
across the three canonical adversary scenarios:
1. bot_like: Mass scanner probe with failed authentication -> T1 LITE
2. interactive: Interactive shell with login success & PTY allocation -> T2 HARDENED
3. transfer_like: Tool ingress probe attempting download -> T2 HARDENED

Enforces:
- Strict un-fabricated feature evaluation through DecisionEngine
- Masked visitor IDs (vis_xxxx) with zero raw IPs stored
- Authentic decision latencies, stage vectors, and SQLite WAL logging
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gatekeeper.decision_api import DecisionEngine
from gatekeeper.policy import EscalationPolicy
from gatekeeper.visitor_memory import VisitorMemory


def populate_lab_decisions(
    db_path: str | Path = "gatekeeper/gatekeeper.db",
    reset: bool = False,
) -> int:
    """Populates db_path with decisions from the three lab scenarios using DecisionEngine."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    if reset and db_file.exists():
        try:
            db_file.unlink()
            for ext in ("-wal", "-shm"):
                wal_file = Path(f"{db_path}{ext}")
                if wal_file.exists():
                    wal_file.unlink()
            print(f"[CLEAN] Reset existing database at {db_path}")
        except Exception as e:
            print(f"[WARN] Could not reset {db_path}: {e}")

    # Use lab mode policy with demo-friendly thresholds
    lab_cfg = PROJECT_ROOT / "config" / "policy_lab.yaml"
    policy = EscalationPolicy(config_path=lab_cfg if lab_cfg.is_file() else None)
    memory = VisitorMemory(db_path=str(db_path))
    engine = DecisionEngine(db_path=str(db_path), policy=policy, memory=memory)

    total_decisions = 0

    print("=" * 65)
    print("Populating Lab Demonstration Decisions via DecisionEngine")
    print(f"Target DB: {db_path} [Mode: LAB]")
    print("=" * 65)

    # -------------------------------------------------------------
    # Scenario 1: Bot-Like Scanner Probe (Expected Tier: T1 LITE)
    # -------------------------------------------------------------
    sess_bot = "sess_lab_bot_01"
    ip_bot = "192.0.2.10"  # RFC 5737 TEST-NET-1 (dummy loopback representation)

    # Stage S1: Connect & Handshake
    d1 = engine.decide(
        session_id=sess_bot,
        source_ip=ip_bot,
        stage="S1",
        features={"cnt_client_kex": 1, "cnt_client_version": 1},
        current_tier="T1",
    )
    total_decisions += 1
    print(f"[{sess_bot}] S1 Handshake  -> Tier: {d1['tier']:<11} Score: {d1['score']:<6} ({d1['score_source']})")

    # Stage S2: Failed Authentication
    d2 = engine.decide(
        session_id=sess_bot,
        source_ip=ip_bot,
        stage="S2",
        features={"cnt_login_failed": 3, "cnt_login_success": 0},
        current_tier=d1["tier"],
    )
    total_decisions += 1
    print(f"[{sess_bot}] S2 Auth Probe -> Tier: {d2['tier']:<11} Score: {d2['score']:<6} ({d2['score_source']})")

    # Close session
    engine.record_session(source_ip=ip_bot, tier_served=d2["tier"], value_label=0)

    # -------------------------------------------------------------
    # Scenario 2: Interactive Recon Attacker (Expected Tier: T2 HARDENED)
    # -------------------------------------------------------------
    sess_int = "sess_lab_int_02"
    ip_int = "192.0.2.20"

    # Stage S1: Connect & Handshake
    d3 = engine.decide(
        session_id=sess_int,
        source_ip=ip_int,
        stage="S1",
        features={"cnt_client_kex": 1, "cnt_client_version": 1},
        current_tier="T1",
    )
    total_decisions += 1
    print(f"[{sess_int}] S1 Handshake  -> Tier: {d3['tier']:<11} Score: {d3['score']:<6} ({d3['score_source']})")

    # Stage S2: Successful Login (Triggers T2 Escalation in Lab Mode!)
    d4 = engine.decide(
        session_id=sess_int,
        source_ip=ip_int,
        stage="S2",
        features={"cnt_login_failed": 0, "cnt_login_success": 1},
        current_tier=d3["tier"],
    )
    total_decisions += 1
    print(f"[{sess_int}] S2 Login Pass -> Tier: {d4['tier']:<11} Score: {d4['score']:<6} ({d4['score_source']})")

    # Stage S3: Interactive PTY Requested
    d5 = engine.decide(
        session_id=sess_int,
        source_ip=ip_int,
        stage="S3",
        features={"cnt_login_success": 1, "has_pty": 1, "cnt_client_size": 1, "cnt_client_var": 1},
        current_tier=d4["tier"],
    )
    total_decisions += 1
    print(f"[{sess_int}] S3 PTY Channel -> Tier: {d5['tier']:<11} Score: {d5['score']:<6} ({d5['score_source']})")

    # Stage S4: Interactive Shell Commands
    d6 = engine.decide(
        session_id=sess_int,
        source_ip=ip_int,
        stage="S4",
        features={"s4_cmd1_has_pipe": 1, "chaining_ops_count": 1},
        current_tier=d5["tier"],
    )
    total_decisions += 1
    print(f"[{sess_int}] S4 Shell Cmds  -> Tier: {d6['tier']:<11} Score: {d6['score']:<6} ({d6['score_source']})")

    # Close session
    engine.record_session(source_ip=ip_int, tier_served=d6["tier"], value_label=1)

    # -------------------------------------------------------------
    # Scenario 3: Tool Ingress / Transfer Attacker (Expected Tier: T2 HARDENED)
    # -------------------------------------------------------------
    sess_trf = "sess_lab_trf_03"
    ip_trf = "192.0.2.30"

    # Stage S1: Connect
    d7 = engine.decide(
        session_id=sess_trf,
        source_ip=ip_trf,
        stage="S1",
        features={"cnt_client_kex": 1, "cnt_client_version": 1},
        current_tier="T1",
    )
    total_decisions += 1
    print(f"[{sess_trf}] S1 Handshake  -> Tier: {d7['tier']:<11} Score: {d7['score']:<6} ({d7['score_source']})")

    # Stage S2: Login Success
    d8 = engine.decide(
        session_id=sess_trf,
        source_ip=ip_trf,
        stage="S2",
        features={"cnt_login_failed": 1, "cnt_login_success": 1},
        current_tier=d7["tier"],
    )
    total_decisions += 1
    print(f"[{sess_trf}] S2 Login Pass -> Tier: {d8['tier']:<11} Score: {d8['score']:<6} ({d8['score_source']})")

    # Stage S4: Download / Wget Command
    d9 = engine.decide(
        session_id=sess_trf,
        source_ip=ip_trf,
        stage="S4",
        features={"s4_cmd1_has_chain": 1, "cnt_command_input": 1},
        current_tier=d8["tier"],
    )
    total_decisions += 1
    print(f"[{sess_trf}] S4 Ingress Cmd -> Tier: {d9['tier']:<11} Score: {d9['score']:<6} ({d9['score_source']})")

    # Close session
    engine.record_session(source_ip=ip_trf, tier_served=d9["tier"], value_label=1)

    print("=" * 65)
    print(f"Successfully recorded {total_decisions} decisions into {db_path}!")
    print("=" * 65)
    return total_decisions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate Lab Demo Decisions")
    parser.add_argument("--db", default="gatekeeper/gatekeeper.db", help="Path to SQLite decision DB")
    parser.add_argument("--reset", action="store_true", help="Reset existing database before writing")
    args = parser.parse_args()

    populate_lab_decisions(db_path=args.db, reset=args.reset)
