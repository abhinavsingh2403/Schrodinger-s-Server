"""Interactive Attacker Scenario for Kali Linux Demo.

Spec: Login, request a PTY, run 6 or more varied benign commands (ls, uname -a, cat /etc/passwd, id, whoami, ps), disconnect.
Safety: Refuses non-allowlisted targets before attempting any connection.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.attackers.common import (
    assert_lab_target_allowlisted,
    execute_ssh_command,
    ScenarioResult,
)

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
) -> ScenarioResult:
    """Executes the interactive reconnaissance scenario with PTY allocation."""
    assert_lab_target_allowlisted(host)
    actions: List[str] = []
    ok = True
    returncode = 0
    reason = "completed"

    if dry_run:
        pty_msg = f"[LOGIN_PTY_REQUESTED] user={username} host={host}:{port} pty=true"
        actions.append(pty_msg)
        print(f"[DRY-RUN] {pty_msg}")

        for c in INTERACTIVE_COMMANDS:
            cmd_msg = f"[EXEC_PTY_COMMAND] {c}"
            actions.append(cmd_msg)
            print(f"[DRY-RUN] {cmd_msg}")

        disc_msg = f"[DISCONNECT] Interactive shell terminated gracefully for {host}:{port}"
        actions.append(disc_msg)
        print(f"[DRY-RUN] {disc_msg}")

        return ScenarioResult("interactive", host, port, ok=True, returncode=0, reason="dry-run", actions=actions)

    pty_msg = f"[LOGIN_PTY_REQUESTED] user={username} host={host}:{port} pty=true"
    actions.append(pty_msg)

    for c in INTERACTIVE_COMMANDS:
        cmd_msg = f"[EXEC_PTY_COMMAND] {c}"
        actions.append(cmd_msg)
        res = execute_ssh_command(host, port, username, password=password, command=c, allocate_pty=True)
        if res.returncode == 255:
            ok = False
            returncode = 255
            reason = f"Command '{c}' failed with SSH code 255: {res.stderr.strip()}"
            actions.append(f"[ERROR] {reason}")
            break

    disc_msg = f"[DISCONNECT] Interactive shell terminated gracefully for {host}:{port}"
    actions.append(disc_msg)

    return ScenarioResult("interactive", host, port, ok=ok, returncode=returncode, reason=reason, actions=actions)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive Adversary Reconnaissance (Kali Demo)")
    parser.add_argument("--host", default="127.0.0.1", help="Target honeypot host (must be lab allowlisted)")
    parser.add_argument("--port", type=int, default=2222, help="Target honeypot SSH port")
    parser.add_argument("--username", default="root", help="Honeypot login username")
    parser.add_argument("--password", default="root", help="Honeypot login password")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without sending network traffic")
    args = parser.parse_args()

    result = run_interactive(
        host=args.host,
        port=args.port,
        dry_run=args.dry_run,
        username=args.username,
        password=args.password,
    )
    print(result.to_json_line())
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
