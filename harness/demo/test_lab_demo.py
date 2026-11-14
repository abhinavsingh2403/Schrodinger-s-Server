"""Unit tests for harness/demo/run_lab_demo.sh.

Verifies:
1. --dry-run executes cleanly without starting network services or attacker processes.
2. Refusal of non-loopback target hosts (defense in depth).
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "harness" / "demo" / "run_lab_demo.sh"


@pytest.fixture
def bash_executable() -> str:
    """Find bash executable or skip if unavailable."""
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash executable not found in PATH")
    return bash


def test_script_exists() -> None:
    assert SCRIPT_PATH.is_file(), f"Expected script at {SCRIPT_PATH}"


def test_dry_run_execution(bash_executable: str) -> None:
    """Asserts that --dry-run exits 0 and describes all three demo scenarios."""
    result = subprocess.run(
        [bash_executable, "harness/demo/run_lab_demo.sh", "--dry-run"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Dry-run failed: {result.stderr}"
    assert "[DRY-RUN] Validated target host: 127.0.0.1:2222" in result.stdout
    assert "bot_like" in result.stdout
    assert "interactive" in result.stdout
    assert "transfer_like" in result.stdout


def test_refuse_non_loopback_host(bash_executable: str) -> None:
    """Asserts that script refuses non-loopback IP addresses."""
    for bad_host in ["8.8.8.8", "192.168.1.1", "example.com"]:
        result = subprocess.run(
            [bash_executable, "harness/demo/run_lab_demo.sh", "--host", bad_host],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0, f"Expected non-zero exit for bad host {bad_host}"
        assert "SAFETY ERROR: Refusing non-loopback host" in result.stderr


def test_refuse_non_loopback_host_with_dry_run(bash_executable: str) -> None:
    """Asserts that script refuses non-loopback IP addresses even when --dry-run is specified."""
    result = subprocess.run(
        [bash_executable, "harness/demo/run_lab_demo.sh", "--dry-run", "--host", "10.0.0.1"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "SAFETY ERROR: Refusing non-loopback host" in result.stderr
