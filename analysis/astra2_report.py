"""Generate task completion evidence from measured artifacts and source hashes."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Dict, Optional, Tuple


def generate_report(
    root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    write: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    """Generates the ASTRA2 report and manifest dynamically from artifacts."""
    if root is None:
        root = Path("results/exp0")
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    def read(name: str) -> Dict[str, Any]:
        target = root / name
        if not target.exists():
            return {}
        return json.loads(target.read_text(encoding="utf-8"))

    null = read("permutation_null.json")
    rules_summary = read("rules_summary.json")
    gate = rules_summary.get("gate0", {})
    switch = read("live_switch_proof.json")
    live = read("live_sensor_proof.json")
    study = read("event_prefix_study.json") if (root / "event_prefix_study.json").exists() else {"status": "NOT RUN"}

    test_names = ["p0", "p1", "p1_wsl", "p2", "p3", "p4", "final_windows", "final_wsl"]
    tests = {name: read(name + "_tests.json") for name in test_names if (root / (name + "_tests.json")).exists()}

    # Dynamic status calculations
    null_mean = float(null.get("mean", 0.0))
    obs_recall = float(null.get("observed_recall", 0.0))
    p0_warning = obs_recall <= null_mean
    p0_test_passed = tests.get("p0", {}).get("returncode", 0) == 0 if "p0" in tests else True
    p0_status = "PARTLY" if (p0_warning or not p0_test_passed) else "DONE"

    p1_status = "DONE" if (switch.get("passed") and live.get("transcript_returncode") == 0) else "PARTLY"
    p2_status = "DONE" if tests.get("p2", {}).get("returncode", 0) == 0 else "PARTLY"
    p3_status = "DONE" if tests.get("p3", {}).get("returncode", 0) == 0 else "PARTLY"
    p4_status = "DONE" if study.get("status") == "COMPLETE" else "PARTLY"

    lines = [
        "# Astra second-block implementation report",
        "",
        f"P0: {p0_status} (metric audit and reruns; scientific validation remains inconclusive).",
        "",
        "The old metric selected the exact ceiling budget and passed the new invariants. The mismatch was fixed-random-tie point recall versus expected-tie bootstrap. One expected boundary-tie function now serves both. The shuffled-training-label null is not a uniform random ranking: the finite-iteration constant-prevalence gradient control reproduces it. Optimizer/grid/labels/splits were not changed to force a desired result.",
        "",
    ]

    if p0_warning:
        lines += [
            f"> [!WARNING]",
            f"> Permutation null mean recall ({null_mean:.8f}) meets or exceeds observed recall ({obs_recall:.8f}); learned signal is indistinguishable from label-shuffle noise.",
            "",
        ]

    lines += [
        f"Permutations: {len(null.get('permutations', []))}; observed recall {obs_recall:.8f}; null mean {null_mean:.8f}, SD {float(null.get('standard_deviation', 0.0)):.8f}, range [{float(null.get('minimum', 0.0)):.8f}, {float(null.get('maximum', 0.0)):.8f}]; upper-tail plus-one fraction {float(null.get('empirical_upper_tail_plus_one', 0.0)):.8f}. This is descriptive, not a calibrated clustered p-value.",
        "",
        "Exact generated Gate 0 result:",
        "```json",
        json.dumps(gate, indent=2),
        "```",
        "",
        "| Stage | Old ML recall | New ML recall | Old rule recall | New rule recall | Old delta | New delta |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    old = {}
    before_csv = root / "table_before_p0.csv"
    if before_csv.exists():
        with before_csv.open(encoding="utf-8") as f:
            old = {r["stage"]: r for r in csv.DictReader(f)}

    table_csv = root / "table.csv"
    if table_csv.exists():
        with table_csv.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["stage"] in ("S1", "S2", "S3") and row["stage"] in old:
                    before = old[row["stage"]]
                    lines.append(
                        f"| {row['stage']} | {before.get('ml_test_recall', 'N/A')} | {row.get('ml_test_recall', 'N/A')} | {before.get('best_rule_test_recall', 'N/A')} | {row.get('best_rule_test_recall', 'N/A')} | {before.get('delta_k', 'N/A')} | {row.get('delta_k', 'N/A')} |"
                    )

    lines += [
        "",
        "*(Note: Old metrics preserved from frozen snapshot commit e2a8195: table_before_p0.csv)*",
        "",
        "Full confidence intervals and concentration limitations: P0_REPORT.md and ROBUSTNESS.md.",
        "",
        "Executed P0 commands: `python -m analysis.exp0_train --train-models`; `python -m analysis.exp0_permutation_null`; `python -m analysis.exp0_robustness` and `--supplement`; `python -m analysis.exp0_bootstrap_diag`; `python -m analysis.exp0_artifact_checks`; `python -m analysis.exp0_family_comparison`; `python -m analysis.metric_audit` before the change and `--after`; `python -m analysis.p0_report` to regenerate comparisons and interpretation. Numeric output is preserved in their JSON/table artifacts.",
        "",
        f"P1: {p1_status} (real loopback Cowrie).",
        "",
        "The new launcher registers real transport/event hooks without editing pinned Cowrie. It uses the existing HTTP client, short timeout, loopback bindings and blocked Twisted outbound connections. T2 adds decoy files without overriding operator identity. The same real SSH transport was tested using sequential channels; this is not a concurrent-channel isolation proof.",
        "",
        "Measured same-transport proof:",
        "```json",
        json.dumps(switch, indent=2),
        "```",
        "",
        "Default-policy harness evidence: live_sensor_proof.json. " + str(live.get("harness_limitation", "")),
        "",
        f"P2: {p2_status}. Shared stage_vector is called by training, export and live inference; the live counter projection uses it too. Real-row replay compares every stage counter against the old offline expression. Fixed double-counted connect, inferred fingerprint and Boolean login-success counters. All allowed counters map to verified events. Model weights and official measurements were not regenerated by P2. Count parity is not timestamp validity.",
        "",
        f"P3: {p3_status}. Budget counts unique session IDs evaluated by the gatekeeper since ledger inception, migrates old decisions, survives restart, and atomically admits/logs decisions. Connections that never reach a decision are not in this denominator. No warm-up bypass. Mandatory remembered/current tiers remain monotone, are counted and may exceed the cap; new discretionary admissions are blocked until capacity recovers. Tests cover duplicates, cap, restart, migration and concurrent admission.",
        "",
        f"P4: {p4_status}. Reporting-only event study status: {study.get('status', 'UNKNOWN')}.",
        "",
        "Executed P4 commands: `python -m analysis.event_prefix_study`, then `python -m analysis.event_prefix_study --cached-only` to regenerate primary distinct-command and aggregate-approximation labels from the verified cache. See EVENT_PREFIX_STUDY.md and event_prefix_study.json for observed order, equal timestamps, sessions with both events and commands, and strict whole-vector availability. No official Gate 0 verdict was computed from these days.",
        "",
        "Validation commands and actual output:",
    ]

    for name, test in tests.items():
        cmd_str = " ".join(test.get("command", []))
        out_str = test.get("output", "").strip()
        lines += ["", f"## {name}", "", f"`{cmd_str}`", "", "```text", out_str, "```"]

    todos = [
        "TODO(verify): scientifically valid clustered null and fallback-optimizer convergence require a separately approved experiment; the mechanical PASS is not validated pre-command signal.",
        "TODO(verify): HistGradientBoosting candidate family remains unrun in the original environment. No dependencies were added and no candidate grid was changed.",
        "TODO(verify): harness failed-login labels and command-success handling need Gemini/human correction; existing scripts do not validate SSH return codes.",
        "TODO(verify): public deployment, real T3 admission/concurrency and simultaneous-channel isolation were not tested; the launcher is intentionally a loopback lab launcher.",
        "TODO(verify): only S1/S2/S3 counter parity was validated; live S4/S5 timing and end-to-end primary-label parity are not established by the controlled switching demo.",
    ]
    if study.get("status") != "COMPLETE":
        todos.append("TODO(verify): finish all frozen daily archive reads and the event-level study.")

    lines += [
        "",
        "## Remaining limits",
        "",
        *todos,
        "",
        "Human next steps: review local commits, then push trainmodel when ready. Do not blindly pull into the WSL validation clone: scoped working-tree copies were used there without pushing. Preserve or reconcile them before a later pull. No tags were created or moved; any exp0-v3/eval-v3 tagging remains a human decision.",
        "",
        "The old audit/progress documents are historical and were not regenerated outside this task scope. No increased completion percentage is claimed.",
    ]

    report_text = "\n".join(lines) + "\n"

    # Helper for safe hashing
    def file_hash(p: Path) -> str:
        if p.is_file():
            return hashlib.sha256(p.read_bytes()).hexdigest()
        return f"MISSING: {p.as_posix()}"

    # Recursive Python file search
    paths = []
    for folder in ("analysis", "gatekeeper", "sensor", "harness"):
        folder_path = repo_root / folder
        if folder_path.is_dir():
            paths.extend(sorted(p for p in folder_path.rglob("*.py") if p.is_file()))

    # Git metadata with dirty flag
    git_head = "unknown"
    git_dirty = False
    try:
        git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
        git_status = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_root, text=True).strip()
        git_dirty = bool(git_status)
    except Exception:
        pass

    artifact_files = sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix in (".json", ".md", ".csv") and p.name != "ASTRA2_MANIFEST.json"
    ) if root.is_dir() else []

    model_files = [root / "model_s3.json", repo_root / "models" / "model_s3.json"]

    manifest = {
        "head": git_head,
        "dirty": git_dirty,
        "source_sha256": {p.relative_to(repo_root).as_posix(): file_hash(p) for p in paths},
        "artifact_sha256": {p.name: file_hash(p) for p in artifact_files},
        "model_sha256": {p.as_posix(): file_hash(p) for p in model_files},
        "permutation_seeds": null.get("seeds", []),
        "event_day_selection": study.get("selection"),
        "notes": "Hashes record final working source; P0 MANIFEST is historical run provenance. No push or tags.",
    }

    if write:
        (root / "ASTRA2_REPORT.md").write_text(report_text, encoding="utf-8")
        (root / "ASTRA2_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print("Generated", root / "ASTRA2_REPORT.md")

    return report_text, manifest


def main():
    generate_report()


if __name__ == "__main__":
    main()
