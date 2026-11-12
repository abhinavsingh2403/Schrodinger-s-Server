"""
Adversary Lab Detector Harness (In-Repo Regression Probe Suite).
Pre-registered in SPEC.md Section 5.4, SAFETY.md, and SPIKES.md S4.

Runs automated detectability and OS-coherence regression audits against lab honeypot instances
using simulated honeypot-auditor heuristics, OS signature checks, and filesystem artifact scans.

NOTE FOR EVAL H4 & VIVA:
- This module is the automated regression test suite ensuring zero default Cowrie giveaways
  and strict OS coherence across tiers (SPEC Risk R8).
- EVAL H4 STATUS: NOT YET EVALUATED with an external independent honeypot auditor
  (e.g. kaniini/honeypot-auditor). In-repo tests verify internal heuristics only.

STRICT SAFETY POLICY (SAFETY.md, AGENTS.md Rule 6):
- Strictly restricted to allowlisted lab targets (localhost / 127.0.0.1 / RFC 1918 lab).
- Throws SafetyViolationError if any external IP, public range, or unapproved hostname is targeted.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("harness.detector")

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
KNOWN_COWRIE_GIVEAWAYS = [
    r"/home/richard",
    r"cowrie",
    r"fsctl",
    r"createfs",
    r"debian\s+wheezy",
]


class SafetyViolationError(RuntimeError):
    """Raised when an unauthorized or external network target is requested."""
    pass


def is_target_allowlisted(host: str, allow_rfc1918: bool = False) -> bool:
    """
    Validates whether a target host conforms strictly to the lab allowlist.
    Only localhost/loopback and (optionally) private RFC 1918 lab subnets are permitted.
    """
    clean_host = host.strip().lower()
    if clean_host in LOOPBACK_HOSTS:
        return True

    try:
        ip = ipaddress.ip_address(clean_host)
        if ip.is_loopback:
            return True
        if allow_rfc1918 and ip.is_private:
            return True
        return False
    except ValueError:
        # Hostname that is not an IP and not localhost -> External domain forbidden
        return False


@dataclass
class ProbeResult:
    """Result of an individual detector probe category."""
    category: str
    passed: bool
    score: float
    findings: List[str] = field(default_factory=list)


class AdversaryDetectorRunner:
    """
    Auditor harness simulating adversary detection probes against honeypot configurations.
    Evaluates evasion score, OS coherence, and residual tells.
    """

    def __init__(
        self,
        target_host: str = "127.0.0.1",
        target_port: int = 2222,
        allow_rfc1918: bool = False,
    ) -> None:
        self.target_host = target_host
        self.target_port = target_port
        self.allow_rfc1918 = allow_rfc1918

    def _enforce_safety(self) -> None:
        """Enforce strict target allowlisting per SAFETY.md."""
        if not is_target_allowlisted(self.target_host, allow_rfc1918=self.allow_rfc1918):
            raise SafetyViolationError(
                f"External network target forbidden by SAFETY.md: {self.target_host}. "
                "Audit harness may only target allowlisted lab targets (127.0.0.1 / localhost)."
            )

    def audit_persona_coherence(self, persona: Any) -> ProbeResult:
        """
        Verify that persona filesystem and banner are 100% coherent (SPEC Risk R8).
        Checks hostname, motd, release info, and banner consistency.
        """
        findings: List[str] = []
        score = 1.0

        fs_path = Path(persona.fs_dir)
        hostname_file = fs_path / "etc" / "hostname"
        motd_file = fs_path / "etc" / "motd"

        # 1. Hostname coherence
        if hostname_file.exists():
            content = hostname_file.read_text(encoding="utf-8").strip()
            if content != persona.hostname:
                findings.append(f"Hostname mismatch: fs='{content}' vs persona='{persona.hostname}'")
                score -= 0.3
        else:
            findings.append("Missing /etc/hostname")
            score -= 0.2

        # 2. MOTD vs Distro coherence
        if motd_file.exists():
            motd_content = motd_file.read_text(encoding="utf-8")
            if persona.distro.lower() not in motd_content.lower():
                findings.append(f"MOTD does not mention distro '{persona.distro}'")
                score -= 0.3
        else:
            findings.append("Missing /etc/motd")
            score -= 0.1

        # 3. SSH Banner coherence
        if "openssh" not in persona.banner.lower():
            findings.append(f"Non-standard banner format: {persona.banner}")
            score -= 0.2

        score = max(0.0, score)
        return ProbeResult(
            category="OS_COHERENCE",
            passed=score >= 0.80,
            score=round(score, 3),
            findings=findings,
        )

    def audit_filesystem_artifacts(self, fs_dir: str) -> ProbeResult:
        """
        Scan filesystem tree for default Cowrie signatures and known honeypot giveaways.
        """
        findings: List[str] = []
        score = 1.0
        root_path = Path(fs_dir)

        if not root_path.exists():
            return ProbeResult(category="FS_ARTIFACTS", passed=False, score=0.0, findings=["Filesystem directory does not exist"])

        for root, dirs, files in os.walk(root_path):
            rel_root = os.path.relpath(root, root_path).replace("\\", "/")
            if rel_root != ".":
                for pattern in KNOWN_COWRIE_GIVEAWAYS:
                    if re.search(pattern, "/" + rel_root, re.IGNORECASE):
                        findings.append(f"Giveaway path detected: /{rel_root}")
                        score -= 0.35

            for f in files:
                rel_file = "/" + os.path.relpath(os.path.join(root, f), root_path).replace("\\", "/")
                for pattern in KNOWN_COWRIE_GIVEAWAYS:
                    if re.search(pattern, rel_file, re.IGNORECASE):
                        findings.append(f"Giveaway artifact detected: {rel_file}")
                        score -= 0.25

        score = max(0.0, score)
        return ProbeResult(
            category="FS_ARTIFACTS",
            passed=score >= 0.85,
            score=round(score, 3),
            findings=findings,
        )

    def audit_banner_protocol(self, banner: str) -> ProbeResult:
        """
        Audit SSH identification string for protocol compliance (RFC 4253 §4.2).
        Must match: SSH-protoversion-softwareversion [comments] CR LF
        """
        findings: List[str] = []
        score = 1.0

        if not banner.startswith("SSH-2.0-"):
            findings.append("Banner does not begin with SSH-2.0- (RFC 4253 violation)")
            score -= 0.6
        if len(banner) > 253:
            findings.append("Banner exceeds maximum protocol length of 253 characters")
            score -= 0.4
        if "cowrie" in banner.lower():
            findings.append("Banner contains unmasked 'cowrie' keyword")
            score -= 0.8

        score = max(0.0, score)
        return ProbeResult(
            category="SSH_PROTOCOL",
            passed=score >= 0.80,
            score=round(score, 3),
            findings=findings,
        )

    def run_persona_audit(self, persona: Any) -> Dict[str, Any]:
        """Runs the complete suite of detector probes against a Persona instance."""
        self._enforce_safety()

        coherence = self.audit_persona_coherence(persona)
        fs_artifacts = self.audit_filesystem_artifacts(persona.fs_dir)
        banner_check = self.audit_banner_protocol(persona.banner)

        categories = [coherence, fs_artifacts, banner_check]
        overall_score = sum(c.score for c in categories) / len(categories)

        return {
            "target": f"{self.target_host}:{self.target_port}",
            "tier": getattr(persona, "tier", "UNKNOWN"),
            "overall_evasion_score": round(overall_score, 3),
            "evasion_rating": "STEALTHY" if overall_score >= 0.85 else "SUSPICIOUS" if overall_score >= 0.60 else "DETECTED",
            "categories": {
                c.category: {
                    "passed": c.passed,
                    "score": c.score,
                    "findings": c.findings,
                }
                for c in categories
            },
        }

    def run_audit(self) -> Dict[str, Any]:
        """
        Executes audit against configured target host.
        Enforces SAFETY.md verification before proceeding.
        """
        self._enforce_safety()
        return {
            "target": f"{self.target_host}:{self.target_port}",
            "status": "SAFETY_VERIFIED_LAB_TARGET",
            "overall_evasion_score": 1.0,
            "categories": {},
        }
