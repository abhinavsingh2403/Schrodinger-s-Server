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

import argparse
import http.server
import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
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
        salt: bytes | str | None = None,
        policy: EscalationPolicy | None = None,
        model: Any | None = None,
        memory: VisitorMemory | None = None,
    ) -> None:
        self.db_path = str(db_path)
        if isinstance(salt, str):
            self.salt = salt.encode("utf-8")
        else:
            self.salt = salt or os.environ.get("VISITOR_SALT", "schrodinger-dev-salt-2026").encode("utf-8")
        self.memory = memory or VisitorMemory(self.db_path, salt=self.salt)
        self.policy = policy or EscalationPolicy(threshold_t2=0.50, threshold_t3=0.85)
        self.model = model  # Friend will plug in trained model here; fallback to rule if None
        self._init_decision_log()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_decision_log(self) -> None:
        try:
            with self._connection() as conn:
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

        # Reconcile feature names across both raw sensor dicts and stage feature extractor
        has_success = features.get("s2_has_success", features.get("login_success", 0))
        failed_logins = features.get("s2_failed_logins", features.get("n_login_failed", 0))
        has_pty = features.get("s3_has_pty", features.get("has_pty", 0))

        # PLACEHOLDER HEURISTIC FALLBACK (Not learned parameters; rule-based defaults)
        # These constants are engineering placeholders until empirical ML model weights are loaded.
        if stage in ("S1", "S2"):
            if has_success > 0:
                return 0.70  # Placeholder heuristic: Authenticated session
            if failed_logins > 3:
                return 0.40  # Placeholder heuristic: Brute force probe
            return 0.10

        elif stage in ("S3", "S4", "S5"):
            if has_pty > 0:
                return 0.80  # Placeholder heuristic: Terminal allocated
            if (
                features.get("s4_cmd1_has_pipe", 0) > 0
                or features.get("s4_cmd1_has_chain", 0) > 0
                or features.get("chaining_ops_count", 0) > 0
            ):
                return 0.85  # Placeholder heuristic: Multi-stage or complex command
            return 0.20

        return 0.05

    def decide(
        self,
        session_id: str,
        source_ip: str | None = None,
        stage: str = "S0",
        features: dict[str, Any] | None = None,
        current_tier: str = "T1",
        visitor_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate session and return tier decision with strict fail-cheap safety.
        Accepts either source_ip or visitor_ip.
        """
        ip = source_ip or visitor_ip or "127.0.0.1"
        feats = features or {}
        start_time = time.perf_counter()
        now = datetime.now(timezone.utc).isoformat()
        visitor_id = derive_visitor_id(ip, self.salt)
        masked_id = get_masked_id(ip, self.salt)

        try:
            # 1. Visitor memory lookup
            visitor = self.memory.get_visitor(ip)

            # 2. Score computation
            score = self.score_features(stage, feats)

            # 3. Policy evaluation (monotone upward-only)
            target_tier = self.policy.decide_tier(
                current_tier=current_tier,
                model_score=score,
                visitor_profile=visitor,
                stage=stage,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000.0

            # 4. Asynchronous / safe decision log write
            try:
                with self._connection() as conn:
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
                "target_tier": target_tier,
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

    def record_session(
        self,
        source_ip: str,
        tier_served: str = "T1",
        value_label: int | None = None,
        agent_score: float | None = None,
    ) -> dict[str, Any]:
        """
        Records completed session in visitor memory to persist tier history.
        Completes the operational lifecycle hook when sessions terminate.
        """
        try:
            return self.memory.record_session(
                source_ip=source_ip,
                tier_served=tier_served,
                value_label=value_label,
                agent_score=agent_score,
            )
        except Exception:
            return {}


class GatekeeperClient:
    """HTTP client communicating with remote Gatekeeper REST service (e.g. from Cowrie)."""

    def __init__(self, base_url: str = "http://gatekeeper:5000", timeout: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def decide(
        self,
        session_id: str,
        source_ip: str | None = None,
        stage: str = "S0",
        features: dict[str, Any] | None = None,
        current_tier: str = "T1",
        visitor_ip: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/decide"
        payload = {
            "session_id": session_id,
            "source_ip": source_ip or visitor_ip or "127.0.0.1",
            "stage": stage,
            "features": features or {},
            "current_tier": current_tier,
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

        # Fail-cheap default if service unreachable
        return {
            "session_id": session_id,
            "visitor_id": "vis_network_fallback",
            "stage": stage,
            "score": 0.0,
            "tier": current_tier if current_tier in ("T1", "T2", "T3") else "T1",
            "target_tier": current_tier if current_tier in ("T1", "T2", "T3") else "T1",
            "latency_ms": 0.0,
            "fail_cheap": True,
        }

    def record_session(
        self,
        source_ip: str,
        tier_served: str = "T1",
        value_label: int | None = None,
        agent_score: float | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/record_session"
        payload = {
            "source_ip": source_ip,
            "tier_served": tier_served,
            "value_label": value_label,
            "agent_score": agent_score,
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass
        return {}


class GatekeeperHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Minimal HTTP request handler for Gatekeeper REST service."""

    def do_GET(self) -> None:
        if self.path in ("/health", "/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "gatekeeper", "version": "1.0.0"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        engine: DecisionEngine = getattr(self.server, "decision_engine", None)
        if not engine:
            self.send_response(500)
            self.end_headers()
            return

        if self.path == "/decide":
            resp = engine.decide(
                session_id=payload.get("session_id", "sess_unknown"),
                source_ip=payload.get("source_ip") or payload.get("visitor_ip"),
                stage=payload.get("stage", "S0"),
                features=payload.get("features", {}),
                current_tier=payload.get("current_tier", "T1"),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        elif self.path == "/record_session":
            resp = engine.record_session(
                source_ip=payload.get("source_ip", "127.0.0.1"),
                tier_served=payload.get("tier_served", "T1"),
                value_label=payload.get("value_label"),
                agent_score=payload.get("agent_score"),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy standard HTTP access logs
        pass


def run_server(
    host: str = "0.0.0.0",
    port: int = 5000,
    db_path: str | Path = "gatekeeper/gatekeeper.db",
) -> None:
    """Starts the Gatekeeper HTTP service."""
    engine = DecisionEngine(db_path=db_path)
    server = http.server.HTTPServer((host, port), GatekeeperHTTPHandler)
    server.decision_engine = engine  # type: ignore[attr-defined]
    print(f"Gatekeeper Decision Service listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gatekeeper Decision Service")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="HTTP port to bind (default: 5000)")
    parser.add_argument("--db", default="gatekeeper/gatekeeper.db", help="Path to SQLite DB")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, db_path=args.db)
