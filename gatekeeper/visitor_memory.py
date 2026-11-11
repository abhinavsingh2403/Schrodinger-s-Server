"""
visitor_memory.py: SQLite-backed visitor memory with salted HMAC tracking.

Per SPEC.md Section 5.2:
- visitor_id = HMAC-SHA256(secret_salt, source_ip)
- Secret salt stored outside git / loaded via environment or argument
- Stores: first_seen, last_seen, n_sessions, highest_tier_served, last_value_label, last_agent_score
- SQLite with WAL mode
- Fail-cheap rule: If unreachable or errors, defaults safely to T1
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Default tier hierarchy (monotone upward-only)
TIER_RANK = {"T1": 1, "T2": 2, "T3": 3}
RANK_TO_TIER = {1: "T1", 2: "T2", 3: "T3"}


def derive_visitor_id(source_ip: str, salt: bytes) -> str:
    """Derive deterministic, salted HMAC visitor ID from raw IP address."""
    if not source_ip or not salt:
        raise ValueError("source_ip and salt must be non-empty")
    h = hmac.new(salt, source_ip.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()[:16]


def get_masked_id(source_ip: str, salt: bytes) -> str:
    """Returns a privacy-safe masked identifier for dashboards and logs."""
    vid = derive_visitor_id(source_ip, salt)
    return f"vis_{vid[:8]}"


class VisitorMemory:
    """Persistent SQLite visitor memory supporting WAL mode and fail-cheap fallback."""

    def __init__(self, db_path: str | Path, salt: bytes | None = None) -> None:
        self.db_path = str(db_path)
        self.salt = salt or os.environ.get("VISITOR_SALT", "schrodinger-dev-salt-2026").encode("utf-8")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create visitor table if not exists."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS visitors (
                        visitor_id TEXT PRIMARY KEY,
                        first_seen TEXT NOT NULL,
                        last_seen TEXT NOT NULL,
                        n_sessions INTEGER DEFAULT 1,
                        highest_tier_served TEXT DEFAULT 'T1',
                        last_value_label INTEGER,
                        last_agent_score REAL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_visitors_last_seen
                    ON visitors(last_seen)
                    """
                )
        except Exception:
            # Operational failure during DB init; will fail-cheap on queries
            pass

    def get_visitor(self, source_ip: str) -> dict[str, Any]:
        """
        Retrieves visitor profile. If unknown or on error, returns fail-cheap default.
        """
        try:
            visitor_id = derive_visitor_id(source_ip, self.salt)
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM visitors WHERE visitor_id = ?", (visitor_id,)
                ).fetchone()
                if row:
                    return dict(row)
        except Exception:
            # Fail-cheap rule: Never block or drop connection on error
            pass

        return {
            "visitor_id": derive_visitor_id(source_ip, self.salt),
            "first_seen": None,
            "last_seen": None,
            "n_sessions": 0,
            "highest_tier_served": "T1",
            "last_value_label": None,
            "last_agent_score": None,
        }

    def record_session(
        self,
        source_ip: str,
        tier_served: str = "T1",
        value_label: int | None = None,
        agent_score: float | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """
        Records or updates a visitor's session history.
        Enforces monotone upward-only highest_tier_served.
        """
        now = timestamp or datetime.now(timezone.utc).isoformat()
        visitor_id = derive_visitor_id(source_ip, self.salt)

        try:
            with self._get_connection() as conn:
                existing = conn.execute(
                    "SELECT n_sessions, highest_tier_served FROM visitors WHERE visitor_id = ?",
                    (visitor_id,),
                ).fetchone()

                if existing:
                    new_n = existing["n_sessions"] + 1
                    old_rank = TIER_RANK.get(existing["highest_tier_served"], 1)
                    new_rank = max(old_rank, TIER_RANK.get(tier_served, 1))
                    highest_tier = RANK_TO_TIER.get(new_rank, "T1")

                    conn.execute(
                        """
                        UPDATE visitors
                        SET last_seen = ?,
                            n_sessions = ?,
                            highest_tier_served = ?,
                            last_value_label = COALESCE(?, last_value_label),
                            last_agent_score = COALESCE(?, last_agent_score)
                        WHERE visitor_id = ?
                        """,
                        (now, new_n, highest_tier, value_label, agent_score, visitor_id),
                    )
                else:
                    highest_tier = tier_served if tier_served in TIER_RANK else "T1"
                    conn.execute(
                        """
                        INSERT INTO visitors (
                            visitor_id, first_seen, last_seen, n_sessions,
                            highest_tier_served, last_value_label, last_agent_score
                        ) VALUES (?, ?, ?, 1, ?, ?, ?)
                        """,
                        (visitor_id, now, now, highest_tier, value_label, agent_score),
                    )

            return self.get_visitor(source_ip)
        except Exception:
            # Fail-cheap return
            return {
                "visitor_id": visitor_id,
                "first_seen": now,
                "last_seen": now,
                "n_sessions": 1,
                "highest_tier_served": tier_served,
                "last_value_label": value_label,
                "last_agent_score": agent_score,
            }
