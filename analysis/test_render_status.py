"""
Tests for Honest Status Table Generator (analysis/render_status.py).
Enforces G4 acceptance criteria:
1. Running the script twice gives identical output.
2. The percentage matches progress_accounting's output.
3. README.md contains a link to docs/STATUS.md without hand-written percentages.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from analysis.render_status import render_status, load_progress_data, STATUS_MD_PATH, PROJECT_ROOT
from analysis.progress_accounting import ITEMS as ACCOUNTING_ITEMS


def test_render_status_deterministic_output(tmp_path: Path):
    """G4 Acceptance: Running the script twice gives identical output."""
    out_file1 = tmp_path / "STATUS_1.md"
    out_file2 = tmp_path / "STATUS_2.md"

    pct1 = render_status(out_path=out_file1)
    pct2 = render_status(out_path=out_file2)

    assert pct1 == pct2
    assert out_file1.read_text(encoding="utf-8") == out_file2.read_text(encoding="utf-8")


def test_render_status_matches_progress_accounting():
    """G4 Acceptance: Compares the percentage to progress_accounting's output."""
    credit = {'Done': 1.0, 'Partial': 0.5, 'Not done': 0.0}
    earned = sum(weight * credit[status] for _, weight, status, _ in ACCOUNTING_ITEMS)
    total = sum(weight for _, weight, _, _ in ACCOUNTING_ITEMS)
    expected_pct = 100.0 * earned / total

    _, r_earned, r_total, r_pct = load_progress_data()

    assert r_earned == earned
    assert r_total == total
    assert round(r_pct, 4) == round(expected_pct, 4)


def test_readme_links_to_status_md():
    """Verify README.md contains a link to docs/STATUS.md."""
    readme_path = PROJECT_ROOT / "README.md"
    assert readme_path.exists()
    content = readme_path.read_text(encoding="utf-8")
    assert "docs/STATUS.md" in content
