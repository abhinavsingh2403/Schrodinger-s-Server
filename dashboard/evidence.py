"""Read reviewed local evidence by public ID, with provenance and privacy filtering."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = 2 * 1024 * 1024
# Explicit paths, never a directory glob. Markdown statuses describe the document.
GROUPS = [
    ("results", "UNKNOWN", "done", "progress.json safety_check.json"),
    ("results", "LAB", "exploratory", "cost_model.json"),
    ("results/cost", "LAB", "exploratory", "concurrency_probe.json concurrency_probe_before.json cost_T1_only.json cost_T2_only.json COST_PER_TIER.md t1_trace.json"),
    ("results/cost", "LAB", "INVALID", "cost_model_confounded_T2.json"),
    ("results/study", "LAB", "done", "marker_consistency.json"),
    ("results/exp1", "UNKNOWN", "exploratory", "metrics.json cohorts.json ROOT_CAUSE.md"),
    ("results/exp1", "UNKNOWN", "INCONCLUSIVE", "EXPERIMENT1_RESULT.md"),
    ("results/exp0", "UNKNOWN", "exploratory", "NULL_ROOT_CAUSE.md NULL_DIAGNOSIS.md POSTHOC_ML_EVAL.md EXPERIMENT1_FEASIBILITY.md"),
    ("results/exp0", "UNKNOWN", "INCONCLUSIVE", "PRECOMMAND_NOT_VERIFIABLE.md"),
    ("results/replay", "LAB", "exploratory", "selection.json observations.json REPLAY_RESULT.md"),
    ("results/detector", "LAB", "INCONCLUSIVE", "DETECTOR_RESULT.md"),
    ("results/demo", "LAB", "done", "s1_multi_visitor_proof.json s2_mid_session_switch_proof.json s3_showcase.json"),
    ("docs", "UNKNOWN", "done", "STATUS.md"),
]
CATALOG = {Path(name).stem: (f"{folder}/{name}", scope, status)
           for folder, scope, status, names in GROUPS for name in names.split()}
PRIVATE = re.compile(r"(?i)\b(?:\d{1,3}\.){3}\d{1,3}\b|[a-z]:[\\/]|\\\\|(?<!\w)/(?:home|tmp|users|mnt|etc|opt|var|root|private|usr)/|-----BEGIN .*KEY|\b(?:ghp_|sk-|AKIA)[\w-]{12,}|(?:token|password|secret)\s*[:=]\s*\S+")
DROP = set("command command_line commands output session session_id visitor visitor_id rows password secret token salt source_ip key".split())


def clean(value):
    """Drop private fields, including positional trace rows containing identifiers."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k.lower() not in DROP and not PRIVATE.search(k)}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, str) and PRIVATE.search(value):
        return "[withheld]"
    return value


def labels(source=None, scope="UNKNOWN", status="NOT RUN", profile="UNKNOWN"):
    return dict(scope=scope, status=status, source_file=source, policy_profile=profile,
                demo_label="LAB_DEMO_NOT_ML" if profile == "LAB_DEMO" else None)


def evidence(item, root=ROOT):
    entry = CATALOG.get(item)
    if not entry:
        return 404, {**labels(), "data": None, "empty": "Unknown evidence ID"}
    source, scope, status = entry
    path = root / source
    meta = labels(source, scope, status)
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
            raise ValueError
        with resolved.open("rb") as stream:
            raw = stream.read(CAP + 1)
        if len(raw) > CAP:
            raise ValueError
        content = raw.decode("utf-8")
        kind = "markdown" if path.suffix == ".md" else "json"
        data = ({"text": "\n".join(clean(line) for line in content.split("\n"))}
                if kind == "markdown" else clean(json.loads(content)))
    except (OSError, ValueError, RuntimeError):
        return 404, {**meta, "status": "NOT RUN", "data": None, "empty": "Evidence unavailable"}
    if isinstance(data, dict):
        if data.get("passed") is False or data.get("pure") is False:
            meta["status"] = "INVALID"
        profile = data.get("policy_profile")
        if source.startswith("results/demo/") and data.get("label") == "LAB_DEMO_NOT_ML":
            profile = "LAB_DEMO"
        if profile in ("DEFAULT", "LAB_DEMO"):
            meta.update(labels(source, scope, meta["status"], profile))
    return 200, {**meta, "id": item, "title": item.replace("_", " "), "kind": kind, "data": data}


def response(path, root=ROOT):
    if path == "/api/progress":
        code, payload = evidence("progress", root)
        return code, {**payload, "note": "Weighted checklist of project work, not a performance measure."}
    if path == "/api/evidence/index":
        items = []
        for item in CATALOG:
            code, payload = evidence(item, root)
            if code == 200:
                data = payload.pop("data")
                items.append({**payload, "summary_fields": list(data) if isinstance(data, dict) else []})
        return 200, {**labels("dashboard/evidence.py", status="done" if items else "NOT RUN"),
                     "items": items, "empty": None if items else "Evidence unavailable"}
    return evidence(path.removeprefix("/api/evidence/"), root)
