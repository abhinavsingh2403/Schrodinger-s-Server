"""Reporting-only shuffled-label, ablation and label-component checks for S3."""
import json
import random
import math
from pathlib import Path
from analysis.exp0_rules import PurePythonLogisticRegression, recall_at_budget
from analysis.exp0_train import load_parquet_as_dict_records, filter_prefix_determined_exclusions, get_rule_test_scores
from analysis.exp0_robustness import component_name


def main():
    root = Path('results/exp0')
    saved, metadata = PurePythonLogisticRegression.load_json(root / 'model_s3.json')
    train = load_parquet_as_dict_records(root / 'train.parquet', sample_limit=50000)
    test = filter_prefix_determined_exclusions(load_parquet_as_dict_records(root / 'test.parquet'), 'S3')[0]
    y = [r['v_full'] for r in train]
    test_y = [r['v_full'] for r in test]
    groups = ['cnt_client_size', 'cnt_client_var', 'cnt_session_params']
    out = {'seed': 20261111, 'model': metadata['model_type'], 'checks': {},
           'event_order': 'See event_order.json for the separately executed bounded single-day range check; aggregate prefix validity remains unverified.',
           'scope': 'Same saved-model hyperparameters and official training-sample loader. Reporting only; no model selection on test.'}
    for name, dropped in [('refit', []), ('shuffle', []), *[(g, [g]) for g in groups], ('all_three', groups)]:
        feats = [f for f in metadata['features'] if f not in dropped]
        x = [[float(r[f] or 0) for f in feats] for r in train]
        xt = [[float(r[f] or 0) for f in feats] for r in test]
        fit_y = y.copy()
        if name == 'shuffle':
            random.Random(out['seed']).shuffle(fit_y)
        model = PurePythonLogisticRegression(C=saved.C, max_iter=saved.max_iter, lr=saved.lr).fit(x, fit_y)
        recall = recall_at_budget(model.predict_proba(xt), test_y, .1)
        out['checks'][name] = {'dropped': dropped, 'test_recall': recall}
        print(name, recall, flush=True)
    out['shuffle_interpretation'] = 'A shuffled-label recall far from the budget is a diagnostic signal, not proof of leakage; inspect finite-sample ties and distribution shift.'
    ml_scores = saved.predict_proba([[float(r[f] or 0) for f in metadata['features']] for r in test])
    rule_scores = get_rule_test_scores('R6_failed_logins', test, train, 'S3')
    rng = random.Random(42)
    ties = [rng.random() for _ in test]
    def selected(scores):
        return set(sorted(range(len(test)), key=lambda i: (scores[i], ties[i]), reverse=True)[:math.ceil(.1 * len(test))])
    ml_selected, rule_selected = selected(ml_scores), selected(rule_scores)
    out['component_gain'] = {}
    for name in sorted({component_name(r) for r in test if r['v_full']}):
        indices = {i for i, r in enumerate(test) if component_name(r) == name}
        ml_count, rule_count = len(indices & ml_selected), len(indices & rule_selected)
        out['component_gain'][name] = {'positives': len(indices), 'share_of_positives': len(indices) / sum(test_y),
            'ml_captured': ml_count, 'rule_captured': rule_count, 'ml_recall': ml_count / len(indices),
            'delta_contribution_to_overall_recall': (ml_count - rule_count) / sum(test_y)}
    (root / 'artifact_checks.json').write_text(json.dumps(out, indent=2) + '\n')
    with (root / 'ROBUSTNESS.md').open('a', encoding='utf-8') as f:
        f.write('\n## Leakage and artifact checks\n\n```json\n' + json.dumps(out, indent=2) + '\n```\n')


if __name__ == '__main__':
    main()
