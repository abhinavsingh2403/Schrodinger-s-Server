"""
Bot-Like Attacker Scenario for Kali Linux Demo.
Spec: Connect, a few failed logins, one successful login, run at most 2 commands, disconnect.
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


def run_bot_like(
    host: str = "127.0.0.1",
    port: int = 2222,
    dry_run: bool = False,
    username: str = "root",
    password: str = "root",
) -> List[str]:
    """Executes the bot-like attacker scenario. Returns executed action log."""
    assert_lab_target_allowlisted(host)
    actions: List[str] = []

    # 1. Failed login attempts (brute force scanner simulation)
    failed_attempts = [("admin", "123456"), ("user", "password")]
    for u, p in failed_attempts:
        action_msg = f"[FAILED_LOGIN_ATTEMPT] user={u} pass=*** host={host}:{port}"
        actions.append(action_msg)
        if dry_run:
            print(f"[DRY-RUN] {action_msg}")
        else:
            # Simulate failed authentication probe via ssh with bad credentials
            cmd = build_ssh_command(host, port, u, command="exit")
            try:
                subprocess.run(cmd, capture_output=True, timeout=5)
            except Exception as e:
                actions.append(f"[ERROR] {e}")

    # 2. Successful login attempt
    succ_msg = f"[LOGIN_SUCCESS] user={username} host={host}:{port}"
    actions.append(succ_msg)
    if dry_run:
        print(f"[DRY-RUN] {succ_msg}")

    # 3. Run at most 2 automated commands (spec: run at most 2 commands)
    bot_commands = ["uname -a", "cat /proc/cpuinfo"]
    for c in bot_commands:
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

    # 4. Disconnect
    disc_msg = f"[DISCONNECT] Session closed gracefully for {host}:{port}"
    actions.append(disc_msg)
    if dry_run:
        print(f"[DRY-RUN] {disc_msg}")

    return actions


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot-Like Adversary Probe (Kali Demo)")
    parser.add_argument("--host", default="127.0.0.1", help="Target honeypot host (must be lab allowlisted)")
    parser.add_argument("--port", type=int, default=2222, help="Target honeypot SSH port")
    parser.add_argument("--username", default="root", help="Honeypot login username")
    parser.add_argument("--password", default="root", help="Honeypot login password")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without sending network traffic")
    args = parser.parse_args()

    run_bot_like(
        host=args.host,
        port=args.port,
        dry_run=args.dry_run,
        username=args.username,
        password=args.password,
    )


if __name__ == "__main__":
    main()
