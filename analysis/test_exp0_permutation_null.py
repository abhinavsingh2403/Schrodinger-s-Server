"""Protect label counts and isolation in the reporting-only permutation test."""
from analysis.exp0_permutation_null import permute


def test_permutation_preserves_counts_and_input():
    original = [0] * 70 + [1] * 30
    shuffled = permute(original, 42)
    assert original == [0] * 70 + [1] * 30
    assert sorted(shuffled) == sorted(original)
    assert shuffled != original
    assert shuffled == permute(original, 42)
    assert shuffled != permute(original, 43)
