"""
exp0_rules.py: Pre-declared simple-rule baselines (R0 to R7) for Experiment 0.

Per EXPERIMENT0.md Section 7:
- R0: Random score (uniform [0, 1])
- R1: 1 if login succeeded, else 0 (S2+)
- R2: 1 if PTY / terminal requested (S3+)
- R3: 1 if interactive shell rather than exec (S3+)
- R4: Delay / duration score (S4+)
- R5: Rarity score (negative log frequency of version/sensor features) (S1+)
- R6: Number of failed logins before success (S2+)
- R7: Depth-3 decision tree on simple features R1-R6 (S2+)
"""

from __future__ import annotations

import math
import random
from typing import Any


def score_r0_random(n: int, seed: int = 42) -> list[float]:
    """R0: Uniform random baseline."""
    rng = random.Random(seed)
    return [rng.random() for _ in range(n)]


def score_r1_login_success(cnt_login_success: list[int]) -> list[float]:
    """R1: 1 if login succeeded, else 0."""
    return [1.0 if x > 0 else 0.0 for x in cnt_login_success]


def score_r2_pty_requested(has_pty: list[bool]) -> list[float]:
    """R2: 1 if PTY requested, else 0."""
    return [1.0 if p else 0.0 for p in has_pty]


def score_r5_rarity(items: list[str], train_counts: dict[str, int], total_train: int) -> list[float]:
    """R5: Negative log frequency of item in training set (rarity)."""
    scores = []
    for item in items:
        count = train_counts.get(item, 1)  # Laplace add-1 smoothing
        freq = count / (total_train + len(train_counts))
        scores.append(-math.log(max(freq, 1e-9)))
    return scores


def score_r6_failed_logins(cnt_login_failed: list[int], sign: int = 1) -> list[float]:
    """R6: Number of failed logins before success."""
    return [float(sign * x) for x in cnt_login_failed]


def recall_at_budget(scores: list[float], labels: list[int], budget: float) -> float:
    """
    Computes recall of value=1 sessions within the top `budget` fraction of highest-scored sessions.
    
    budget is in (0, 1], e.g. 0.10 for 10% budget.
    """
    if not scores or not labels or len(scores) != len(labels):
        raise ValueError("Scores and labels must be non-empty and of equal length.")

    total_positives = sum(labels)
    if total_positives == 0:
        return 0.0

    k = max(1, int(math.ceil(budget * len(scores))))
    
    # Sort indices descending by score
    indexed_scores = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    top_k_indices = [idx for idx, _ in indexed_scores[:k]]

    positives_captured = sum(labels[i] for i in top_k_indices)
    return positives_captured / total_positives
