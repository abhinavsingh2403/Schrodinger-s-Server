"""
decision_api.py: In-process and HTTP Decision API for Schrödinger's Server.

Per SPEC.md Section 5.2:
- Ingests Cowrie session events or stage queries
- Evaluates visitor memory and stage features
- Scores session (via ML model or rule fallback)
- Applies upward-only escalation policy
- Logs decision to SQLite WAL with latency measurement
- Fail-cheap rule: On any error, timeout, or missing input, defaults safely to T1
"""

from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gatekeeper.feature_extractor import SessionFeatureExtractor
from gatekeeper.policy import EscalationPolicy
from gatekeeper.visitor_memory import VisitorMemory, derive_visitor_id, get_masked_id


class DecisionEngine:
    """Core decision engine coordinating feature extraction, visitor memory, scoring, and policy."""

    def __init__(
        self,
        db_path: str | Path = "gatekeeper/gatekeeper.db",
        salt: bytes | None = None,
        policy: EscalationPolicy | None = None,
        model: Any | None = None,
    ) -> None:
        self.db_path = str(db_path)
        self.salt = salt or os.environ.get("VISITOR_SALT", "schrodinger-dev-salt-2026").encode("utf-8")
        self.memory = VisitorMemory(self.db_path, salt=self.salt)
        self.policy = policy or EscalationPolicy(threshold_t2=0.50, threshold_t3=0.85)
        self.model = model  # Friend will plug in trained model here; fallback to rule if None
        self._init_decision_log()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_decision_log(self) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS decision_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        visitor_id TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        score REAL NOT NULL,
                        tier_decided TEXT NOT NULL,
                        latency_ms REAL NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_decision_session
                    ON decision_log(session_id)
                    """
                )
        except Exception:
            pass

    def score_features(self, stage: str, features: dict[str, Any]) -> float:
        """Score stage features using loaded model or pre-declared heuristic fallback."""
        if self.model is not None:
            try:
                # If model has predict_proba
                return float(self.model.predict_proba([list(features.values())])[0][1])
            except Exception:
                pass

        # Rule-based fallback (EXPERIMENT0.md Section 7)
        if stage in ("S1", "S2"):
            if features.get("s2_has_success", 0) > 0:
                return 0.70  # Authenticated session: high probability of value
            if features.get("s2_failed_logins", 0) > 3:
                return 0.40  # Brute force probe
            return 0.10

        elif stage in ("S3", "S4", "S5"):
            if features.get("s3_has_pty", 0) > 0:
                return 0.80  # Terminal allocated: interactive candidate
            if features.get("s4_cmd1_has_pipe", 0) > 0 or features.get("s4_cmd1_has_chain", 0) > 0:
                return 0.85  # Multi-stage or complex command
            return 0.20

        return 0.05

    def decide(
        self,
        session_id: str,
        source_ip: str,
        stage: str,
        features: dict[str, Any],
        current_tier: str = "T1",
    ) -> dict[str, Any]:
        """
        Evaluate session and return tier decision with strict fail-cheap safety.
        """
        start_time = time.perf_counter()
        now = datetime.now(timezone.utc).isoformat()
        visitor_id = derive_visitor_id(source_ip, self.salt)
        masked_id = get_masked_id(source_ip, self.salt)

        try:
            # 1. Visitor memory lookup
            visitor = self.memory.get_visitor(source_ip)

            # 2. Score computation
            score = self.score_features(stage, features)

            # 3. Policy evaluation (monotone upward-only)
            target_tier = self.policy.decide_tier(
                current_tier=current_tier,
                model_score=score,
                visitor_profile=visitor,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000.0

            # 4. Asynchronous / safe decision log write
            try:
                with self._get_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO decision_log (
                            session_id, visitor_id, stage, score, tier_decided, latency_ms, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (session_id, visitor_id, stage, score, target_tier, latency_ms, now),
                    )
            except Exception:
                pass

            return {
                "session_id": session_id,
                "visitor_id": masked_id,
                "stage": stage,
                "score": round(score, 4),
                "tier": target_tier,
                "latency_ms": round(latency_ms, 3),
                "fail_cheap": False,
            }

        except Exception:
            # Fail-cheap rule: If any error happens, default to T1
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "session_id": session_id,
                "visitor_id": masked_id,
                "stage": stage,
                "score": 0.0,
                "tier": current_tier if current_tier in ("T1", "T2", "T3") else "T1",
                "latency_ms": round(latency_ms, 3),
                "fail_cheap": True,
            }
