"""Tests for Adversary Lab Attacker Scenarios (harness/attackers/).

Enforces G6 and Task 2 acceptance criteria:
1. Allowlist safety guard refuses public IPs and external URLs.
2. Accepts 127.0.0.1, localhost, and RFC1918 private lab addresses.
3. Password handling does not leak passwords into argv.
4. Detection of OpenSSH returncode 255 errors.
5. Deterministic --dry-run and valid single-line JSON output.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from harness.detector_runner import SafetyViolationError
from harness.attackers.common import (
    assert_lab_target_allowlisted,
    assert_lab_url_allowlisted,
    build_ssh_command,
    execute_ssh_command,
    ScenarioResult,
)
from harness.attackers.bot_like import run_bot_like
from harness.attackers.transfer_like import run_transfer_like
from harness.attackers.interactive import run_interactive, INTERACTIVE_COMMANDS


def test_safety_guard_refuses_public_ip():
    """Public IP and internet domains must be refused immediately."""
    unauthorized_targets = [
        "8.8.8.8",
        "1.1.1.1",
        "93.184.216.34",
        "142.250.190.46",
        "scanme.nmap.org",
        "evil-honeypot.com",
    ]
    for target in unauthorized_targets:
        with pytest.raises(SafetyViolationError) as exc_info:
            assert_lab_target_allowlisted(target)
        assert "NOT in the lab allowlist" in str(exc_info.value)


def test_safety_guard_accepts_lab_allowlist():
    """Localhost and RFC1918 private subnets are permitted."""
    allowed_targets = [
        "127.0.0.1",
        "localhost",
        "::1",
        "10.0.0.1",
        "10.254.1.99",
        "172.16.0.1",
        "172.31.255.254",
        "192.168.1.1",
        "192.168.100.50",
    ]
    for target in allowed_targets:
        assert_lab_target_allowlisted(target)


def test_url_safety_guard():
    """Verify that external download URLs are refused by transfer_like safety check."""
    public_urls = [
        "http://malware.com/drop.sh",
        "https://8.8.8.8/x.bin",
        "http://c2.evil.org/miner",
    ]
    for url in public_urls:
        with pytest.raises(SafetyViolationError):
            assert_lab_url_allowlisted(url)

    allowed_urls = [
        "http://127.0.0.1:8000/sample.bin",
        "http://localhost:8080/file.txt",
        "http://192.168.1.50/payload.bin",
        "http://10.0.0.2:9000/test.tar",
    ]
    for url in allowed_urls:
        assert_lab_url_allowlisted(url)


def test_bot_like_dry_run():
    """Verify bot_like scenario runs in dry-run without network and obeys 2-command ceiling."""
    result = run_bot_like(host="127.0.0.1", port=2222, dry_run=True)
    assert result["ok"] is True
    actions = result["actions"]
    assert any("[FAILED_LOGIN_ATTEMPT]" in a for a in actions)
    assert any("[LOGIN_SUCCESS]" in a for a in actions)
    assert any("[DISCONNECT]" in a for a in actions)

    command_actions = [a for a in actions if "[EXEC_COMMAND]" in a]
    assert 1 <= len(command_actions) <= 2, "Bot-like scenario must run at most 2 commands"


def test_transfer_like_dry_run():
    """Verify transfer_like scenario runs in dry-run with local lab URL."""
    result = run_transfer_like(
        host="127.0.0.1",
        port=2222,
        url="http://127.0.0.1:8000/sample.bin",
        dry_run=True,
    )
    assert result["ok"] is True
    actions = result["actions"]
    assert any("[LOGIN_SUCCESS]" in a for a in actions)
    assert any("wget -q" in a for a in actions)
    assert any("[DISCONNECT]" in a for a in actions)

    with pytest.raises(SafetyViolationError):
        run_transfer_like(host="127.0.0.1", url="http://evil.com/x.sh", dry_run=True)


def test_interactive_dry_run():
    """Verify interactive scenario runs in dry-run with PTY and >= 6 benign recon commands."""
    result = run_interactive(host="127.0.0.1", port=2222, dry_run=True)
    assert result["ok"] is True
    actions = result["actions"]
    assert any("[LOGIN_PTY_REQUESTED]" in a for a in actions)
    assert any("[DISCONNECT]" in a for a in actions)

    command_actions = [a for a in actions if "[EXEC_PTY_COMMAND]" in a]
    assert len(command_actions) >= 6

    action_text = " ".join(actions)
    for cmd in ["uname -a", "id", "whoami", "cat /etc/passwd", "ls -la", "ps aux"]:
        assert cmd in action_text, f"Missing recon command '{cmd}' in interactive scenario"


def test_password_never_leaks_into_argv(monkeypatch: pytest.MonkeyPatch):
    """Verify password argument never appears in subprocess argv."""
    captured_calls = []

    def mock_subprocess_run(cmd, **kwargs):
        captured_calls.append({"cmd": cmd, "env": kwargs.get("env", {})})
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    secret = "SuperSecretPassword123!"
    execute_ssh_command("127.0.0.1", 2222, "root", secret, command="uname -a")

    assert len(captured_calls) == 1
    executed_cmd = captured_calls[0]["cmd"]
    env = captured_calls[0]["env"]

    # Password must NEVER appear in the command arguments
    for arg in executed_cmd:
        assert secret not in arg, f"Password leaked into argv: {arg}"

    # Either SSHPASS or SSH_ASKPASS must be configured in env
    assert "SSHPASS" in env or "SSH_ASKPASS" in env


def test_error_detection_on_returncode_255(monkeypatch: pytest.MonkeyPatch):
    """Verify scenarios detect SSH connection/authentication failure on returncode 255."""

    def mock_failing_ssh(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["ssh"],
            returncode=255,
            stdout="",
            stderr="ssh: connect to host 127.0.0.1 port 2222: Connection refused",
        )

    monkeypatch.setattr("harness.attackers.bot_like.execute_ssh_command", mock_failing_ssh)
    monkeypatch.setattr("harness.attackers.interactive.execute_ssh_command", mock_failing_ssh)
    monkeypatch.setattr("harness.attackers.transfer_like.execute_ssh_command", mock_failing_ssh)

    bot_res = run_bot_like(host="127.0.0.1", port=2222, dry_run=False)
    assert bot_res["ok"] is False
    assert bot_res["returncode"] == 255
    assert "255" in bot_res["reason"]

    inter_res = run_interactive(host="127.0.0.1", port=2222, dry_run=False)
    assert inter_res["ok"] is False
    assert inter_res["returncode"] == 255
    assert "255" in inter_res["reason"]

    trans_res = run_transfer_like(host="127.0.0.1", port=2222, dry_run=False)
    assert trans_res["ok"] is False
    assert trans_res["returncode"] == 255
    assert "255" in trans_res["reason"]


def test_scenario_result_json_line():
    """Verify ScenarioResult outputs a single JSON line without newlines."""
    res = ScenarioResult(
        scenario="bot_like",
        host="127.0.0.1",
        port=2222,
        ok=True,
        returncode=0,
        reason="completed",
        actions=["[LOGIN_SUCCESS]", "[EXEC_COMMAND]"],
    )
    json_line = res.to_json_line()
    assert "\n" not in json_line
    parsed = json.loads(json_line)
    assert parsed["scenario"] == "bot_like"
    assert parsed["ok"] is True
    assert parsed["returncode"] == 0
    assert parsed["host"] == "127.0.0.1"
