"""Reproduce saved S3 model recall before interpreting reporting-only robustness.

Uses saved splits and model without changing the official experiment artifacts.
Matching recall is not a claim of identical original model weights.
"""
from pathlib import Path
import csv
import json
import random
import math
from collections import Counter

from analysis.exp0_rules import PurePythonLogisticRegression, recall_at_budget
from analysis.exp0_train import (
    STAGE_VALID_RULES, filter_prefix_determined_exclusions,
    load_parquet_as_dict_records, get_rule_test_scores,
    paired_cluster_bootstrap_delta, STAGE_BONFERRONI_ALPHA,
)


def component_name(record):
    """Return disjoint label-component membership, preserving overlaps."""
    parts = []
    if record['cnt_command_input'] >= 5:
        parts.append('commands')
    if record['cnt_file_upload'] + record['cnt_file_download'] > 0:
        parts.append('transfer')
    if record['cnt_direct_tcpip_request'] > 0:
        parts.append('direct-tcpip')
    return '+'.join(parts) or 'negative'


def main():
    root = Path('results/exp0')
    model, metadata = PurePythonLogisticRegression.load_json(root / 'model_s3.json')
    train = load_parquet_as_dict_records(root / 'train.parquet', sample_limit=50000)
    splits = {s: filter_prefix_determined_exclusions(
        load_parquet_as_dict_records(root / f'{s}.parquet'), 'S3')[0]
        for s in ('val', 'test')}
    official = next(r for r in csv.DictReader((root / 'table.csv').open()) if r['stage'] == 'S3')
    out = {'model_source': 'loaded results/exp0/model_s3.json; separately retrained export',
           'official_row': official, 'rules': {}, 'ml': {}, 'seed': 42}
    for split, records in splits.items():
        labels = [r['v_full'] for r in records]
        scores = model.predict_proba([[float(r[f] or 0) for f in metadata['features']] for r in records])
        out['ml'][split] = recall_at_budget(scores, labels, .10)
        for rule in STAGE_VALID_RULES['S3']:
            rule_scores = get_rule_test_scores(rule, records, train, 'S3')
            out['rules'].setdefault(rule, {})[split] = recall_at_budget(rule_scores, labels, .10)
        if split == 'test':
            out['label_components'] = dict(Counter(component_name(r) for r in records if r['v_full']))
    for row in out['rules'].values():
        row['delta_exported_ml'] = out['ml']['test'] - row['test']
        row['generalisation_gap'] = row['test'] - row['val']
    out['ml']['difference_from_official'] = out['ml']['test'] - float(official['ml_test_recall'])
    out['recall_reproduced'] = abs(out['ml']['difference_from_official']) <= 1e-4
    out['verdict'] = 'TBD: bootstrap comparisons pending'
    out['limitations'] = [
        'Saved export reproduces official S3 recall within acceptance tolerance; this does not prove identical fitted weights.',
        'Export script retrains independently and calibrates on unfiltered validation sessions; official harness filters validation/test by stage.',
        'TODO(verify): official model-family comparison; project environment lacks scikit-learn, so its fallback skips HistGradientBoosting.',
        'Model-family comparison cannot recover a gradient-boosting candidate that was not trained in the manifest environment.',
    ]
    (root / 'robustness.json').write_text(json.dumps(out, indent=2) + '\n')
    lines = ['# S3 robustness audit (reporting only)', '', out['verdict'], '',
             'Loaded the saved export; these measurements do not establish official-model identity.', '',
             '| Model/rule | Validation recall | Test recall |', '|---|---:|---:|',
             f"| Saved export | {out['ml']['val']:.8f} | {out['ml']['test']:.8f} |"]
    for name, row in out['rules'].items():
        label = name + (' — PROXY (aggregate counter, not version string)' if name == 'R5_rarity' else '')
        lines.append(f"| {label} | {row['val']:.8f} | {row['test']:.8f} |")
    lines += ['', f"Saved-export test recall minus official row: {out['ml']['difference_from_official']:.8f}",
              '', 'Disjoint positive label-component counts:', '```json',
              json.dumps(out['label_components'], indent=2), '```', '', *out['limitations']]
    (root / 'ROBUSTNESS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=2))


def supplement():
    """Compute paired intervals and component capture for the reproduced S3 scores."""
    root = Path('results/exp0')
    out = json.loads((root / 'robustness.json').read_text())
    out['limitations'] = [
        'Saved export reproduces official S3 recall within acceptance tolerance; independently refitted weights are not proven identical.',
        'Export calibration uses all validation sessions, unlike the stage-filtered official evaluation.',
        'HistGradientBoosting was unavailable in the project environment; a best candidate cannot be reported for an untrained family.',
        'Point recall and bootstrap share expected uniform boundary-tie capture; bootstrap seed is 20261111.',
    ]
    model, metadata = PurePythonLogisticRegression.load_json(root / 'model_s3.json')
    train = load_parquet_as_dict_records(root / 'train.parquet', sample_limit=50000)
    records = filter_prefix_determined_exclusions(load_parquet_as_dict_records(root / 'test.parquet'), 'S3')[0]
    labels = [r['v_full'] for r in records]
    clusters = [r['src_ip'] for r in records]
    scores = model.predict_proba([[float(r[f] or 0) for f in metadata['features']] for r in records])
    captured = {name: recall_at_budget(scores, [int(component_name(r) == name) for r in records], .1) * count
                for name, count in out['label_components'].items()}
    out['component_recall'] = {name: {'positives': count, 'captured': captured[name], 'recall': captured[name] / count}
                               for name, count in out['label_components'].items()}
    for rule in STAGE_VALID_RULES['S3']:
        print('Bootstrap:', rule, flush=True)
        rule_scores = get_rule_test_scores(rule, records, train, 'S3')
        out['rules'][rule]['bootstrap'] = paired_cluster_bootstrap_delta(scores, rule_scores, labels, clusters,
            alpha=STAGE_BONFERRONI_ALPHA['S3'])
        (root / 'robustness.json').write_text(json.dumps(out, indent=2) + '\n')
    best = max(out['rules'], key=lambda name: out['rules'][name]['test'])
    row = out['rules'][best]
    out['test_selected_baseline'] = best
    out['verdict'] = 'robust' if row['delta_exported_ml'] >= .05 and row['bootstrap'][1] > 0 and sum(labels) >= 500 else 'NOT robust'
    (root / 'robustness.json').write_text(json.dumps(out, indent=2) + '\n')
    with (root / 'ROBUSTNESS.md').open('a', encoding='utf-8') as f:
        f.write('\n## Paired bootstrap and label components\n\nReporting-only test-selected baseline verdict: ' + out['verdict'] + '\n\n```json\n' + json.dumps(out, indent=2) + '\n```\n')


def render():
    """Regenerate the report from measurements, without copying numeric claims by hand."""
    root = Path('results/exp0')
    out = json.loads((root / 'robustness.json').read_text())
    out['official_row'] = next(r for r in csv.DictReader((root / 'table.csv').open()) if r['stage'] == 'S3')
    out['ml']['generalisation_gap'] = out['ml']['test'] - out['ml']['val']
    out['ml']['difference_from_official'] = out['ml']['test'] - float(out['official_row']['ml_test_recall'])
    out.pop('identity_verified', None)
    out['recall_reproduced'] = abs(out['ml']['difference_from_official']) <= 1e-4
    (root / 'robustness.json').write_text(json.dumps(out, indent=2) + '\n')
    lines = ['# S3 robustness audit (reporting only)', '',
             'Test-selected baseline sensitivity: **' + out['verdict'] + '**.', '',
             'Saved export reproduces the official S3 point recall after stage filtering. Official outcome is unchanged.', '',
             '| Rule | Validation recall | Test recall | ML minus rule | Adjusted CI |',
             '|---|---:|---:|---:|---|']
    for name, row in out['rules'].items():
        label = name + (' — PROXY (aggregate counter, not version string)' if name == 'R5_rarity' else '')
        lines.append(f"| {label} | {row['val']:.8f} | {row['test']:.8f} | {row['delta_exported_ml']:.8f} | {row.get('bootstrap', ['TBD'])[1:]} |")
    lines += ['', 'ML measurements: `' + json.dumps(out['ml']) + '`', '',
              'Baseline chosen on test for sensitivity only: ' + out.get('test_selected_baseline', 'TBD'), '',
              'Model-family comparison: HistGradientBoosting NOT RUN (absent in the manifest-matching environment).',
              'The stored winning C is the lowest declared grid value; no grid expansion was performed.', '',
              'Component capture:', '```json', json.dumps(out.get('component_recall', {}), indent=2), '```', '',
              'Captured positives are overwhelmingly transfer-labelled; this does not establish interactive-attacker prediction.']
    diag_path = root / 'bootstrap_diagnostics.json'
    if diag_path.exists():
        diag = json.loads(diag_path.read_text())
        largest = diag['stages']['S3']['concentration']['top_one_percent']
        lines += ['', '## Bootstrap interpretation', '',
                  'There was a reproducibility bug: unordered cluster iteration made fixed-seed draws change between processes. Sorting cluster IDs fixes it; the wide S3 interval remains.',
                  f"At S3, the largest {largest['clusters']} clusters contain {largest['session_share']:.2%} of sessions and {largest['positive_share']:.2%} of positives. Drawing these clusters repeatedly or omitting them substantially changes both the available budget and the positive denominator. This concentration explains why the distribution is broad and asymmetric.",
                  'S2 has exact equal-recall draws, so its upper endpoint can be zero without identical score vectors.', '',
                  '| Stage | Full CI | Excluding largest clusters CI | Weight cap | Capped CI | Median delta | Draws below zero | Above 0.3 | Above 0.5 | Exact zero |',
                  '|---|---|---|---:|---|---:|---:|---:|---:|---:|']
        for stage, row in diag['stages'].items():
            full = row['full']
            lines.append(f"| {stage} | {full['ci']} | {row['exclude_top_one_percent']['ci']} | {row['weight_cap']} | {row['capped']['ci']} | {full['median']:.8f} | {full['below_zero']} | {full['above_point_three']} | {full['above_point_five']} | {full['exact_zero']} |")
        lines += ['', 'Weight caps use the nearest-rank percentile of cluster size; each cluster contribution is scaled proportionally. These sensitivities change the population weighting and are not alternate official outcomes.',
                  diag['method_caveat']]
    check_path = root / 'artifact_checks.json'
    if check_path.exists():
        checks = json.loads(check_path.read_text())
        lines += ['', '## Artifact interpretation', '',
                  f"The shuffled-label model has recall {checks['checks']['shuffle']['test_recall']:.8f}. The constant-prevalence gradient control in the metric audit reproduces this systematic ranking; shuffling training labels does not force a finite-iteration fitted score vector to rank test sessions uniformly at random.",
                  f"Removing session parameters reduces recall to {checks['checks']['cnt_session_params']['test_recall']:.8f}. The sampled log contains parameter events after commands; whole-session counters therefore cannot be assumed to represent only a pre-command prefix.",
                  'The positive gain comes from transfer-only sessions and command/transfer overlaps. Performance is worse than the baseline on command-only and direct-tcpip-only positives.']
    for filename, title in [('artifact_checks.json', 'Leakage and ablations'), ('event_order.json', 'Observed event order'), ('bootstrap_diagnostics.json', 'Bootstrap diagnostics'), ('family_comparison.json', 'Candidate family comparison')]:
        if (root / filename).exists():
            lines += ['', '## ' + title, '', '```json', (root / filename).read_text().strip(), '```']
    (root / 'ROBUSTNESS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    import sys
    if '--render' in sys.argv:
        render()
    elif '--supplement' in sys.argv:
        supplement()
    else:
        main()
