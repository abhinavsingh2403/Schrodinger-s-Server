"""
Common safety guards and execution helpers for adversary lab demo scripts.
Enforces SAFETY.md and AGENTS.md Rule 6:
- Only allowlisted lab targets (127.0.0.1, localhost, RFC 1918 private IPs) are permitted.
- Refuses any public IP, internet hostname, or unauthorized target.
"""

from __future__ import annotations

import argparse
import ipaddress
import subprocess
import sys
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from harness.detector_runner import is_target_allowlisted, SafetyViolationError


def assert_lab_target_allowlisted(host: str) -> None:
    """Refuses execution unless host is strictly 127.0.0.1, localhost, or RFC1918 private IP."""
    if not is_target_allowlisted(host, allow_rfc1918=True):
        raise SafetyViolationError(
            f"SAFETY VIOLATION: Target host '{host}' is NOT in the lab allowlist! "
            f"Only 127.0.0.1, localhost, and RFC 1918 private lab addresses are permitted."
        )


def assert_lab_url_allowlisted(url: str) -> None:
    """Refuses URLs that point outside allowlisted local lab targets."""
    parsed = urlparse(url)
    hostname = parsed.hostname or url
    if not is_target_allowlisted(hostname, allow_rfc1918=True):
        raise SafetyViolationError(
            f"SAFETY VIOLATION: Download URL '{url}' references non-allowlisted host '{hostname}'! "
            f"Only local lab URL placeholders are permitted."
        )


def build_ssh_command(
    host: str,
    port: int,
    username: str,
    command: Optional[str] = None,
    allocate_pty: bool = False,
) -> List[str]:
    """Constructs a non-interactive ssh command using standard OpenSSH client flags."""
    cmd = [
        "ssh",
        "-p", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=5",
    ]
    if allocate_pty:
        cmd.append("-tt")
    else:
        cmd.append("-T")

    cmd.append(f"{username}@{host}")
    if command:
        cmd.append(command)
    return cmd
