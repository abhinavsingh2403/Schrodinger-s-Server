"""Privacy-preserving projections of recorded engine decisions."""
from collections import Counter
from datetime import datetime
from hashlib import sha256
import hmac
import math
import os
import re
from statistics import median

from dashboard.evidence import labels

SOURCES = set("rule_r0_random rule_r1_login_success rule_r6_failed_logins rule_r7_decision_tree rule_r2_pty_requested heuristic_command_chain heuristic_command_base ml_model_s3 lab_pty_mechanism LAB_DEMO_NOT_ML_s5_command_count fail_cheap_fallback".split())

DEFAULT_MASKING_SALT = os.environ.get("DASHBOARD_MASKING_SALT", "").encode("utf-8")


def masked(value, prefix, salt: bytes = DEFAULT_MASKING_SALT):
    """Generate a privacy-safe pseudonym.
    
    If DASHBOARD_MASKING_SALT is configured, computes keyed HMAC-SHA256.
    Otherwise defaults to deterministic SHA-256 for backward compatibility
    with static fixtures and test invariants.
    """
    if salt:
        return prefix + hmac.new(salt, str(value).encode("utf-8"), sha256).hexdigest()[:24]
    return prefix + sha256(str(value).encode("utf-8")).hexdigest()[:24]


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def public_row(row):
    row = dict(row)
    for key, allowed in (("stage", {"S1","S2","S3","S4","S5"}), ("tier", {"T1","T2","T3"}),
                         ("score_source", SOURCES)):
        if row[key] not in allowed:
            row[key] = "UNKNOWN"
    try:
        datetime.fromisoformat(row["timestamp"])
    except (ValueError, TypeError):
        row["timestamp"] = None
    row["session_id"] = masked(row["session_id"], "ses_")
    row["visitor_id"] = masked(row["visitor_id"], "vis_")
    return row


def common(rows, field):
    values = {r[field] for r in rows}
    return next(iter(values)) if len(values) == 1 else "UNKNOWN"


def decision_response(provider, path):
    summary = path == "/api/decisions/summary"
    requested = path.rsplit("/", 1)[-1]
    rows = []
    if summary or re.fullmatch(r"ses_[0-9a-f]{24}", requested):
        rows = list(reversed(provider.get_decisions_data(limit=-1, public=True)["decisions"]))
        if not summary:
            rows = [r for r in rows if r["session_id"] == requested]
    meta = labels("decision_log", common(rows, "provenance"), "done" if rows else "NOT RUN",
                  common(rows, "policy_profile"))
    if not rows:
        return (200 if summary else 404), {**meta, "data": None, "empty": "NO DATA"}
    if not summary:
        decisions = []
        for row in rows:
            item = {k:v for k,v in row.items() if k not in ("session_id","visitor_id","tier")}
            decisions.append({**item, "tier_decided": row["tier"],
                              "demo_label": "LAB_DEMO_NOT_ML" if row["policy_profile"] == "LAB_DEMO" else None})
        return 200, {**meta, "data": {"session_id": requested, "decisions": decisions}}
    counts = {k: dict(Counter(r[k] for r in rows)) for k in
              ("tier","stage","provenance","policy_profile","score_source")}
    times = sorted(r["latency_ms"] for r in rows if r["latency_ms"] is not None)
    latency = None if not times else dict(min=times[0], median=median(times),
                                          p95=times[math.ceil(.95*len(times))-1], max=times[-1])
    return 200, {**meta, "data": {"counts": counts, "total_sessions": len({r["session_id"] for r in rows}),
                 "latency_ms": latency, "latency_label": "engine compute time, not end-to-end"}}
