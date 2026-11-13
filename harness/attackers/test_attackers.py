"""
Tests for Adversary Lab Attacker Scenarios (harness/attackers/).
Enforces G6 acceptance criteria:
1. Allowlist safety guard refuses public IPs and external URLs.
2. Accepts 127.0.0.1, localhost, and RFC1918 private lab addresses.
3. --dry-run runs deterministically in tests without network access.
"""

from __future__ import annotations

import pytest

from harness.detector_runner import SafetyViolationError
from harness.attackers.common import (
    assert_lab_target_allowlisted,
    assert_lab_url_allowlisted,
    build_ssh_command,
)
from harness.attackers.bot_like import run_bot_like
from harness.attackers.transfer_like import run_transfer_like
from harness.attackers.interactive import run_interactive, INTERACTIVE_COMMANDS


def test_safety_guard_refuses_public_ip():
    """G6 Acceptance: Public IP and internet domains must be refused immediately."""
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
    """G6 Acceptance: Localhost and RFC1918 private subnets are permitted."""
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
        # Should not raise any SafetyViolationError
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
    actions = run_bot_like(host="127.0.0.1", port=2222, dry_run=True)
    assert any("[FAILED_LOGIN_ATTEMPT]" in a for a in actions)
    assert any("[LOGIN_SUCCESS]" in a for a in actions)
    assert any("[DISCONNECT]" in a for a in actions)

    command_actions = [a for a in actions if "[EXEC_COMMAND]" in a]
    assert 1 <= len(command_actions) <= 2, "Bot-like scenario must run at most 2 commands"


def test_transfer_like_dry_run():
    """Verify transfer_like scenario runs in dry-run with local lab URL."""
    actions = run_transfer_like(
        host="127.0.0.1",
        port=2222,
        url="http://127.0.0.1:8000/sample.bin",
        dry_run=True,
    )
    assert any("[LOGIN_SUCCESS]" in a for a in actions)
    assert any("wget -q" in a for a in actions)
    assert any("[DISCONNECT]" in a for a in actions)

    # Refuses public URL even with dry_run
    with pytest.raises(SafetyViolationError):
        run_transfer_like(host="127.0.0.1", url="http://evil.com/x.sh", dry_run=True)


def test_interactive_dry_run():
    """Verify interactive scenario runs in dry-run with PTY and >= 6 benign recon commands."""
    actions = run_interactive(host="127.0.0.1", port=2222, dry_run=True)
    assert any("[LOGIN_PTY_REQUESTED]" in a for a in actions)
    assert any("[DISCONNECT]" in a for a in actions)

    command_actions = [a for a in actions if "[EXEC_PTY_COMMAND]" in a]
    assert len(command_actions) >= 6, f"Interactive scenario must run at least 6 commands, got {len(command_actions)}"

    # Ensure classic recon commands are present
    action_text = " ".join(actions)
    for cmd in ["uname -a", "id", "whoami", "cat /etc/passwd", "ls -la", "ps aux"]:
        assert cmd in action_text, f"Missing recon command '{cmd}' in interactive scenario"
