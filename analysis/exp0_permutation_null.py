"""Reporting-only training-label permutation distribution using the unchanged model.

Session-wise permutations diagnose ranking sensitivity; clustered labels are not
exchangeable, so the exceedance fraction is descriptive, not a calibrated p-value.
"""
import json
import random
import statistics
from pathlib import Path
from analysis.exp0_rules import PurePythonLogisticRegression, recall_at_budget
from analysis.exp0_train import load_parquet_as_dict_records, filter_prefix_determined_exclusions


def permute(labels, seed):
    """Return a seeded permutation without modifying the original training labels."""
    result = list(labels)
    random.Random(seed).shuffle(result)
    return result


def main():
    root = Path('results/exp0')
    saved, meta = PurePythonLogisticRegression.load_json(root / 'model_s3.json')
    train = load_parquet_as_dict_records(root / 'train.parquet', sample_limit=50000)
    test = filter_prefix_determined_exclusions(load_parquet_as_dict_records(root / 'test.parquet'), 'S3')[0]
    x = [[float(r[f] or 0) for f in meta['features']] for r in train]
    xt = [[float(r[f] or 0) for f in meta['features']] for r in test]
    y, yt = [r['v_full'] for r in train], [r['v_full'] for r in test]
    observed = recall_at_budget(saved.predict_proba(xt), yt, .1)
    out = {'status': 'RUNNING', 'observed_recall': observed, 'seeds': list(range(20261111, 20261311)),
           'permutations': [], 'scope': 'Fixed saved-model hyperparameters; session-wise training-label shuffle only; no grid selection or official-outcome change.',
           'caveat': 'Descriptive diagnostic, not a calibrated clustered permutation significance test.'}
    path = root / 'permutation_null.json'
    for seed in out['seeds']:
        model = PurePythonLogisticRegression(C=saved.C, max_iter=saved.max_iter, lr=saved.lr).fit(x, permute(y, seed))
        scores = model.predict_proba(xt)
        row = {'seed': seed, 'recall': recall_at_budget(scores, yt, .1), 'score_bins': len(set(scores))}
        out['permutations'].append(row)
        path.write_text(json.dumps(out, indent=2) + '\n')
        print(len(out['permutations']), row, flush=True)
    values = sorted(r['recall'] for r in out['permutations'])
    out.update(status='COMPLETE', minimum=values[0], maximum=values[-1], mean=statistics.mean(values),
               median=statistics.median(values), at_or_above_observed=sum(v >= observed for v in values),
               exceedance_fraction=sum(v >= observed for v in values) / len(values))
    path.write_text(json.dumps(out, indent=2) + '\n')
    (root / 'PERMUTATION_NULL.md').write_text('# Training-label permutation diagnostic\n\n' +
        f"Observed recall: {observed:.8f}. Completed permutations: {len(values)}.\n\n" +
        f"Null mean: {out['mean']:.8f}; median: {out['median']:.8f}; range: [{values[0]:.8f}, {values[-1]:.8f}].\n\n" +
        f"At or above observed: {out['at_or_above_observed']} ({out['exceedance_fraction']:.2%}).\n\n" + out['caveat'] + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
