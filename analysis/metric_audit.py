"""Diagnose exact-budget selection and finite-iteration shuffled-model ranking."""
from collections import Counter
import json
import math
from pathlib import Path
import random
import statistics
from analysis.exp0_rules import PurePythonLogisticRegression, recall_at_budget
from analysis.exp0_train import load_parquet_as_dict_records, filter_prefix_determined_exclusions, get_rule_test_scores
from analysis.exp0_permutation_null import permute


def main():
    root = Path('results/exp0')
    model, meta = PurePythonLogisticRegression.load_json(root / 'model_s3.json')
    train = load_parquet_as_dict_records(root / 'train.parquet', sample_limit=50000)
    test = filter_prefix_determined_exclusions(load_parquet_as_dict_records(root / 'test.parquet'), 'S3')[0]
    x = [[float(r[f] or 0) for f in meta['features']] for r in train]
    xt = [[float(r[f] or 0) for f in meta['features']] for r in test]
    y, yt = [r['v_full'] for r in train], [r['v_full'] for r in test]
    shuffled = PurePythonLogisticRegression(C=model.C, max_iter=model.max_iter, lr=model.lr).fit(x, permute(y,20261111))
    # Conditional-expectation control: replacing every training label with the
    # training prevalence gives the expected gradient of a uniform label shuffle.
    control = PurePythonLogisticRegression(C=model.C, max_iter=model.max_iter, lr=model.lr).fit(x, [statistics.mean(y)] * len(y))
    vectors = {'official': model.predict_proba(xt), 'shuffled': shuffled.predict_proba(xt),
               'constant_prevalence_gradient_control': control.predict_proba(xt)}
    for name in ('R6_failed_logins','R7_decision_tree'):
        vectors[name] = get_rule_test_scores(name,test,train,'S3')
    out = {'estimators': {}, 'training_prevalence': statistics.mean(y),
           'shuffled_training_mean_prediction': statistics.mean(shuffled.predict_proba(x)),
           'shuffled_weights': shuffled.weights, 'control_weights': control.weights,
           'control_is_candidate': False}
    for name,scores in vectors.items():
        rng = random.Random(42)
        ties = [rng.random() for _ in scores]
        selected = sorted(range(len(scores)),key=lambda i:(scores[i],ties[i]),reverse=True)[:math.ceil(.1*len(scores))]
        counts = Counter(scores)
        out['estimators'][name] = {'sessions':len(scores),'positives':sum(yt),'unique_scores':len(counts),
            'largest_bin':max(counts.values()),'selected':len(selected),'recall':recall_at_budget(scores,yt,.1),
            'direct_selection_recall':sum(yt[i] for i in selected)/sum(yt)}
    import sys
    path = root / ('metric_audit_after.json' if '--after' in sys.argv else 'metric_audit_before.json')
    if path.exists():
        raise FileExistsError('Preserve the before-change evidence')
    path.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))


if __name__ == '__main__':
    main()
