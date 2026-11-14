"""Unit tests for analysis/astra2_report.py.

Verifies:
1. Dynamic P0/P1/P2/P3/P4 status derivation.
2. Permutation null warning triggered when observed_recall <= mean.
3. Frozen snapshot note for table_before_p0.csv (commit e2a8195).
4. Manifest generation: git dirty flag, recursive source scan, and MISSING handler.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pytest

from analysis.astra2_report import generate_report


@pytest.fixture
def mock_results_dir(tmp_path: Path) -> Path:
    """Creates a temporary results directory with mock artifacts."""
    results = tmp_path / "results" / "exp0"
    results.mkdir(parents=True)

    null_data = {
        "status": "COMPLETE",
        "observed_recall": 0.2919,
        "mean": 0.6491,
        "minimum": 0.6490,
        "maximum": 0.6495,
        "standard_deviation": 0.0001,
        "empirical_upper_tail_plus_one": 1.0,
        "permutations": [1, 2, 3],
        "seeds": [12345],
    }
    (results / "permutation_null.json").write_text(json.dumps(null_data), encoding="utf-8")

    rules_summary = {"gate0": {"S3": {"delta": 0.1768}}}
    (results / "rules_summary.json").write_text(json.dumps(rules_summary), encoding="utf-8")

    switch_data = {"passed": True}
    (results / "live_switch_proof.json").write_text(json.dumps(switch_data), encoding="utf-8")

    live_data = {"transcript_returncode": 0, "harness_limitation": "lab limitation"}
    (results / "live_sensor_proof.json").write_text(json.dumps(live_data), encoding="utf-8")

    study_data = {"status": "COMPLETE", "selection": ["day1"]}
    (results / "event_prefix_study.json").write_text(json.dumps(study_data), encoding="utf-8")

    for t in ["p0", "p2", "p3"]:
        (results / f"{t}_tests.json").write_text(
            json.dumps({"returncode": 0, "command": ["pytest"], "output": "1 passed"}),
            encoding="utf-8",
        )

    (results / "table_before_p0.csv").write_text(
        "stage,ml_test_recall,best_rule_test_recall,delta_k\nS3,0.2984,0.1151,0.1833\n",
        encoding="utf-8",
    )
    (results / "table.csv").write_text(
        "stage,ml_test_recall,best_rule_test_recall,delta_k\nS3,0.2919,0.1151,0.1768\n",
        encoding="utf-8",
    )

    return results


def test_dynamic_p0_status_with_null_warning(mock_results_dir: Path):
    """When observed recall <= null mean, P0 must evaluate to PARTLY and show warning."""
    report_text, manifest = generate_report(root=mock_results_dir, write=False)

    assert "P0: PARTLY" in report_text
    assert "> [!WARNING]" in report_text
    assert "Permutation null mean recall" in report_text
    assert "indistinguishable from label-shuffle noise" in report_text


def test_dynamic_p0_status_when_observed_exceeds_null(mock_results_dir: Path):
    """When observed recall > null mean and test passes, P0 evaluates to DONE without warning."""
    null_path = mock_results_dir / "permutation_null.json"
    data = json.loads(null_path.read_text(encoding="utf-8"))
    data["observed_recall"] = 0.8500  # Exceeds mean 0.6491
    null_path.write_text(json.dumps(data), encoding="utf-8")

    report_text, manifest = generate_report(root=mock_results_dir, write=False)

    assert "P0: DONE" in report_text
    assert "Permutation null mean recall" not in report_text


def test_dynamic_p1_p2_p3_p4_statuses(mock_results_dir: Path):
    """Verify statuses reflect mock results accurately."""
    report_text, manifest = generate_report(root=mock_results_dir, write=False)

    assert "P1: DONE" in report_text
    assert "P2: DONE" in report_text
    assert "P3: DONE" in report_text
    assert "P4: DONE" in report_text

    # Change P4 study status to PARTIAL
    study_path = mock_results_dir / "event_prefix_study.json"
    study_path.write_text(json.dumps({"status": "PARTIAL"}), encoding="utf-8")

    report_text_partly, _ = generate_report(root=mock_results_dir, write=False)
    assert "P4: PARTLY" in report_text_partly


def test_frozen_snapshot_reference(mock_results_dir: Path):
    """Verify report explicitly cites frozen snapshot commit e2a8195 for table_before_p0.csv."""
    report_text, _ = generate_report(root=mock_results_dir, write=False)
    assert "e2a8195" in report_text
    assert "table_before_p0.csv" in report_text


def test_manifest_contains_git_dirty_and_missing_handling(mock_results_dir: Path, tmp_path: Path):
    """Verify manifest records dirty flag and handles missing files with MISSING marker."""
    _, manifest = generate_report(root=mock_results_dir, write=False)

    assert "dirty" in manifest
    assert isinstance(manifest["dirty"], bool)
    assert "head" in manifest

    # Nonexistent models must be recorded with MISSING:
    assert any("MISSING: " in v for v in manifest["model_sha256"].values())
