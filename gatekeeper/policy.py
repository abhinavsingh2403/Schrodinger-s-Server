"""
policy.py: Monotone upward-only escalation policy engine for Schrödinger's Server.

Per SPEC.md Section 3, Section 5.3 & Section 10:
- Tier order: T1 Lite (1) < T2 Hardened (2) < T3 Real VM (3)
- Escalation is strictly upward-only: never downgrades within a session or visitor context
- Visitor memory escalation: A visitor that previously earned T2 or T3 retains that fidelity
- Loads config/policy.yaml for stage-dependent thresholds and budget ceilings
- Enforces max_escalation_fraction (10% budget ceiling) and max_concurrent_t3
- Fail-cheap: on any error or missing input, defaults safely to T1
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

TIER_RANK: dict[str, int] = {"T1": 1, "T2": 2, "T3": 3}
RANK_TO_TIER: dict[int, str] = {1: "T1", 2: "T2", 3: "T3"}


def parse_policy_yaml(file_path: Path | str) -> dict[str, Any]:
    """Pure-Python parser for config/policy.yaml with zero external dependencies."""
    p = Path(file_path)
    if not p.is_file():
        return {}

    cfg: dict[str, Any] = {
        "budget": {"max_escalation_fraction": 0.10, "max_concurrent_t3": 4},
        "thresholds": {"tau_v2": {}, "tau_v3": {}, "tau_a": {}},
    }

    current_section = ""
    current_sub = ""

    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Section headers
            if line.startswith("budget:"):
                current_section = "budget"
                current_sub = ""
                continue
            elif line.startswith("thresholds:"):
                current_section = "thresholds"
                current_sub = ""
                continue

            if current_section == "budget" and ":" in stripped:
                k, v = [x.strip() for x in stripped.split(":", 1)]
                v = v.split("#")[0].strip()
                try:
                    cfg["budget"][k] = float(v) if "." in v else int(v)
                except ValueError:
                    cfg["budget"][k] = v

            elif current_section == "thresholds":
                if stripped.endswith(":") and not stripped.startswith("S"):
                    current_sub = stripped.rstrip(":")
                    if current_sub not in cfg["thresholds"]:
                        cfg["thresholds"][current_sub] = {}
                elif ":" in stripped and current_sub:
                    k, v = [x.strip() for x in stripped.split(":", 1)]
                    v = v.split("#")[0].strip()
                    try:
                        cfg["thresholds"][current_sub][k] = float(v)
                    except ValueError:
                        pass

    return cfg


class EscalationPolicy:
    """Evaluates early decision features and visitor history to choose honeypot tier."""

    def __init__(
        self,
        threshold_t2: float = 0.50,
        threshold_t3: float = 0.85,
        t3_enabled: bool = False,
        config_path: str | Path | None = None,
    ) -> None:
        self.threshold_t2 = threshold_t2
        self.threshold_t3 = threshold_t3
        self.t3_enabled = t3_enabled
        self.config_path = config_path or self._default_config_path()

        # Loaded policy config
        self.cfg = parse_policy_yaml(self.config_path) if self.config_path else {}
        budget_cfg = self.cfg.get("budget", {})
        self.max_escalation_fraction: float = float(budget_cfg.get("max_escalation_fraction", 0.10))
        self.max_concurrent_t3: int = int(budget_cfg.get("max_concurrent_t3", 4))
        self.thresholds_v2: dict[str, float] = self.cfg.get("thresholds", {}).get("tau_v2", {})
        self.thresholds_v3: dict[str, float] = self.cfg.get("thresholds", {}).get("tau_v3", {})

        # Budget accounting
        self.total_decisions: int = 0
        self.escalated_decisions: int = 0
        self.active_t3_count: int = 0

    @staticmethod
    def _default_config_path() -> Path | None:
        cand = Path(__file__).resolve().parent.parent / "config" / "policy.yaml"
        return cand if cand.is_file() else None

    def get_threshold_t2(self, stage: str | None = None) -> float:
        if stage and stage in self.thresholds_v2:
            return self.thresholds_v2[stage]
        return self.threshold_t2

    def get_threshold_t3(self, stage: str | None = None) -> float:
        if stage and stage in self.thresholds_v3:
            return self.thresholds_v3[stage]
        return self.threshold_t3

    def decide_tier(
        self,
        current_tier: str = "T1",
        model_score: float = 0.0,
        visitor_profile: dict[str, Any] | None = None,
        stage: str | None = None,
    ) -> str:
        """
        Decides target tier enforcing upward-only escalation, stage thresholds, and budget constraints.
        
        @param current_tier: Current tier in the session (T1, T2, T3)
        @param model_score: Predicted value probability in [0, 1]
        @param visitor_profile: Dictionary from visitor_memory
        @param stage: Optional decision stage identifier ('S0', 'S1', ..., 'S5')
        @return: Escalated or maintained tier string
        """
        try:
            self.total_decisions += 1
            current_rank = TIER_RANK.get(current_tier, 1)

            # Check visitor memory history
            memory_rank = 1
            if visitor_profile:
                highest_past = visitor_profile.get("highest_tier_served", "T1")
                memory_rank = TIER_RANK.get(highest_past, 1)

            # Score-based tier recommendation using stage-specific thresholds
            th_t2 = self.get_threshold_t2(stage)
            th_t3 = self.get_threshold_t3(stage)

            score_rank = 1
            if self.t3_enabled and model_score >= th_t3:
                # Check concurrent T3 ceiling
                if self.active_t3_count < self.max_concurrent_t3:
                    score_rank = 3
                else:
                    score_rank = 2  # Spillover to T2 when T3 ceiling reached
            elif model_score >= th_t2:
                # Check 10% budget ceiling (if above budget and not saved by memory or current, damp to T1)
                curr_escalation_rate = (self.escalated_decisions / self.total_decisions) if self.total_decisions > 100 else 0.0
                if curr_escalation_rate <= self.max_escalation_fraction or memory_rank >= 2 or current_rank >= 2:
                    score_rank = 2
                else:
                    score_rank = 1

            # Upward-only rule: take the maximum of current, memory, and score
            target_rank = max(current_rank, memory_rank, score_rank)

            # Cap at T2 if T3 is disabled
            if not self.t3_enabled and target_rank > 2:
                target_rank = 2

            if target_rank >= 2:
                self.escalated_decisions += 1

            return RANK_TO_TIER.get(target_rank, "T1")

        except Exception:
            # Fail-cheap rule: fall back to current tier or T1
            return current_tier if current_tier in TIER_RANK else "T1"
