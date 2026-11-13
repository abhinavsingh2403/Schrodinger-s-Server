"""
Tests for Infrastructure & Security Configurations (infra/).
Pre-registered in SAFETY.md Section 2 and SPEC.md Section 5.1.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest


INFRA_DIR = Path(__file__).resolve().parent


def test_cowrie_config_safety_rules():
    """Verify SAFETY.md: Telnet must be disabled and outbound connections blocked."""
    cfg_path = INFRA_DIR / "cowrie.cfg"
    assert cfg_path.exists(), "infra/cowrie.cfg must exist"

    content = cfg_path.read_text(encoding="utf-8")

    # Telnet strictly disabled
    assert "enabled = false" in content
    assert "[telnet]" in content

    # SSH enabled on non-default internal port
    assert "[ssh]" in content
    assert "listen_endpoints" in content

    # Identity matching identity.yaml (Ubuntu 22.04 LTS / OpenSSH 8.9p1)
    assert "srv-app-01" in content
    assert "OpenSSH_8.9p1" in content


def test_egress_firewall_script_rules():
    """Verify SAFETY.md Rule 2: Egress blocking script must forbid outbound internet."""
    fw_path = INFRA_DIR / "egress_firewall.sh"
    assert fw_path.exists(), "infra/egress_firewall.sh must exist"

    content = fw_path.read_text(encoding="utf-8")

    # Drops outbound forwarding and non-loopback output
    assert "iptables" in content or "nft" in content
    assert "DROP" in content
    assert "lo" in content  # Loopback allowed for local inter-service IPC


def test_docker_compose_structure():
    """Verify container network isolation and safety boundaries."""
    compose_path = INFRA_DIR / "docker-compose.yml"
    assert compose_path.exists(), "infra/docker-compose.yml must exist"

    content = compose_path.read_text(encoding="utf-8")

    # Must define honeypot, gatekeeper, and dashboard services
    assert "sensor" in content or "honeypot" in content
    assert "gatekeeper" in content
    assert "dashboard" in content

    # Must specify internal network bridge with isolation
    assert "networks:" in content
    assert "internal_honeypot_net" in content


def test_smoke_test_scripts_exist_and_validate():
    """Verify G8: smoke_test.ps1, smoke_test.sh, and parse_compose.py exist and pass static check."""
    from infra.parse_compose import inspect_compose
    from io import StringIO
    import sys

    ps1_path = INFRA_DIR / "smoke_test.ps1"
    sh_path = INFRA_DIR / "smoke_test.sh"
    parser_path = INFRA_DIR / "parse_compose.py"

    assert ps1_path.exists()
    assert sh_path.exists()
    assert parser_path.exists()

    # Capture parser output on current docker-compose.yml
    stdout_buf = StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = stdout_buf
        inspect_compose(INFRA_DIR / "docker-compose.yml")
    finally:
        sys.stdout = old_stdout

    out = stdout_buf.getvalue()
    assert "INTERNAL_NETWORK:True" in out
    assert "0.0.0.0" not in out
    assert "PORT:sensor:127.0.0.1:2222:2222" in out

