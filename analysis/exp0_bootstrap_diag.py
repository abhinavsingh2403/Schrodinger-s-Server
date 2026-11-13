"""Inspect the official bootstrap distribution without changing its statistic.

A profiling return hook observes local deltas; raw source identifiers never leave memory.
Sensitivity caps use fractional cluster weights, preserving each cluster's composition.
"""
import inspect
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path
from analysis import exp0_train as train_module
from analysis.exp0_rules import PurePythonLogisticRegression


def run_distribution(ml, rule, labels, ids, cap=None):
    """Capture draws from the same function, optionally capping cluster weight for sensitivity."""
    fn = train_module.paired_cluster_bootstrap_delta
    if cap is not None:
        # Reporting-only copy: multiply each cluster's contribution by min(1, cap/size).
        source = inspect.getsource(fn).replace(
            'c_tot, c_pos, ml_sp, ml_pos_sp, ru_sp, ru_pos_sp = cluster_profiles[c_idx]',
            'c_tot, c_pos, ml_sp, ml_pos_sp, ru_sp, ru_pos_sp = cluster_profiles[c_idx]\n            count *= min(1.0, WEIGHT_CAP / c_tot)')
        namespace = {**vars(train_module), 'WEIGHT_CAP': cap}
        exec(compile(source, '<reporting-only-weight-cap>', 'exec'), namespace)
        fn = namespace[fn.__name__]
    captured = {}
    def observe(frame, event, arg):
        if event == 'return' and frame.f_code is fn.__code__:
            captured['deltas'] = frame.f_locals.get('deltas', [])
    previous = sys.getprofile()
    try:
        sys.setprofile(observe)
        result = fn(ml, rule, labels, ids, alpha=train_module.STAGE_BONFERRONI_ALPHA['S3'])
    finally:
        sys.setprofile(previous)
    ds = captured['deltas']
    return {'point_delta': result[0], 'ci': list(result[1:]), 'median': statistics.median(ds),
            'draws': len(ds), 'below_zero': sum(x < 0 for x in ds),
            'above_point_three': sum(x > .3 for x in ds), 'above_point_five': sum(x > .5 for x in ds),
            'exact_zero': sum(x == 0 for x in ds)}


def main():
    root = Path('results/exp0')
    train = train_module.load_parquet_as_dict_records(root / 'train.parquet', sample_limit=50000)
    raw_test = train_module.load_parquet_as_dict_records(root / 'test.parquet')
    model, meta = PurePythonLogisticRegression.load_json(root / 'model_s3.json')
    out = {'seed': 20261111, 'stages': {}, 'bug': 'Fixed process-dependent cluster ordering by sorting cluster IDs. Regression test failed before fix.',
           'method_caveat': 'Official bootstrap averages capture within tied score bins, while reported point recall uses fixed random tie-breaking. This audit retains that statistic; it is not an exact bootstrap of the fixed-tie point estimator.'}
    for stage, rule_name in [('S2', 'R7_decision_tree'), ('S3', 'R6_failed_logins')]:
        records = train_module.filter_prefix_determined_exclusions(raw_test, stage)[0]
        features = train_module.STAGE_ALLOWED_FEATURES[stage]
        stage_model = model
        if stage == 'S2':
            stage_model = PurePythonLogisticRegression(C=model.C, max_iter=model.max_iter, lr=model.lr).fit(
                [[float(r[f] or 0) for f in features] for r in train], [r['v_full'] for r in train])
        ml = stage_model.predict_proba([[float(r[f] or 0) for f in features] for r in records])
        rule = train_module.get_rule_test_scores(rule_name, records, train, stage)
        labels = [r['v_full'] for r in records]
        ids = [r['src_ip'] for r in records]
        sizes = Counter(ids)
        positives = Counter(cid for cid, y in zip(ids, labels) if y)
        largest = sorted(sizes, key=lambda cid: (-sizes[cid], cid))
        top_count = math.ceil(.01 * len(sizes))
        row = {'clusters': len(sizes), 'concentration': {}}
        for name, count in [('top_1', 1), ('top_10', 10), ('top_one_percent', top_count)]:
            chosen = largest[:count]
            sessions = sum(sizes[c] for c in chosen)
            pos = sum(positives[c] for c in chosen)
            row['concentration'][name] = {'clusters': len(chosen), 'sessions': sessions, 'positives': pos,
                'session_share': sessions / len(ids), 'positive_share': pos / sum(labels)}
        print(stage, 'full bootstrap', flush=True)
        row['full'] = run_distribution(ml, rule, labels, ids)
        removed = set(largest[:top_count])
        keep = [i for i, cid in enumerate(ids) if cid not in removed]
        row['exclude_top_one_percent'] = run_distribution(*[[v[i] for i in keep] for v in (ml, rule, labels, ids)])
        cap = sorted(sizes.values())[math.ceil(.99 * len(sizes)) - 1]
        row['weight_cap'] = cap
        row['capped'] = run_distribution(ml, rule, labels, ids, cap=cap)
        row['capped']['point_delta_note'] = 'Point delta is the original unweighted point; CI and median use capped cluster weights.'
        out['stages'][stage] = row
        (root / 'bootstrap_diagnostics.json').write_text(json.dumps(out, indent=2) + '\n')
        print(stage, json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
