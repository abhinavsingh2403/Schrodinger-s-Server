"""Common safety guards and execution helpers for adversary lab demo scripts.

Enforces SAFETY.md and AGENTS.md Rule 6:
- Only allowlisted lab targets (127.0.0.1, localhost, RFC 1918 private IPs) are permitted.
- Refuses any public IP, internet hostname, or unauthorized target.
- Executes SSH commands without leaking passwords into argv.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, List, Optional
from urllib.parse import urlparse

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
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


def execute_ssh_command(
    host: str,
    port: int,
    username: str,
    password: str,
    command: Optional[str] = None,
    allocate_pty: bool = False,
    timeout: float = 10.0,
) -> subprocess.CompletedProcess:
    """Executes SSH command securely without leaking password in argv.

    Uses sshpass -e (env variable SSHPASS) if installed, or an ephemeral SSH_ASKPASS script.
    """
    assert_lab_target_allowlisted(host)
    cmd = build_ssh_command(host, port, username, command=command, allocate_pty=allocate_pty)

    env = os.environ.copy()
    askpass_file: Optional[Path] = None

    if shutil.which("sshpass"):
        cmd = ["sshpass", "-e"] + cmd
        env["SSHPASS"] = password
    else:
        temp_fd, temp_path = tempfile.mkstemp(prefix="askpass_")
        askpass_file = Path(temp_path)
        with os.fdopen(temp_fd, "w") as f:
            if sys.platform == "win32":
                f.write(f"@echo {password}\n")
            else:
                f.write(f"#!/bin/sh\nprintf '%s\\n' '{password}'\n")
        try:
            askpass_file.chmod(0o700)
        except OSError:
            pass
        env["SSH_ASKPASS"] = str(askpass_file)
        env["SSH_ASKPASS_REQUIRE"] = "force"
        if "DISPLAY" not in env:
            env["DISPLAY"] = ":lab"

    try:
        return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    finally:
        if askpass_file and askpass_file.exists():
            try:
                askpass_file.unlink()
            except OSError:
                pass


class ScenarioResult(dict):
    """Holds scenario execution metadata, acts as a dict, and yields action strings when iterated."""

    def __init__(
        self,
        scenario: str,
        host: str,
        port: int,
        ok: bool,
        returncode: int,
        reason: str,
        actions: Optional[List[str]] = None,
    ):
        actions_list = actions or []
        super().__init__(
            scenario=scenario,
            host=host,
            port=port,
            ok=ok,
            returncode=returncode,
            reason=reason,
            actions=actions_list,
        )

    def __iter__(self):
        """Allows iterating over actions for backward compatibility with existing tests."""
        return iter(self.get("actions", []))

    def to_json_line(self) -> str:
        """Returns single-line JSON string without formatting/newlines."""
        summary = {
            "scenario": self["scenario"],
            "host": self["host"],
            "port": self["port"],
            "ok": self["ok"],
            "returncode": self["returncode"],
            "reason": self["reason"],
        }
        return json.dumps(summary)
