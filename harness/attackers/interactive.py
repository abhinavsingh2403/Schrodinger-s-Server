"""
Interactive Attacker Scenario for Kali Linux Demo.
Spec: Login, request a PTY, run 6 or more varied benign commands (ls, uname -a, cat /etc/passwd, id, whoami, ps), disconnect.
Safety: Refuses non-allowlisted targets before attempting any connection.
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

from harness.attackers.common import assert_lab_target_allowlisted, build_ssh_command

INTERACTIVE_COMMANDS = [
    "uname -a",
    "id",
    "whoami",
    "cat /etc/passwd",
    "ls -la",
    "ps aux",
]


def run_interactive(
    host: str = "127.0.0.1",
    port: int = 2222,
    dry_run: bool = False,
    username: str = "root",
    password: str = "root",
) -> List[str]:
    """Executes the interactive reconnaissance scenario with PTY allocation."""
    assert_lab_target_allowlisted(host)
    actions: List[str] = []

    # 1. Login with pseudo-terminal allocation request
    pty_msg = f"[LOGIN_PTY_REQUESTED] user={username} host={host}:{port} pty=true"
    actions.append(pty_msg)
    if dry_run:
        print(f"[DRY-RUN] {pty_msg}")

    # 2. Run 6 or more varied benign commands
    for c in INTERACTIVE_COMMANDS:
        cmd_msg = f"[EXEC_PTY_COMMAND] {c}"
        actions.append(cmd_msg)
        if dry_run:
            print(f"[DRY-RUN] {cmd_msg}")
        else:
            cmd = build_ssh_command(host, port, username, command=c, allocate_pty=True)
            try:
                subprocess.run(cmd, capture_output=True, timeout=5)
            except Exception as e:
                actions.append(f"[ERROR] {e}")

    # 3. Disconnect
    disc_msg = f"[DISCONNECT] Interactive PTY session closed gracefully for {host}:{port}"
    actions.append(disc_msg)
    if dry_run:
        print(f"[DRY-RUN] {disc_msg}")

    return actions


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive Recon Adversary Probe (Kali Demo)")
    parser.add_argument("--host", default="127.0.0.1", help="Target honeypot host (must be lab allowlisted)")
    parser.add_argument("--port", type=int, default=2222, help="Target honeypot SSH port")
    parser.add_argument("--username", default="root", help="Honeypot login username")
    parser.add_argument("--password", default="root", help="Honeypot login password")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without sending network traffic")
    args = parser.parse_args()

    run_interactive(
        host=args.host,
        port=args.port,
        dry_run=args.dry_run,
        username=args.username,
        password=args.password,
    )


if __name__ == "__main__":
    main()
