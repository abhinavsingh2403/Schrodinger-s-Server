"""
Tests for Spike S1: Per-session persona switching in Cowrie after login.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Ensure paths
COWRIE_ROOT = Path(__file__).resolve().parent / "cowrie-src"
sys.path.insert(0, str(COWRIE_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import types
if "cowrie._version" not in sys.modules:
    m = types.ModuleType("cowrie._version")
    m.__version__ = "3.1.6"
    m.version = "3.1.6"
    sys.modules["cowrie._version"] = m

from spike_s1_poc import run_command_in_session


def test_odd_port_assigns_persona_1():
    with tempfile.TemporaryDirectory() as tmp_dir:
        p1_dir = os.path.join(tmp_dir, "persona1")
        p2_dir = os.path.join(tmp_dir, "persona2")
        os.makedirs(os.path.join(p1_dir, "etc"), exist_ok=True)
        os.makedirs(os.path.join(p2_dir, "etc"), exist_ok=True)
        with open(os.path.join(p1_dir, "etc", "motd"), "w") as f:
            f.write("Welcome to Ubuntu 22.04 LTS (Web Cluster Node 1)\n")
        with open(os.path.join(p2_dir, "etc", "motd"), "w") as f:
            f.write("Welcome to Debian GNU/Linux 12 (Minimal Sensor)\n")

        res_host = run_command_in_session(54321, b"hostname", p1_dir, p2_dir)
        res_cat = run_command_in_session(54321, b"cat /etc/persona", p1_dir, p2_dir)
        res_motd = run_command_in_session(54321, b"cat /etc/motd", p1_dir, p2_dir)

        assert res_host["persona"] == "Persona 1 (T2 Web Server)"
        assert res_host["output"].strip() == "web-srv-01"
        assert "PERSONA_1" in res_cat["output"]
        assert "Ubuntu" in res_motd["output"]


def test_even_port_assigns_persona_2():
    with tempfile.TemporaryDirectory() as tmp_dir:
        p1_dir = os.path.join(tmp_dir, "persona1")
        p2_dir = os.path.join(tmp_dir, "persona2")
        os.makedirs(os.path.join(p1_dir, "etc"), exist_ok=True)
        os.makedirs(os.path.join(p2_dir, "etc"), exist_ok=True)
        with open(os.path.join(p1_dir, "etc", "motd"), "w") as f:
            f.write("Welcome to Ubuntu 22.04 LTS (Web Cluster Node 1)\n")
        with open(os.path.join(p2_dir, "etc", "motd"), "w") as f:
            f.write("Welcome to Debian GNU/Linux 12 (Minimal Sensor)\n")

        res_host = run_command_in_session(54322, b"hostname", p1_dir, p2_dir)
        res_cat = run_command_in_session(54322, b"cat /etc/persona", p1_dir, p2_dir)
        res_motd = run_command_in_session(54322, b"cat /etc/motd", p1_dir, p2_dir)

        assert res_host["persona"] == "Persona 2 (T1 Generic Server)"
        assert res_host["output"].strip() == "generic-srv-02"
        assert "PERSONA_2" in res_cat["output"]
        assert "Debian" in res_motd["output"]
