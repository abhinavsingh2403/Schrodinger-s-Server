"""Generate the audit handoff from executed checks, source and measured artifacts.

This refreshes presentation only; official statistical results come from exp0_train.
"""
import ast
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from analysis import exp0_train
from analysis.exp0_robustness import render
from analysis.progress_accounting import main as progress

ROOT = Path('results/exp0')


def verify_pins():
    """Query package metadata without downloading or installing distributions."""
    report = {'python': sys.version, 'packages': {}}
    for line in Path('requirements.txt').read_text().splitlines():
        if '==' not in line or line.startswith('#'):
            continue
        name, pinned = line.split('==')
        result = subprocess.run([sys.executable, '-m', 'pip', 'index', 'versions', name], capture_output=True, text=True)
        available = next((s.partition(':')[2].strip().split(', ') for s in result.stdout.splitlines() if s.startswith('Available versions:')), [])
        report['packages'][name] = {'pin': pinned, 'installed': importlib.metadata.version(name),
                                   'index_exit_code': result.returncode, 'pin_listed': pinned in available,
                                   'source': f'https://pypi.org/simple/{name.lower()}/'}
    (ROOT / 'pins_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


def verify_tests():
    """Capture real suite output; never substitute an expected count."""
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-ra'], capture_output=True, text=True)
    (ROOT / 'audit_tests.json').write_text(json.dumps({'command': 'python -m pytest -q -ra',
        'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}, indent=2) + '\n')
    print(result.stdout)
    if result.returncode:
        raise SystemExit(result.returncode)


def refresh_reports():
    """Re-render official reports from the regenerated official CSV, preserving metrics."""
    summary = json.loads((ROOT / 'rules_summary.json').read_text())
    rows = list(csv.DictReader((ROOT / 'table.csv').open()))
    for row in rows:
        for key, value in list(row.items()):
            if value in ('True', 'False'):
                row[key] = value == 'True'
            else:
                try:
                    row[key] = json.loads(value)
                except (ValueError, TypeError):
                    pass
    exp0_train.write_table_csv(ROOT / 'table.csv', rows)
    exp0_train.write_exp0_result_md(ROOT / 'EXP0_RESULT.md', summary['gate0'], rows, summary['counts'], datetime.now(timezone.utc))
    for filename in ('rules.json', 'rules_summary.json'):
        data = json.loads((ROOT / filename).read_text())
        stages = data.get('stages', data)
        for stage in ('S1', 'S2', 'S3'):
            stages[stage]['proxy_notice'] = 'R5_rarity: PROXY (aggregate counter, not version string); R3 not stage-valid; hassh rarity not evaluated'
        (ROOT / filename).write_text(json.dumps(data, indent=2) + '\n')
    exp0_train.write_manifest_json(Path('results/MANIFEST.json'), summary['counts'])
    manifest_path = Path('results/MANIFEST.json')
    manifest = json.loads(manifest_path.read_text())
    manifest['library_versions'] = {dist.metadata['Name']: dist.version for dist in importlib.metadata.distributions()}
    manifest['audit_source_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted(Path('analysis').glob('exp0_*.py'))}
    for p in sorted(ROOT.glob('*.json')) + [ROOT / 'ROBUSTNESS.md', Path('models/model_s3.json')]:
        manifest['result_artifacts'][p.as_posix()] = {'md5': exp0_train.compute_file_md5(p), 'eval_ref': 'Audit output or unchanged input; see audit report'}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')


def main():
    progress()
    render()
    robustness = json.loads((ROOT / 'robustness.json').read_text())
    checks = json.loads((ROOT / 'artifact_checks.json').read_text())
    boot = json.loads((ROOT / 'bootstrap_diagnostics.json').read_text())
    events = json.loads((ROOT / 'event_order.json').read_text())
    summary = json.loads((ROOT / 'rules_summary.json').read_text())
    tests = json.loads((ROOT / 'audit_tests.json').read_text())
    progress_data = json.loads((ROOT / 'progress.json').read_text())
    pins = json.loads((ROOT / 'pins_audit.json').read_text())
    claims_path = Path('CLAIMS.md')
    claims = claims_path.read_text(encoding='utf-8')
    claim_marker = '## Audit package-index verification'
    if claim_marker in claims:
        claims = claims[:claims.index(claim_marker)].rstrip() + '\n'
    claim_lines = [claim_marker, '', 'Verified by the executed pip index queries recorded in results/exp0/pins_audit.json; no installation was performed.', '',
                   '| Package version | Source | Status |', '|---|---|---|']
    for name, evidence in pins['packages'].items():
        status = '[V] observed in package-index output' if evidence['pin_listed'] else '[U] not verified'
        claim_lines.append(f"| {name} {evidence['pin']} exists | {evidence['source']} | {status} |")
    claim_lines += ['', 'Event-log ordering observations are recorded by analysis/exp0_event_order.py against the D1 archive URL above. They describe a partial sample, not verified complete event-prefix availability.', '']
    claims_path.write_text(claims + '\n' + '\n'.join(claim_lines), encoding='utf-8')
    rows = list(csv.DictReader((ROOT / 'table.csv').open()))
    s3 = next(r for r in rows if r['stage'] == 'S3')
    tasks = [
        ('T1', 'PARTLY', 'python -m analysis.exp0_robustness; python -m analysis.exp0_robustness --supplement; python -m analysis.exp0_family_comparison', 'Baseline sensitivity is ' + robustness['verdict'] + '; gradient-boosting family unavailable. See ROBUSTNESS.md.'),
        ('T2', 'DONE', 'python -m analysis.exp0_bootstrap_diag; python -m analysis.exp0_train --train-models', 'Fixed unordered cluster iteration; official results regenerated. Concentration and weighted sensitivities recorded.'),
        ('T3', 'PARTLY', 'python -m analysis.exp0_artifact_checks; python -m analysis.exp0_event_order', 'Shuffle sanity check fails; parameter events observed after commands. Size/var ordering remains unverified.'),
        ('T4', 'DONE', 'python -m pytest -q analysis/test_exp0_report_hygiene.py', 'Generated CSV, JSON and reports explicitly mark aggregate proxies without changing scores.'),
        ('T5', 'DONE', 'python -m analysis.exp0_audit_ledger', 'Tag timestamps, target commits and historical stage rows copied from Git into DECISIONS.md.'),
        ('T6', 'DONE', 'python -m analysis.progress_accounting', f"Weighted completion {progress_data['percentage']:.1f}% from the required checklist."),
        ('T7', 'PARTLY', 'python -m analysis.exp0_audit_report --verify-pins', 'Pins match the inspected project environment and index. Human must confirm it was the original run environment.'),
        ('T8', 'DONE', 'python -m analysis.exp0_audit_report --refresh-reports', 'UTC run date; generated root and results reports are identical.'),
        ('T9', 'PARTLY', 'python -m pytest -q gatekeeper/test_model_inference_parity.py gatekeeper/test_policy.py sensor/test_adaptive_server.py', 'Local checks pass; Linux collection fails on missing lark; dashboard truthfulness checks fail.'),
    ]
    lines = ['## Current audit findings (supersedes earlier performance claims)', '',
             '| Task | Status | Command | Evidence / limitation |', '|---|---|---|---|']
    lines += [f'| {task} | {status} | `{command}` | {evidence} |' for task, status, command, evidence in tasks]
    lines += ['', '### Executed test suite', '', '```text', tests['stdout'].strip(), '```', '',
              'Initial default Python could not import pytest; the project virtual environment was used. Restricted local HTTP access initially failed; the permitted loopback test run succeeded.', '',
              '### Scientific interpretation', '',
              f"Reporting-only baseline verdict: **{robustness['verdict']}**. Best test rule: {robustness['test_selected_baseline']}; official selection remains validation-based.",
              'Bootstrap verdict: both a reproducibility bug and a strong data-concentration effect. Sorting cluster IDs fixes process-dependent draws; the broad S3 distribution persists.',
              'S3 cluster diagnostics: `' + json.dumps(boot['stages']['S3']) + '`',
              'S2 exact-zero bootstrap draws: ' + str(boot['stages']['S2']['full']['exact_zero']) + '. Equal capture occurs in these draws; this does not mean the two score vectors are identical.',
              f"Shuffle test recall: {checks['checks']['shuffle']['test_recall']:.8f}. This fails the requested near-budget sanity check; it is a leakage/bug signal requiring investigation, not by itself proof of leakage.",
              f"Removing session parameters gives recall {checks['checks']['cnt_session_params']['test_recall']:.8f}; removing all channel groups gives {checks['checks']['all_three']['test_recall']:.8f}.",
              'Transfer-labelled sessions account for almost all captured positives; direct-tcpip-only sessions have no captured positives. This supports transfer-artifact discrimination, not a broad interactive-attacker claim.',
              'Event-order evidence: `' + json.dumps(events) + '`', '',
              '### Official result and viva-safe statement', '',
              'Gate 0 Outcome: ' + summary['gate0']['gate0_outcome'] + ' - ' + summary['gate0']['interpretation'], '',
              f"1. The regenerated aggregate-only evaluation reports {summary['gate0']['gate0_outcome']} at S3, with ML recall {s3['ml_test_recall']} and baseline recall {s3['best_rule_test_recall']}.",
              '2. The fixed day split is a nine-day sample, and source-IP purging introduces survivorship bias.',
              '3. The result followed an exploratory path with test results visible, so it is exploratory-confirmatory.',
              '4. The gain mainly concerns transfer-labelled sessions; shuffled-label and event-order checks undermine a causal pre-command interpretation.',
              '5. Event-level prefix validation and unresolved integration checks are required before stronger scientific or deployment claims.', '',
              '### Integration audit', '',
              '- Parity: PASS for the existing handcrafted counter/event fixture and model scores; it does not read a parquet row, compare every feature, or establish one shared extraction module.',
              '- Budget: PASS for the existing exhaustion fixture. The counter is lifetime decisions per policy instance, resets on restart, permits a warmup and memory/current-tier exceptions, and does not count unique sessions. T3 takes another branch.',
              '- Decision scoring: only S3 uses the saved model. Other stages and exception fallbacks use placeholder constants, not fitted rule probabilities. Source-extracted score-return statements:', '```python']
    source = Path('gatekeeper/decision_api.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'score_features')
    for node in ast.walk(method):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple) and isinstance(node.value.elts[0], ast.Constant):
            lines.append(ast.get_source_segment(source, node))
    lines.extend(line.strip() for line in source.splitlines() if 'calibrated_th = float(metadata.get(' in line)
    lines += ['```',
              '- Model-loading threshold defaults and zero-score exception paths are also constants; see gatekeeper/decision_api.py. They are not empirical probabilities.',
              '- Linux: attempted `wsl -d kali-linux --cd <repo> -- python3 -m pytest -q sensor/test_spike_s1_poc.py sensor/test_adaptive_server.py`; collection failed with `ModuleNotFoundError: No module named lark`. Integration with real Cowrie did not execute successfully in this task. Windows skips Twisted-dependent tests.',
              '- Dashboard: FAIL. JSON and decision-database sources coexist with numeric fallbacks, static fabricated live rows and random simulated updates in dashboard/templates/index.html. Panel labelling is not consistently tied to actual provenance.',
              '- Detector: harness/detector_runner.py correctly says EVAL H4 NOT YET EVALUATED; a visible dashboard notice now repeats that status and identifies synthetic demonstration data. Real held-out replay is NOT DONE: harness/replay/replay_engine.py builds SYNTHETIC command templates from counters.', '',
              '### TODO(verify) and human next steps', '',
              '- Investigate shuffled-label ranking and validate all channel counters against complete event-level prefixes; size/var ordering was not observed in the small sample.',
              '- Review tie-bin averaging versus the fixed-random-tie point statistic; no estimator redesign was made.',
              '- Confirm original run environment and exact saved-model identity beyond matching recall; review the omitted gradient-boosting family and ignored grid dimensions without retuning on test.',
              '- Install/reconcile the approved pinned Linux dependencies separately, then rerun real Cowrie integration. No packages were installed in this audit.',
              '- Repair dashboard synthetic/live labelling and session-level budget accounting in separate reviewed work.',
              '- Review the commits, push manually, and only then consider exp0-v3/eval-v3. No tags or remote branches were changed.', '']
    parity_source = Path('gatekeeper/test_model_inference_parity.py').read_text(encoding='utf-8')
    parity_assertion = next(line.strip() for line in parity_source.splitlines() if 'assert abs(prob_offline - prob_live)' in line)
    policy_source = Path('gatekeeper/test_policy.py').read_text(encoding='utf-8')
    policy_test = next(node for node in ast.walk(ast.parse(policy_source)) if isinstance(node, ast.FunctionDef) and node.name == 'test_policy_budget_ceiling_enforcement')
    lines += ['### Executed integration-test evidence', '', 'Parity tolerance assertion from the executed test:',
              '```python', parity_assertion, '```', '', 'Budget exhaustion fixture from the executed test:',
              '```python', ast.get_source_segment(policy_source, policy_test), '```', '']
    report = '\n'.join(lines)
    (ROOT / 'AUDIT.md').write_text(report, encoding='utf-8')
    handoff = Path('HANDOFF.md')
    text = handoff.read_text(encoding='utf-8')
    marker = '## Current audit findings'
    if marker in text:
        text = text[:text.index(marker)]
    # Keep the required checklist; replace stale claims and invented progress/latency narrative.
    stop = text.index('<!-- GENERATED PROGRESS END -->') + len('<!-- GENERATED PROGRESS END -->')
    handoff.write_text(text[:stop] + '\n\n' + report, encoding='utf-8')
    readme = Path('README.md')
    text = readme.read_text(encoding='utf-8')
    updated = []
    for line in text.splitlines():
        if line.startswith('| **O3: Experiment 0'):
            line = f"| **O3: Experiment 0 (`EXPERIMENT0.md`)** | Core (Gate 0) | **PARTIAL: {summary['gate0']['gate0_outcome']} at S3** | ML recall {s3['ml_test_recall']}; rule recall {s3['best_rule_test_recall']}; adjusted CI [{s3['ci_lower']}, {s3['ci_upper']}]. Exploratory-confirmatory; shuffle and prefix-validity checks unresolved. See [audit](results/exp0/AUDIT.md). |"
        elif line.strip().startswith('* *Outcome*: At Stage S3'):
            line = f"   * *Outcome*: Regenerated S3 ML recall {s3['ml_test_recall']} vs rule {s3['best_rule_test_recall']}, delta {s3['delta_k']}, adjusted CI [{s3['ci_lower']}, {s3['ci_upper']}]. The numerical outcome remains {summary['gate0']['gate0_outcome']}; the transfer-driven gain and failed shuffle/prefix checks limit interpretation."
        elif line.strip().startswith('* *Action Completed*: Rewrote `paired_cluster_bootstrap_delta()`'):
            line = '   * *Action Completed*: Bootstrap includes all stage-specific source clusters and recalculates the budget per draw. This audit also fixes process-dependent cluster ordering; see generated concentration and sensitivity diagnostics.'
        elif line.startswith('2. **Exported Model Metric Reconciliation**'):
            line = '2. **Exported Model Provenance**: Applying the same S3 reach filter reproduces the official recall from the saved export. Its calibration still uses unfiltered validation data; review exact model identity and serving calibration separately.'
        line = line.replace(' with 1.60 $\\mu$s pure ML inference.', '; current test outcomes and limitations are in HANDOFF.md.')
        line = line.replace('seal the leak-free baseline code and results', 'record the reviewed exploratory audit and its unresolved limitations')
        updated.append(line)
    readme.write_text('\n'.join(updated) + '\n', encoding='utf-8')
    print('Generated HANDOFF.md and results/exp0/AUDIT.md')


if __name__ == '__main__':
    if '--verify-pins' in sys.argv:
        verify_pins()
    elif '--verify-tests' in sys.argv:
        verify_tests()
    elif '--refresh-reports' in sys.argv:
        refresh_reports()
    else:
        main()
