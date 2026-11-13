"""Finalize P0 measurements and render the audit without hand-entered results."""
import csv
import json
import statistics
import hashlib
import importlib.metadata
from pathlib import Path
from analysis.exp0_robustness import component_name, render
from analysis.exp0_rules import PurePythonLogisticRegression, recall_at_budget
from analysis.exp0_train import load_parquet_as_dict_records, filter_prefix_determined_exclusions, evaluate_gate0_decision_rule, write_exp0_result_md


def main():
    root = Path('results/exp0')
    null = json.loads((root / 'permutation_null.json').read_text())
    assert null['status'] == 'COMPLETE'
    values = [r['recall'] for r in null['permutations']]
    null['empirical_upper_tail_plus_one'] = (1 + null['at_or_above_observed']) / (1 + len(values))
    null['standard_deviation'] = statistics.stdev(values)
    (root / 'permutation_null.json').write_text(json.dumps(null, indent=2) + '\n')
    (root / 'PERMUTATION_NULL.md').write_text(
        '# Training-label permutation diagnostic\n\n' +
        f"Observed recall: {null['observed_recall']:.8f}; completed permutations: {len(values)}.\n\n" +
        f"Null mean {null['mean']:.8f}, standard deviation {null['standard_deviation']:.8f}, range [{min(values):.8f}, {max(values):.8f}].\n\n" +
        f"At or above observed: {null['at_or_above_observed']}; empirical upper-tail plus-one fraction: {null['empirical_upper_tail_plus_one']:.8f}.\n\n" +
        null['caveat'] + '\n\nThe null is not near the budget. Constant-prevalence training produces the same ranking: see P0_REPORT.md.\n', encoding='utf-8')
    diag = json.loads((root / 'bootstrap_diagnostics.json').read_text())
    diag['method_caveat'] = 'Point estimates and bootstrap draws share expected uniform boundary-tie capture. Cluster concentration still limits interpretation.'
    (root / 'bootstrap_diagnostics.json').write_text(json.dumps(diag, indent=2) + '\n')
    robust = json.loads((root / 'robustness.json').read_text())
    model, meta = PurePythonLogisticRegression.load_json(root / 'model_s3.json')
    records = filter_prefix_determined_exclusions(load_parquet_as_dict_records(root / 'test.parquet'), 'S3')[0]
    scores = model.predict_proba([[float(r[f] or 0) for f in meta['features']] for r in records])
    for name, row in robust['component_recall'].items():
        row['recall'] = recall_at_budget(scores, [int(component_name(r) == name) for r in records], .1)
        row['captured'] = row['recall'] * row['positives']
    robust['limitations'][-1] = 'Point and bootstrap use expected uniform boundary-tie capture; bootstrap seed 20261111.'
    (root / 'robustness.json').write_text(json.dumps(robust, indent=2) + '\n')
    render()
    before = {r['stage']: r for r in csv.DictReader((root / 'table_before_p0.csv').open())}
    after = list(csv.DictReader((root / 'table.csv').open()))
    summary = json.loads((root / 'rules_summary.json').read_text())
    stages = {r['stage']: {'delta': float(r['delta_k']), 'ci_lower': float(r['ci_lower']),
              'ci_upper': float(r['ci_upper']), 'min_size_met': r['min_size_met'] == 'True', 'ml_status': 'COMPLETE'}
              for r in after if r['stage'] in ('S1', 'S2', 'S3')}
    gate = evaluate_gate0_decision_rule(stage_results=stages)
    assert gate['gate0_outcome'] == summary['gate0']['gate0_outcome']
    summary['gate0'] = gate
    (root / 'rules_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    report_rows = [dict(r) for r in after]
    for row in report_rows:
        if row['stage'] in stages:
            row['ci_lower'], row['ci_upper'] = float(row['ci_lower']), float(row['ci_upper'])
    write_exp0_result_md(root / 'EXP0_RESULT.md', gate, report_rows, summary['counts'])
    audit = json.loads((root / 'metric_audit_after.json').read_text())
    lines = ['# P0 metric and permutation audit', '',
        'The old seeded metric selected exactly the ceiling budget and passed the new invariants before modification. No tie-bin overflow was found. Its point estimator differed from the tie-averaged bootstrap. Both now use one expected uniform boundary-tie estimator, selected in DECISIONS.md before rerunning.', '',
        'Root-cause evidence: the fallback optimizer starts with zero weights and intercept (initial probability one-half). With rare training positives, finite gradient iterations give common counters persistent negative weights. A diagnostic fit using the same training prevalence for every label reproduces the shuffled model recall, without any label-to-row association. Thus permuting training labels does not make test rankings uniformly random. This control is not an official candidate; the optimizer, grid, labels and splits were not changed.', '',
        '| Stage | Old rule | New rule | Old ML | New ML | Old delta | New delta | Old CI | New CI |',
        '|---|---|---|---|---|---|---|---|---|']
    for row in after:
        old = before[row['stage']]
        lines.append(f"| {row['stage']} | {old['best_rule_test_recall']} | {row['best_rule_test_recall']} | {old['ml_test_recall']} | {row['ml_test_recall']} | {old['delta_k']} | {row['delta_k']} | [{old['ci_lower']}, {old['ci_upper']}] | [{row['ci_lower']}, {row['ci_upper']}] |")
    lines += ['', 'Exact generated Gate 0 result:', '```json', json.dumps(gate, indent=2), '```', '',
        'Numerical PASS does not establish validated early signal. The shuffled-label control outperforms the observed model, the candidate family set is incomplete, clusters are concentrated, and aggregate counters do not establish temporal availability.', '',
        'Null distribution and descriptive empirical tail (not a calibrated significance test):', '```json',
        json.dumps({k: v for k, v in null.items() if k not in ('permutations', 'seeds')}, indent=2), '```', '',
        'Score-bin and exact-budget diagnostics:', '```json', json.dumps(audit, indent=2), '```', '',
        'TODO(verify): optimizer convergence and a scientifically valid clustered null require a separately authorized experiment; event-level availability is evaluated separately in P4.']
    (root / 'P0_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    manifest_path = Path('results/MANIFEST.json')
    manifest = json.loads(manifest_path.read_text())
    manifest['library_versions'] = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}
    manifest['random_seeds']['permutation_seeds'] = null['seeds']
    manifest['metric_estimator'] = 'Expected uniform boundary ties; compatibility seed ignored'
    manifest['audit_source_sha256'] = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in Path('analysis').glob('*.py') if not p.name.startswith('test_')}
    for p in [*root.glob('*.json'), *root.glob('*.md'), root / 'table.csv', Path('EXP0_RESULT.md')]:
        manifest['result_artifacts'][p.as_posix()] = {'md5': hashlib.md5(p.read_bytes()).hexdigest(),
            'eval_ref': 'P0 rerun or retained reporting-only artifact; see P0_REPORT.md'}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(gate))


if __name__ == '__main__':
    main()
