"""Tests for analysis/verify_download.py."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from analysis.verify_download import compute_md5, main, verify_file


def test_compute_md5_and_verify_match(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    test_file = tmp_path / "sample.bin"
    content = b"Schrodinger's Server test payload for streaming verification."
    test_file.write_bytes(content)

    expected_md5 = hashlib.md5(content).hexdigest()

    # Function check
    assert compute_md5(test_file) == expected_md5
    is_match, computed = verify_file(test_file, expected_md5)
    assert is_match is True
    assert computed == expected_md5

    # CLI check - match
    exit_code = main([str(test_file), expected_md5])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "MATCH" in captured.out
    assert computed in captured.out


def test_verify_mismatch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    test_file = tmp_path / "mismatch.bin"
    test_file.write_bytes(b"content A")

    real_md5 = hashlib.md5(b"content A").hexdigest()
    wrong_md5 = "00000000000000000000000000000000"

    is_match, computed = verify_file(test_file, wrong_md5)
    assert is_match is False
    assert computed == real_md5

    # CLI check - mismatch
    exit_code = main([str(test_file), wrong_md5])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "MISMATCH" in captured.out
    assert wrong_md5 in captured.out
    assert real_md5 in captured.out


def test_verify_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    nonexistent = tmp_path / "does_not_exist.bin"
    exit_code = main([str(nonexistent), "00000000000000000000000000000000"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "ERROR" in captured.err
