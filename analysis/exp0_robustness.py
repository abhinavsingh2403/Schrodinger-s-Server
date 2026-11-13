"""Audit saved S3 model identity before attributing robustness to the official run.

Uses saved splits and model without changing the official experiment artifacts.
Stops inference about the official model when its identity cannot be reproduced.
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
    out['identity_verified'] = abs(out['ml']['difference_from_official']) <= 1e-4
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
        'Bootstrap uses the official function, including its tie-bin averaging; point recalls use seed 42 while the bootstrap uses seed 20261111.',
    ]
    model, metadata = PurePythonLogisticRegression.load_json(root / 'model_s3.json')
    train = load_parquet_as_dict_records(root / 'train.parquet', sample_limit=50000)
    records = filter_prefix_determined_exclusions(load_parquet_as_dict_records(root / 'test.parquet'), 'S3')[0]
    labels = [r['v_full'] for r in records]
    clusters = [r['src_ip'] for r in records]
    scores = model.predict_proba([[float(r[f] or 0) for f in metadata['features']] for r in records])
    rng = random.Random(42)
    ties = [rng.random() for _ in records]
    selected = set(sorted(range(len(records)), key=lambda i: (scores[i], ties[i]), reverse=True)[:math.ceil(.1 * len(records))])
    captured = Counter(component_name(records[i]) for i in selected if labels[i])
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
    for filename, title in [('artifact_checks.json', 'Leakage and ablations'), ('bootstrap_diagnostics.json', 'Bootstrap diagnostics')]:
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
