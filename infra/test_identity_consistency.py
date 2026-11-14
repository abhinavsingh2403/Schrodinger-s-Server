"""Tests for Cross-Tier System Identity Consistency (SPEC Section 5.1 & Risk R8).

Verifies:
1. Exact equality between config/identity.yaml and sensor/identity.yaml.
2. Alignment between infra/cowrie.cfg and identity profile (Debian 12 / OpenSSH 9.2p1).
3. HoneyFS personality files in sensor/honeyfs/etc/ match Debian 12 / srv-app-01.
4. Total absence of 'Ubuntu' in identity files, cowrie.cfg, and honeyfs.
5. Deterministic generation by sensor/build_honeyfs.py.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

import pytest

from sensor.build_honeyfs import build_honeyfs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_IDENTITY = PROJECT_ROOT / "config" / "identity.yaml"
SENSOR_IDENTITY = PROJECT_ROOT / "sensor" / "identity.yaml"
COWRIE_CFG = PROJECT_ROOT / "infra" / "cowrie.cfg"
HONEYFS_DIR = PROJECT_ROOT / "sensor" / "honeyfs"


def test_identity_files_exist_and_match():
    """Verify config/identity.yaml and sensor/identity.yaml exist and have identical content."""
    assert CONFIG_IDENTITY.is_file(), f"Missing {CONFIG_IDENTITY}"
    assert SENSOR_IDENTITY.is_file(), f"Missing {SENSOR_IDENTITY}"

    cfg_text = CONFIG_IDENTITY.read_text(encoding="utf-8")
    sensor_text = SENSOR_IDENTITY.read_text(encoding="utf-8")

    assert cfg_text == sensor_text, "config/identity.yaml and sensor/identity.yaml must be identical"
    assert "Debian" in cfg_text
    assert "12 (bookworm)" in cfg_text
    assert "srv-app-01" in cfg_text
    assert "SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u3" in cfg_text


def test_cowrie_cfg_matches_identity():
    """Verify infra/cowrie.cfg aligns with the Debian 12 identity profile."""
    assert COWRIE_CFG.is_file(), f"Missing {COWRIE_CFG}"
    content = COWRIE_CFG.read_text(encoding="utf-8")

    assert "hostname = srv-app-01" in content
    assert "contents_path = /cowrie/honeyfs" in content
    assert "kernel_version = 6.1.0-21-amd64" in content
    assert "kernel_build_string = #1 SMP PREEMPT_DYNAMIC Debian 6.1.90-1 (2024-05-03)" in content
    assert "hardware_platform = x86_64" in content
    assert "operating_system = GNU/Linux" in content
    assert "version = SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u3" in content
    assert "reported_ssh_version" not in content, "Invalid key reported_ssh_version must be removed"


def test_honeyfs_personality_files():
    """Verify HoneyFS contains correct Debian 12 identity files."""
    etc_dir = HONEYFS_DIR / "etc"
    assert etc_dir.is_dir(), f"Missing HoneyFS etc directory at {etc_dir}"

    os_release = etc_dir / "os-release"
    assert os_release.is_file()
    os_rel_text = os_release.read_text(encoding="utf-8")
    assert 'PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"' in os_rel_text
    assert 'ID=debian' in os_rel_text
    assert 'VERSION_ID="12"' in os_rel_text

    issue = etc_dir / "issue"
    assert issue.is_file()
    assert "Debian GNU/Linux 12 \\n \\l" in issue.read_text(encoding="utf-8")

    issue_net = etc_dir / "issue.net"
    assert issue_net.is_file()
    assert "Debian GNU/Linux 12" in issue_net.read_text(encoding="utf-8")

    hostname = etc_dir / "hostname"
    assert hostname.is_file()
    assert "srv-app-01" in hostname.read_text(encoding="utf-8")

    motd = etc_dir / "motd"
    assert motd.is_file()
    motd_text = motd.read_text(encoding="utf-8")
    assert "Debian GNU/Linux" in motd_text


def test_zero_ubuntu_occurrences():
    """Verify total absence of 'Ubuntu' in identity files, cowrie.cfg, and HoneyFS."""
    targets = [
        CONFIG_IDENTITY,
        SENSOR_IDENTITY,
        COWRIE_CFG,
    ]
    if HONEYFS_DIR.is_dir():
        for root, _, files in os.walk(HONEYFS_DIR):
            for f in files:
                targets.append(Path(root) / f)

    for path in targets:
        assert path.is_file(), f"Target file {path} does not exist"
        text = path.read_text(encoding="utf-8")
        assert "ubuntu" not in text.lower(), f"Forbidden string 'Ubuntu' found in {path}"


def test_honeyfs_deterministic_build():
    """Verify build_honeyfs produces deterministic byte-for-byte output."""
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        out1 = build_honeyfs(tmp1)
        out2 = build_honeyfs(tmp2)

        assert sorted(out1.keys()) == sorted(out2.keys())
        for k in out1:
            bytes1 = out1[k].read_bytes()
            bytes2 = out2[k].read_bytes()
            assert bytes1 == bytes2, f"HoneyFS output for {k} is non-deterministic"
