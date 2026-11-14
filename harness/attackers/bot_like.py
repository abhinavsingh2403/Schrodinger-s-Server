"""Bot-Like Attacker Scenario for Kali Linux Demo.

Spec: Connect, a few failed logins, one successful login, run at most 2 commands, disconnect.
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


def run_bot_like(
    host: str = "127.0.0.1",
    port: int = 2222,
    dry_run: bool = False,
    username: str = "root",
    password: str = "root",
) -> ScenarioResult:
    """Executes the bot-like attacker scenario. Returns ScenarioResult."""
    assert_lab_target_allowlisted(host)
    actions: List[str] = []
    ok = True
    returncode = 0
    reason = "completed"

    if dry_run:
        failed_attempts = [("admin", "123456"), ("user", "password")]
        for u, _ in failed_attempts:
            action_msg = f"[FAILED_LOGIN_ATTEMPT] user={u} pass=*** host={host}:{port}"
            actions.append(action_msg)
            print(f"[DRY-RUN] {action_msg}")

        succ_msg = f"[LOGIN_SUCCESS] user={username} host={host}:{port}"
        actions.append(succ_msg)
        print(f"[DRY-RUN] {succ_msg}")

        bot_commands = ["uname -a", "cat /proc/cpuinfo"]
        for c in bot_commands:
            cmd_msg = f"[EXEC_COMMAND] {c}"
            actions.append(cmd_msg)
            print(f"[DRY-RUN] {cmd_msg}")

        disc_msg = f"[DISCONNECT] Session closed gracefully for {host}:{port}"
        actions.append(disc_msg)
        print(f"[DRY-RUN] {disc_msg}")

        return ScenarioResult("bot_like", host, port, ok=True, returncode=0, reason="dry-run", actions=actions)

    # 1. Failed login attempts (brute force scanner simulation)
    failed_attempts = [("admin", "123456"), ("user", "password")]
    for u, p in failed_attempts:
        action_msg = f"[FAILED_LOGIN_ATTEMPT] user={u} pass=*** host={host}:{port}"
        actions.append(action_msg)
        res = execute_ssh_command(host, port, u, password=p, command="exit")
        # In failed attempts, exit code 255 or 1 is normal auth rejection

    # 2. Successful login attempt
    succ_msg = f"[LOGIN_SUCCESS] user={username} host={host}:{port}"
    actions.append(succ_msg)
    res = execute_ssh_command(host, port, username, password=password, command="exit")
    if res.returncode == 255:
        ok = False
        returncode = 255
        reason = f"Authentication or connection failed with code 255: {res.stderr.strip()}"
        actions.append(f"[ERROR] {reason}")
        return ScenarioResult("bot_like", host, port, ok=ok, returncode=returncode, reason=reason, actions=actions)

    # 3. Run at most 2 automated commands
    bot_commands = ["uname -a", "cat /proc/cpuinfo"]
    for c in bot_commands:
        cmd_msg = f"[EXEC_COMMAND] {c}"
        actions.append(cmd_msg)
        res = execute_ssh_command(host, port, username, password=password, command=c)
        if res.returncode == 255:
            ok = False
            returncode = 255
            reason = f"Command '{c}' failed with SSH code 255: {res.stderr.strip()}"
            actions.append(f"[ERROR] {reason}")
            break

    # 4. Disconnect
    disc_msg = f"[DISCONNECT] Session closed gracefully for {host}:{port}"
    actions.append(disc_msg)

    return ScenarioResult("bot_like", host, port, ok=ok, returncode=returncode, reason=reason, actions=actions)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot-Like Adversary Probe (Kali Demo)")
    parser.add_argument("--host", default="127.0.0.1", help="Target honeypot host (must be lab allowlisted)")
    parser.add_argument("--port", type=int, default=2222, help="Target honeypot SSH port")
    parser.add_argument("--username", default="root", help="Honeypot login username")
    parser.add_argument("--password", default="root", help="Honeypot login password")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without sending network traffic")
    args = parser.parse_args()

    result = run_bot_like(
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
