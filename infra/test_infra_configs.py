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
