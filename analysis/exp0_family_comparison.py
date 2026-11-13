"""Report validation-selected fallback LR candidates without adding model families."""
import json
from pathlib import Path
from analysis.exp0_train import load_parquet_as_dict_records, filter_prefix_determined_exclusions, STAGE_ALLOWED_FEATURES
from analysis.exp0_rules import PurePythonLogisticRegression, recall_at_budget


def main():
    root = Path('results/exp0')
    grid = json.loads((root / 'grid.json').read_text())
    data = {s: load_parquet_as_dict_records(root / f'{s}.parquet', sample_limit=50000 if s == 'train' else None)
            for s in ('train', 'val', 'test')}
    for s in ('val', 'test'):
        data[s] = filter_prefix_determined_exclusions(data[s], 'S3')[0]
    x = {s: [[float(r[f] or 0) for f in STAGE_ALLOWED_FEATURES['S3']] for r in records] for s, records in data.items()}
    y = {s: [r['v_full'] for r in records] for s, records in data.items()}
    candidates = []
    for c in grid['logistic_regression']['C']:
        model = PurePythonLogisticRegression(C=c, max_iter=60, lr=.5).fit(x['train'], y['train'])
        row = {'C': c, 'validation_recall': recall_at_budget(model.predict_proba(x['val']), y['val'], .1),
               'test_recall': recall_at_budget(model.predict_proba(x['test']), y['test'], .1)}
        candidates.append(row)
        print(row, flush=True)
    best = max(candidates, key=lambda r: r['validation_recall'])
    out = {'implementation': 'PurePythonLogisticRegression fallback, not sklearn LogisticRegression',
           'candidates': candidates, 'best_lr': best,
           'boundary': best['C'] == min(grid['logistic_regression']['C']),
           'hist_gradient_boosting': 'NOT RUN: absent in manifest-matching environment; no historical family winner recoverable for the current result',
           'grid_audit': 'The sklearn branch ignores max_leaf_nodes and min_samples_leaf grid dimensions. Not changed: pre-registered candidate changes require human review.'}
    (root / 'family_comparison.json').write_text(json.dumps(out, indent=2) + '\n')


if __name__ == '__main__':
    main()
