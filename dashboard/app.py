"""
Read-Only Results Dashboard for Schrödinger's Server.
Pre-registered in SPEC.md Section 4 and AGENTS.md Rule 19.

Rules enforced:
- Every panel is explicitly labeled RECORDED, LAB, LIVE, SYNTHETIC, MIXED, or UNKNOWN.
- All attacker identifiers are cryptographically masked (vis_xxxx); zero raw IPs exposed.
- Impeccable dark-mode UI with high data density and zero external npm/pip dependencies.
- Zero fabricated data: all figures originate from results/*.json or SQLite decision log.
"""

from __future__ import annotations

import argparse
import http.server
import json
import logging
import os
import sqlite3
import statistics
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard import decision_views, evidence

logger = logging.getLogger("dashboard")


VALID_PROVENANCES = frozenset({"SYNTHETIC", "LAB", "LIVE", "UNKNOWN"})


def normalize_policy_profile(value):
    """Only engine-defined profiles are meaningful; legacy/invalid values stay unknown."""
    return value if value in ('DEFAULT', 'LAB_DEMO') else 'UNKNOWN'


def resolve_policy_profile(profiles):
    """Summarize the rows represented by this response, including unknown rows."""
    unique = {normalize_policy_profile(value) for value in profiles}
    return next(iter(unique)) if len(unique) == 1 else ('MIXED' if unique else 'UNKNOWN')


def policy_profile_select(conn):
    """Read older databases without migrating or hiding their decision rows."""
    columns = {row[1] for row in conn.execute('PRAGMA table_info(decision_log)')}
    return 'policy_profile' if 'policy_profile' in columns else "'UNKNOWN' AS policy_profile"


def resolve_decision_provenance(mode: str, row_provenances: List[str]) -> str:
    """
    Deterministically resolves the aggregate sensor/decision provenance label.
    Shared by both /api/stats and /api/decisions.

    Rules:
    1. If there are no rows in the decision log:
       Return 'SYNTHETIC' if mode == 'SYNTHETIC' else 'UNKNOWN'.
    2. If all rows share the same provenance (e.g. all 'SYNTHETIC' or all 'LAB'):
       Return that row provenance.
       Note: A LAB-only DB under mode == 'LIVE' returns 'LAB', not 'LIVE'.
    3. If rows have mixed provenance (e.g. some 'SYNTHETIC' and some 'LAB'):
       Return 'MIXED'.
    """
    if not row_provenances:
        return "SYNTHETIC" if mode.upper() == "SYNTHETIC" else "UNKNOWN"

    clean_prov = [
        p.upper() if (p and p.upper() in VALID_PROVENANCES) else "UNKNOWN"
        for p in row_provenances
    ]
    unique_prov = set(clean_prov)
    if not unique_prov:
        return "SYNTHETIC" if mode.upper() == "SYNTHETIC" else "UNKNOWN"

    if len(unique_prov) > 1:
        return "MIXED"

    return next(iter(unique_prov))


class DashboardServer:
    """Core state and data provider for the read-only dashboard."""

    def __init__(
        self,
        db_path: str | Path = "gatekeeper/gatekeeper.db",
        base_rates_path: str | Path = "results/base_rates.json",
        arm_simulation_path: str | Path = "results/arm_simulation.json",
        natural_experiment_path: str | Path = "results/natural_experiment.json",
        model_path: str | Path = "models/model_s3.json",
        exp0_path: str | Path = "results/exp0/rules_summary.json",
        mode: str = "LAB",
        host: str = "127.0.0.1",
        port: int = 8080,
        gatekeeper_host: str = "127.0.0.1",
        gatekeeper_port: int = 15000,
    ) -> None:
        self.db_path = str(db_path)
        self.base_rates_path = str(base_rates_path)
        self.arm_simulation_path = str(arm_simulation_path)
        self.natural_experiment_path = str(natural_experiment_path)
        self.model_path = str(model_path)
        self.exp0_path = str(exp0_path)
        self.mode = mode.upper() if mode.upper() in ("LIVE", "LAB", "SYNTHETIC", "UNKNOWN") else "UNKNOWN"
        self.host = host
        self.gatekeeper_host = gatekeeper_host
        self.gatekeeper_port = gatekeeper_port
        self.port = port
        self.httpd: Optional[http.server.HTTPServer] = None

    def _get_db_connection(self) -> Optional[sqlite3.Connection]:
        """Safely open read-only connection to SQLite database."""
        if not os.path.exists(self.db_path):
            return None
        try:
            conn = sqlite3.connect(Path(self.db_path).resolve().as_uri() + "?mode=ro", uri=True, timeout=3.0)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception:
            return None

    def get_stats_data(self) -> Dict[str, Any]:
        """Returns aggregated metrics for the RECORDED dataset and LAB/LIVE engine.
        
        If results/base_rates.json is missing, returns status 'NO DATA'.
        """
        if not os.path.exists(self.base_rates_path):
            return {"status": "NO DATA", "source": "RECORDED"}

        dataset_stats: Dict[str, Any] = {
            "source": "RECORDED",
            "label": "RECORDED",
            "total_sessions": None,
            "positive_sessions": None,
            "base_rate_pct": None,
            "days_covered": None,
            "source_description": "RECORDED",
        }

        try:
            with open(self.base_rates_path, "r", encoding="utf-8") as f:
                br = json.load(f)
                overall = br.get("overall", {})
                total = overall.get("total_sessions", br.get("total_sessions"))
                val1_approx = overall.get("value_1_approximation", {})
                pos = val1_approx.get("count", br.get("value_1_count"))

                dataset_stats["total_sessions"] = total
                dataset_stats["positive_sessions"] = pos
                if total and pos is not None:
                    dataset_stats["base_rate_pct"] = round((pos / total) * 100, 2)
                by_day = br.get("by_day", {})
                if isinstance(by_day, dict) and by_day:
                    dataset_stats["days_covered"] = len(by_day)
                dataset_stats["source_description"] = br.get("metadata", {}).get(
                    "approximation_note", "Cowrie public aggregation (DATA.md D1)"
                )
        except Exception as e:
            logger.warning("Error reading %s: %s", self.base_rates_path, e)
            return {"status": "NO DATA", "source": "RECORDED"}

        # Sensor decisions stats (LAB / LIVE / SYNTHETIC / MIXED)
        tier_counts = {"T1": 0, "T2": 0, "T3": 0}
        total_decisions = 0
        latencies: List[float] = []
        row_provenances: List[str] = []
        profiles = []

        conn = self._get_db_connection()
        if conn:
            try:
                profile_column = policy_profile_select(conn)
                rows = conn.execute(f"SELECT session_id, tier_decided, latency_ms, provenance, {profile_column} FROM decision_log").fetchall()
                for r in rows:
                    t = r["tier_decided"]
                    tier_counts[t] = tier_counts.get(t, 0) + 1
                    latencies.append(float(r["latency_ms"]))
                    raw_prov = r["provenance"] if ("provenance" in r.keys() and r["provenance"]) else "UNKNOWN"
                    prov = raw_prov.upper() if raw_prov and raw_prov.upper() in VALID_PROVENANCES else "UNKNOWN"
                    row_provenances.append(prov)
                    profiles.append(r['policy_profile'])
                total_decisions = len(rows)
            except Exception:
                pass
            finally:
                conn.close()

        latencies.sort()
        p95_lat = latencies[int(len(latencies) * 0.95)] if latencies else None

        # Shared provenance resolution across stats and decisions
        sensor_source = resolve_decision_provenance(self.mode, row_provenances)

        sensor_stats = {
            "policy_profile": resolve_policy_profile(profiles),
            "source": sensor_source,
            "label": sensor_source,
            "total_decisions": total_decisions,
            "tier_counts": tier_counts,
            "escalated_count": tier_counts.get("T2", 0) + tier_counts.get("T3", 0),
            "escalation_rate_pct": round(
                ((tier_counts.get("T2", 0) + tier_counts.get("T3", 0)) / total_decisions * 100), 2
            ) if total_decisions > 0 else None,
            "p95_latency_ms": round(p95_lat, 2) if p95_lat is not None else None,
        }

        return {
            "status": "ok",
            "source": "RECORDED",
            "dataset": dataset_stats,
            "sensor": sensor_stats,
        }

    def get_decisions_data(self, limit: int = 50, public: bool = False) -> Dict[str, Any]:
        """Returns the recent decision stream with cryptographically masked visitor IDs."""
        if not os.path.exists(self.db_path):
            fallback_source = resolve_decision_provenance(self.mode, [])
            return {"status": "NO DATA", "source": fallback_source, "label": fallback_source, "policy_profile": "UNKNOWN", "decisions": []}

        read_ok = True
        decisions: List[Dict[str, Any]] = []
        row_provenances: List[str] = []
        conn = self._get_db_connection()

        if conn:
            try:
                profile_column = policy_profile_select(conn)
                columns = {r[1] for r in conn.execute('PRAGMA table_info(decision_log)')}
                score_column = 'score_source' if 'score_source' in columns else "'UNKNOWN' AS score_source"
                rows = conn.execute(
                    f"""
                    SELECT session_id, visitor_id, stage, score, tier_decided, latency_ms, timestamp, provenance, {profile_column}, {score_column}
                    FROM decision_log
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

                for r in rows:
                    vid = r["visitor_id"]
                    masked = vid if vid.startswith("vis_") else f"vis_{vid[:8]}"
                    raw_prov = r["provenance"] if ("provenance" in r.keys() and r["provenance"]) else "UNKNOWN"
                    prov = raw_prov.upper() if raw_prov and raw_prov.upper() in VALID_PROVENANCES else "UNKNOWN"
                    row_provenances.append(prov)
                    decisions.append({
                        "session_id": r["session_id"],
                        "visitor_id": vid if public else masked,
                        "stage": r["stage"],
                        "score": decision_views.number(r["score"]),
                        "tier": r["tier_decided"],
                        "latency_ms": decision_views.number(r["latency_ms"]),
                        "timestamp": r["timestamp"],
                        "provenance": prov,
                        "policy_profile": normalize_policy_profile(r['policy_profile']),
                        "score_source": r["score_source"],
                    })
            except Exception:
                read_ok = False
            finally:
                conn.close()

        if public:
            decisions = [decision_views.public_row(row) for row in decisions]
        # Shared provenance resolution across stats and decisions
        source = resolve_decision_provenance(self.mode, row_provenances)

        return {
            "status": "ok" if read_ok and conn else "NO DATA",
            "source": source,
            "label": source,
            "count": len(decisions),
            "policy_profile": resolve_policy_profile(r['policy_profile'] for r in decisions),
            "decisions": decisions,
        }

    def get_sessions_data(self, public=False):
        """Summarize all stored decisions; returning means an earlier observed session."""
        payload = self.get_decisions_data(limit=-1, public=public)
        rows = list(reversed(payload['decisions']))
        sessions, seen = {}, set()
        for row in rows:
            sid = row['session_id']
            if sid not in sessions:
                sessions[sid] = {'session_id': sid, 'visitor_id': row['visitor_id'],
                    'returning_visitor': row['visitor_id'] in seen, 'stages': {},
                    'transitions': [], 'decisions': [], 'reached_t2': False}
                seen.add(row['visitor_id'])
            session = sessions[sid]
            previous = session['decisions'][-1]['tier'] if session['decisions'] else None
            if previous and previous != row['tier']:
                session['transitions'].append({'stage': row['stage'], 'from': previous, 'to': row['tier']})
            session['stages'][row['stage']] = row['tier']
            session['decisions'].append(row)
            session['reached_t2'] |= row['tier'] in ('T2', 'T3')
        times = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]
        count = len(sessions)
        escalated = sum(s['reached_t2'] for s in sessions.values())
        return {'status': payload['status'], 'source': payload['source'],
            'has_lab_demo': any(r['policy_profile'] == 'LAB_DEMO' for r in rows),
            'sessions': list(sessions.values()),
            'kpis': {'sessions': count, 'reached_t2': escalated,
                'escalation_fraction': escalated/count if count else None,
                'median_compute_ms': statistics.median(round(t, 2) for t in times) if times else None}}

    def get_arms_data(self) -> Dict[str, Any]:
        """Returns comparative intelligence yield per rupee across experimental arms.
        
        Reads only results/arm_simulation.json. Zero fabricated fallback data.
        """
        if not os.path.exists(self.arm_simulation_path):
            return {"status": "NO DATA", "source": "RECORDED"}

        try:
            with open(self.arm_simulation_path, "r", encoding="utf-8") as f:
                sim_data = json.load(f)
            arms_payload = dict(sim_data.get("arms", {}))
            if "Arm D (Adaptive)" in arms_payload and "Arm D (Schrodinger Adaptive)" not in arms_payload:
                arms_payload["Arm D (Schrodinger Adaptive)"] = arms_payload["Arm D (Adaptive)"]

            return {
                "status": "ok",
                "source": "RECORDED",
                "label": "RECORDED",
                "badge": "SIMULATED ORACLE (HINDSIGHT UPPER BOUND)",
                "methodology": "Oracle Retrospective Simulation",
                "scientific_disclaimer": "Retrospective counter-based policy (Oracle Upper Bound); not an online early gatekeeper.",
                **arms_payload,
            }
        except Exception as e:
            logger.warning("Could not read %s: %s", self.arm_simulation_path, e)
            return {"status": "NO DATA", "source": "RECORDED"}

    def get_natural_experiment_data(self) -> Dict[str, Any]:
        """Returns natural experiment association results from results/natural_experiment.json."""
        if not os.path.exists(self.natural_experiment_path):
            return {"status": "NO DATA", "source": "RECORDED"}

        try:
            with open(self.natural_experiment_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["source"] = "RECORDED"
            data["status"] = "ok"
            return data
        except Exception as e:
            logger.warning("Could not read %s: %s", self.natural_experiment_path, e)
            return {"status": "NO DATA", "source": "RECORDED"}

    def get_model_data(self) -> Dict[str, Any]:
        """Returns the serialized model schema and metadata."""
        if not os.path.exists(self.model_path):
            return {"status": "NO DATA", "source": "RECORDED"}

        try:
            with open(self.model_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["source"] = "RECORDED"
            data["status"] = "ok"
            return data
        except Exception as e:
            logger.warning("Could not read %s: %s", self.model_path, e)
            return {"status": "NO DATA", "source": "RECORDED"}

    def get_exp0_data(self) -> Dict[str, Any]:
        """Returns Experiment 0 summary data."""
        if not os.path.exists(self.exp0_path):
            return {"status": "NO DATA", "source": "RECORDED"}

        try:
            with open(self.exp0_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["source"] = "RECORDED"
            data["status"] = "ok"
            return data
        except Exception as e:
            logger.warning("Could not read %s: %s", self.exp0_path, e)
            return {"status": "NO DATA", "source": "RECORDED"}

    def get_detector_data(self) -> Dict[str, Any]:
        """Returns third-party detector evaluation status (EVAL H4)."""
        detector_file = Path(__file__).resolve().parent.parent / "results" / "detector_eval.json"
        if not os.path.exists(detector_file):
            return {
                "status": "NO DATA",
                "source": "RECORDED",
                "badge": "EVAL H4 NOT YET EVALUATED",
                "message": "EVAL H4 NOT YET EVALUATED: Third-party detector evaluation is held out for live trial (see HANDOFF.md).",
            }

        try:
            with open(detector_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["source"] = "RECORDED"
            data["status"] = "ok"
            return data
        except Exception as e:
            logger.warning("Could not read %s: %s", detector_file, e)
            return {
                "status": "NO DATA",
                "source": "RECORDED",
                "badge": "EVAL H4 NOT YET EVALUATED",
            }

    def render_live_html(self) -> str:
        """Render the session-first demo view, without research cost panels."""
        return (Path(__file__).resolve().parent / 'templates/live.html').read_text(encoding='utf-8')

    def render_index_html(self) -> str:
        """Renders responsive single page application with embedded charts."""
        template_path = Path(__file__).resolve().parent / "templates" / "index.html"
        if template_path.exists():
            try:
                return template_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("Could not read template %s: %s", template_path, e)

        return """<!DOCTYPE html>
<html>
<head><title>Schrödinger's Server</title></head>
<body>
  <h1>Schrödinger's Server // Cyber Protocol</h1>
  <span>RECORDED</span><span>LAB</span><span>LIVE</span><span>SYNTHETIC</span><span>MIXED</span><span>UNKNOWN</span>
  <div>Yield per Rupee Optimization</div>
  <div>NO DATA</div>
</body>
</html>"""

    def start(self) -> None:
        """Run the dashboard HTTP server."""
        if self.host != "127.0.0.1":
            raise ValueError("Dashboard requires IPv4 loopback")
        handler_cls = make_dashboard_handler(self)
        self.httpd = http.server.HTTPServer((self.host, self.port), handler_cls)
        logger.info("Serving Schrödinger's Server dashboard at http://%s:%d", self.host, self.port)
        self.httpd.serve_forever()

    def stop(self) -> None:
        """Gracefully stop server."""
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None


PAGE_TITLES = {
    "/evidence": "Evidence Vault",
    "/cost": "Resource Observatory",
    "/ml": "Model Observatory",
    "/session": "Session Forensics",
    "/visitors": "Visitor Atlas",
    "/deception": "Deception Studio",
    "/lab": "Lab Console",
    "/replay": "Replay",
    "/detector": "Detector",
}


LEGACY = {
    "sessions": "decision_log", "decisions": "decision_log", "stats": "results/base_rates.json",
    "arms": "results/arm_simulation.json", "model": "models/model_s3.json",
    "exp0": "results/exp0/rules_summary.json", "natural_experiment": "results/natural_experiment.json",
    "detector": "results/detector_eval.json",
}


def probe_gatekeeper_health(
    host: str = "127.0.0.1",
    port: int = 15000,
    timeout: float = 1.0,
) -> Dict[str, Any]:
    """Securely probes the local Gatekeeper health endpoint on loopback.

    Security constraints:
    - Strictly restricts target to IPv4 loopback (127.0.0.1).
    - Prohibits user-supplied or external URLs.
    - Validates HTTP 200 status and {"status": "ok"} response shape.
    - Accurately reports ONLINE, UNAVAILABLE, or UNKNOWN.
    """
    if host not in ("127.0.0.1", "localhost"):
        return {
            "status": "UNKNOWN",
            "service": "gatekeeper",
            "error": "Security boundary: probing non-loopback host is forbidden",
            "port": port,
        }

    url = f"http://{host}:{port}/health"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Schrodinger-Dashboard/1.0", "Accept": "application/json"},
        )
        # Connect directly to loopback. HTTPErrorProcessor is the component
        # that normally dispatches redirects; bypass redirect and proxy handlers.
        class DirectResponse(urllib.request.HTTPErrorProcessor):
            def http_response(self, request, response):
                return response

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), DirectResponse())
        with opener.open(req, timeout=timeout) as resp:
            if resp.status != 200:
                return {
                    "status": "UNAVAILABLE",
                    "service": "gatekeeper",
                    "error": f"Unexpected HTTP status {resp.status}",
                    "port": port,
                }
            raw = resp.read(8193)
            if len(raw) > 8192:
                raise ValueError("Oversized health response")
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, dict) and data.get("status") == "ok":
                return {
                    "status": "ONLINE",
                    "service": data.get("service", "gatekeeper"),
                    "version": data.get("version", "unknown"),
                    "port": port,
                    "target": f"{host}:{port}",
                }
            return {
                "status": "UNAVAILABLE",
                "service": "gatekeeper",
                "error": "Malformed health payload (missing status='ok')",
                "port": port,
            }
    except urllib.error.HTTPError as e:
        return {
            "status": "UNAVAILABLE",
            "service": "gatekeeper",
            "error": f"HTTP error {e.code}: {e.reason}",
            "port": port,
        }
    except urllib.error.URLError as e:
        return {
            "status": "UNAVAILABLE",
            "service": "gatekeeper",
            "error": f"Connection failed: {e.reason}",
            "port": port,
        }
    except TimeoutError:
        return {
            "status": "UNAVAILABLE",
            "service": "gatekeeper",
            "error": "Connection timed out",
            "port": port,
        }
    except Exception as e:
        return {
            "status": "UNAVAILABLE",
            "service": "gatekeeper",
            "error": f"Unexpected probe error: {e}",
            "port": port,
        }


def api_response(server, path):
    """One wire representation for HTTP and offline fixture generation."""
    if path in ("/api/gatekeeper/health", "/api/health/gatekeeper"):
        health = probe_gatekeeper_health(server.gatekeeper_host, server.gatekeeper_port)
        health["metadata"] = evidence.labels("gatekeeper /health", "LAB", "done" if health["status"] == "ONLINE" else "INCONCLUSIVE")
        return 200, health
    if path.startswith("/api/evidence/") or path == "/api/progress":
        return evidence.response(path)
    if path == "/api/decisions/summary" or path.startswith("/api/session/"):
        return decision_views.decision_response(server, path)
    name = path.removeprefix("/api/")
    if name not in LEGACY:
        return 404, {**evidence.labels(), "data": None, "empty": "Unknown endpoint"}
    getter = getattr(server, f"get_{name}_data")
    payload = getter(public=True) if name in ("sessions", "decisions") else evidence.clean(getter())
    rows = payload.get("decisions", []) if name == "decisions" else [
        r for session in payload.get("sessions", []) for r in session["decisions"]]
    scope = payload.get("source")
    status = "exploratory" if payload.get("status") == "ok" else "NOT RUN"
    if name in ("sessions", "decisions"):
        status = "done" if rows else "NOT RUN"
    payload["metadata"] = evidence.labels(LEGACY[name], scope if scope in VALID_PROVENANCES else "UNKNOWN",
                                          status, decision_views.common(rows, "policy_profile"))
    return 200, payload


def make_dashboard_handler(server_instance: DashboardServer):
    """Factory creating an HTTP request handler bound to the DashboardServer."""

    class DashboardHandler(http.server.BaseHTTPRequestHandler):
        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            if path.startswith("/api/"):
                code, data = api_response(server_instance, path)
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))
                return

            if path == "/" or path == "/index.html":
                html = server_instance.render_live_html()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))

            elif path in PAGE_TITLES:
                template = Path(__file__).with_name("templates") / "page_shell.html"
                html = template.read_text(encoding="utf-8-sig").replace("{{title}}", PAGE_TITLES[path])
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf8"))
            elif path == "/research":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(server_instance.render_index_html().encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")

        def log_message(self, format: str, *args: Any) -> None:
            # Silence default stderr request logging
            pass

    return DashboardHandler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Schrödinger's Server Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface")
    parser.add_argument("--port", type=int, default=8080, help="Listen port")
    parser.add_argument("--mode", default="LAB", choices=["LAB", "LIVE", "SYNTHETIC", "UNKNOWN"], help="Operational mode")
    parser.add_argument("--db", default="gatekeeper/gatekeeper.db", help="Path to SQLite decision DB (default: gatekeeper/gatekeeper.db)")
    parser.add_argument("--gatekeeper-host", default="127.0.0.1", choices=("localhost", "127.0.0.1"))
    parser.add_argument("--gatekeeper-port", default=15000, type=int)
    args = parser.parse_args()
    if not 1 <= args.gatekeeper_port <= 65535:
        parser.error("gatekeeper port outside TCP range")

    dash = DashboardServer(db_path=args.db, host=args.host, port=args.port, mode=args.mode, gatekeeper_host=args.gatekeeper_host, gatekeeper_port=args.gatekeeper_port)
    print(f"Starting Schrödinger's Server dashboard on http://{args.host}:{args.port} [DB: {args.db}]")
    try:
        dash.start()
    except KeyboardInterrupt:
        dash.stop()

