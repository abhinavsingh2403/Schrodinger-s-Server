"""Unit tests for sensor/run_sensor.py host allowlist enforcement.

Covers AGENTS.md Rule 6 (no connections outside the allowlist).
Enforces that sensor launcher only communicates with allowlisted loopback / gatekeeper targets.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch
import pytest

from sensor import run_sensor


class AllowlistPassed(Exception):
    """Sentinel exception raised after the host allowlist validation succeeds."""


ALLOWED_URL_CASES = [
    "http://127.0.0.1:5000",
    "http://localhost:5000",
    "http://gatekeeper:5000",
    "http://127.0.0.1",
    "http://localhost",
    "http://gatekeeper",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
    "http://gatekeeper:8080",
    "http://LOCALHOST:5000",
    "http://GateKeeper:5000",
]

REJECTED_URL_CASES = [
    # External and non-loopback domains / IPs
    "http://127.0.0.1.evil.com:5000",
    "http://evil.com:5000",
    "http://0.0.0.0:5000",
    "http://10.0.0.1:5000",
    "http://192.168.1.1:5000",
    # Empty string
    "",
    # IPv6 forms not in allowlist
    "http://[::1]:5000",
    "http://[::]:5000",
    "http://[fe80::1]:5000",
    # Trailing dot lookalikes
    "http://localhost.:5000",
    "http://gatekeeper.:5000",
    "http://127.0.0.1.:5000",
    # Subdomain lookalikes
    "http://localhost.evil.com:5000",
    "http://gatekeeper.evil.com:5000",
    "http://127.0.0.1.attacker.net:5000",
    # Mixed-case lookalikes targeting external domains
    "http://LocalHost.evil.com:5000",
    "http://GateKeeper.evil.com:5000",
    # Userinfo spoofing
    "http://gatekeeper@evil.com:5000",
    "http://localhost@evil.com:5000",
]


@pytest.mark.parametrize("url", ALLOWED_URL_CASES)
def test_host_allowlist_permits_allowed_targets(url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that legitimate loopback and container service targets pass validation."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_sensor", "--state-dir", str(tmp_path), "--gatekeeper-url", url],
    )
    # Intercept execution immediately after allowlist validation succeeds
    with patch("os.chdir", side_effect=AllowlistPassed):
        with patch.object(Path, "mkdir"):
            with pytest.raises(AllowlistPassed):
                run_sensor.main()


@pytest.mark.parametrize("url", REJECTED_URL_CASES)
def test_host_allowlist_rejects_forbidden_targets(
    url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify that non-allowlisted IPs, lookalikes, IPv6, and external domains are rejected with SystemExit(2)."""
    argv = ["run_sensor", "--state-dir", str(tmp_path)]
    if url != "":
        argv.extend(["--gatekeeper-url", url])
    else:
        argv.extend(["--gatekeeper-url="])

    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc_info:
        run_sensor.main()

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "This lab launcher only permits loopback (127.0.0.1/localhost) or gatekeeper container" in captured.err


def test_run_sensor_provenance_cli_default_lab(tmp_path: Path) -> None:
    """Verify run_sensor CLI defaults --provenance to LAB."""
    parser = run_sensor.make_parser()
    args = parser.parse_args(["--state-dir", str(tmp_path), "--gatekeeper-url", "http://127.0.0.1:5000"])
    assert args.provenance == "LAB"


def test_run_sensor_provenance_cli_live_rejected_until_vps_trial(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify run_sensor CLI rejects --provenance LIVE until the gated VPS trial."""
    parser = run_sensor.make_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--state-dir", str(tmp_path), "--gatekeeper-url", "http://127.0.0.1:5000", "--provenance", "LIVE"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice: 'LIVE'" in captured.err


def test_run_sensor_provenance_cli_invalid_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify run_sensor CLI rejects invalid --provenance with SystemExit(2)."""
    parser = run_sensor.make_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--state-dir", str(tmp_path), "--provenance", "FORGED"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice: 'FORGED'" in captured.err


def test_lifecycle_bridge_provenance_default_and_forwarding() -> None:
    """Verify LifecycleBridge defaults provenance to LAB and passes it to AdaptiveSessionAdapter."""
    bridge = run_sensor.LifecycleBridge(client=None)
    assert bridge.provenance == "LAB"

    # Simulate connect event
    event = {
        "eventid": "cowrie.session.connect",
        "session": "sess_bridge_test",
        "src_ip": "127.0.0.1",
    }
    bridge.event(event)
    assert "sess_bridge_test" in bridge.sessions
    adapter, _ = bridge.sessions["sess_bridge_test"]
    assert adapter.provenance == "LAB"

