"""
Unit tests for Experiment 0 temporal and IP split logic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analysis.exp0_splits import (
    DEFAULT_SEED,
    generate_day_splits,
    save_splits_json,
    verify_ip_grouping,
)


@pytest.fixture
def dummy_52_days() -> list[str]:
    # 52 sequential dates
    return [f"2025-07-{i:02d}" for i in range(1, 32)] + [f"2025-08-{i:02d}" for i in range(1, 22)]


def test_split_sizes_and_ranges(dummy_52_days: list[str]) -> None:
    splits = generate_day_splits(dummy_52_days, seed=42)

    assert len(splits["train"]) == 5
    assert len(splits["validation"]) == 2
    assert len(splits["test"]) == 2

    period_train = set(dummy_52_days[:35])
    period_val = set(dummy_52_days[35:42])
    period_test = set(dummy_52_days[42:50])

    for day in splits["train"]:
        assert day in period_train
    for day in splits["validation"]:
        assert day in period_val
    for day in splits["test"]:
        assert day in period_test


def test_split_determinism(dummy_52_days: list[str]) -> None:
    s1 = generate_day_splits(dummy_52_days, seed=12345)
    s2 = generate_day_splits(dummy_52_days, seed=12345)
    s3 = generate_day_splits(dummy_52_days, seed=99999)

    assert s1 == s2
    assert s1 != s3


def test_insufficient_days_raises_error() -> None:
    with pytest.raises(ValueError, match="Expected at least 50 continuous days"):
        generate_day_splits(["2025-07-01", "2025-07-02"])


def test_verify_ip_grouping_clean() -> None:
    train_ips = {"1.1.1.1", "1.1.1.2"}
    val_ips = {"2.2.2.1", "2.2.2.2"}
    test_ips = {"3.3.3.1", "3.3.3.2"}

    assert verify_ip_grouping(train_ips, val_ips, test_ips) is True


def test_verify_ip_grouping_leakage_detected() -> None:
    train_ips = {"1.1.1.1", "1.1.1.2", "LEAK_IP"}
    val_ips = {"2.2.2.1", "2.2.2.2"}
    test_ips = {"3.3.3.1", "LEAK_IP"}

    with pytest.raises(ValueError, match="IP leakage detected"):
        verify_ip_grouping(train_ips, val_ips, test_ips)


def test_save_and_load_splits(tmp_path: Path, dummy_52_days: list[str]) -> None:
    splits = generate_day_splits(dummy_52_days, seed=DEFAULT_SEED)
    out_file = tmp_path / "splits.json"

    save_splits_json(splits, out_file, seed=DEFAULT_SEED, metadata={"test": True})

    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["seed"] == DEFAULT_SEED
    assert loaded["splits"] == splits
    assert loaded["metadata"]["test"] is True
