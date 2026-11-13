"""
Tests for Documentation Link and Claim Checker (analysis/check_docs.py).
Enforces G11 acceptance criteria.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import pytest

from analysis.check_docs import check_file, scan_all_docs, PROJECT_ROOT


def test_check_docs_detects_broken_link(tmp_path: Path):
    """Verify check_docs flags markdown links to nonexistent targets."""
    md_file = tmp_path / "test_doc.md"
    md_file.write_text("[Broken Link](nonexistent_target.md)\n", encoding="utf-8")

    hits = check_file(md_file)
    broken = [h for h in hits if h["category"] == "broken_link"]
    assert len(broken) == 1
    assert "nonexistent_target.md" in broken[0]["message"]


def test_check_docs_detects_absolute_path(tmp_path: Path):
    """Verify check_docs flags absolute Windows paths."""
    md_file = tmp_path / "test_doc.md"
    md_file.write_text("Refer to `C:\\Users\\test\\file.txt` or file:///C:/repo/doc.md\n", encoding="utf-8")

    hits = check_file(md_file)
    abs_hits = [h for h in hits if h["category"] == "absolute_path"]
    assert len(abs_hits) >= 1
    assert "Absolute Windows path" in abs_hits[0]["message"]


def test_check_docs_detects_forbidden_claims(tmp_path: Path):
    """Verify check_docs flags disallowed phrases like '100% complete' or 'flawless'."""
    md_file = tmp_path / "test_doc.md"
    md_file.write_text("The implementation is 100% complete, flawless, and perfect.\n", encoding="utf-8")

    hits = check_file(md_file)
    claim_hits = [h for h in hits if h["category"] == "disallowed_claim"]
    assert len(claim_hits) >= 3
    phrases = [h["message"] for h in claim_hits]
    assert any("100% complete" in m for m in phrases)
    assert any("flawless" in m for m in phrases)
    assert any("perfect" in m for m in phrases)


def test_repo_has_zero_broken_links_and_zero_absolute_paths():
    """Verify the repository documentation contains zero broken links and zero absolute paths."""
    hits = scan_all_docs(PROJECT_ROOT)
    broken_links = [h for h in hits if h["category"] == "broken_link"]
    abs_paths = [h for h in hits if h["category"] == "absolute_path"]

    assert len(broken_links) == 0, f"Found broken links in repo: {broken_links}"
    assert len(abs_paths) == 0, f"Found absolute paths in repo: {abs_paths}"


def test_check_docs_cli():
    """Verify running check_docs.py CLI succeeds with exit code 0 on clean links and paths."""
    res = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "analysis" / "check_docs.py")],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert res.returncode == 0
    assert "Verification PASSED" in res.stdout
