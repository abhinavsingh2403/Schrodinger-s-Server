"""
policy.py: Monotone upward-only escalation policy engine for Schrödinger's Server.

Per SPEC.md Section 3 & Section 5.3:
- Tier order: T1 Lite (1) < T2 Hardened (2) < T3 Real VM (3)
- Escalation is strictly upward-only: never downgrades within a session or visitor context
- Visitor memory escalation: A visitor that previously earned T2 or T3 retains that fidelity
- Fail-cheap: on any error or missing input, defaults safely to T1
"""

from __future__ import annotations

from typing import Any

TIER_RANK: dict[str, int] = {"T1": 1, "T2": 2, "T3": 3}
RANK_TO_TIER: dict[int, str] = {1: "T1", 2: "T2", 3: "T3"}


class EscalationPolicy:
    """Evaluates early decision features and visitor history to choose honeypot tier."""

    def __init__(
        self,
        threshold_t2: float = 0.50,
        threshold_t3: float = 0.85,
        t3_enabled: bool = False,
    ) -> None:
        self.threshold_t2 = threshold_t2
        self.threshold_t3 = threshold_t3
        self.t3_enabled = t3_enabled

    def decide_tier(
        self,
        current_tier: str = "T1",
        model_score: float = 0.0,
        visitor_profile: dict[str, Any] | None = None,
    ) -> str:
        """
        Decides target tier enforcing upward-only escalation.
        
        @param current_tier: Current tier in the session (T1, T2, T3)
        @param model_score: Predicted value probability in [0, 1]
        @param visitor_profile: Dictionary from visitor_memory
        @return: Escalated or maintained tier string
        """
        try:
            current_rank = TIER_RANK.get(current_tier, 1)

            # Check visitor memory history
            memory_rank = 1
            if visitor_profile:
                highest_past = visitor_profile.get("highest_tier_served", "T1")
                memory_rank = TIER_RANK.get(highest_past, 1)

            # Score-based tier recommendation
            score_rank = 1
            if self.t3_enabled and model_score >= self.threshold_t3:
                score_rank = 3
            elif model_score >= self.threshold_t2:
                score_rank = 2

            # Upward-only rule: take the maximum of current, memory, and score
            target_rank = max(current_rank, memory_rank, score_rank)

            # Cap at T2 if T3 is disabled
            if not self.t3_enabled and target_rank > 2:
                target_rank = 2

            return RANK_TO_TIER.get(target_rank, "T1")

        except Exception:
            # Fail-cheap rule: fall back to current tier or T1
            return current_tier if current_tier in TIER_RANK else "T1"
