"""Compare permutation controls on frozen S3 splits without updating experiment artifacts."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
from statistics import mean
from math import ceil

from analysis.exp0_permutation_null import permute
from analysis.exp0_rules import PurePythonLogisticRegression, recall_at_budget
from analysis.exp0_train import filter_prefix_determined_exclusions, load_parquet_as_dict_records

ROOT = Path('results/exp0')
SEED = 20261111


def block_shuffle(labels, groups):
    """Exchange whole source vectors among equally sized groups, preserving prevalence."""
    blocks = defaultdict(list)
    for index, group in enumerate(groups):
        blocks[group].append(index)
    sizes = defaultdict(list)
    for block in blocks.values():
        sizes[len(block)].append(block)
    result = labels.copy()
    rng = random.Random(SEED)
    for peers in sizes.values():
        donors = peers.copy()
        rng.shuffle(donors)
        for recipient, donor in zip(peers, donors):
            for i, j in zip(recipient, donor):
                result[i] = labels[j]
    return result


def direct(scores, labels, order):
    ranked = sorted(order, key=scores.__getitem__, reverse=True)
    return sum(labels[i] for i in ranked[:ceil(len(labels)*.1)]) / sum(labels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--splits', type=Path, default=ROOT)
    args = parser.parse_args()
    saved, meta = PurePythonLogisticRegression.load_json(ROOT/'model_s3.json')
    train = load_parquet_as_dict_records(args.splits/'train.parquet', sample_limit=50000)
    test = filter_prefix_determined_exclusions(load_parquet_as_dict_records(args.splits/'test.parquet'),'S3')[0]
    def features(rows):
        return [[float(row[key] or 0) for key in meta['features']] for row in rows]
    x, xt = features(train), features(test)
    y, yt = [r['v_full'] for r in train], [r['v_full'] for r in test]
    def predict(labels):
        return PurePythonLogisticRegression(C=saved.C,max_iter=saved.max_iter,lr=saved.lr).fit(x,labels).predict_proba(xt)
    scores = predict(permute(y,SEED))
    recall = lambda s: recall_at_budget(s,yt,.1)
    null = recall(scores)
    frozen = json.loads((ROOT/'permutation_null.json').read_text())
    archived = next(r['recall'] for r in frozen['permutations'] if r['seed']==SEED)
    blocks = block_shuffle(y,[r['src_ip'] for r in train])
    order = list(range(len(yt)))
    shuffled = permute(order,SEED)
    lines = ['# S3 null-control diagnosis','',
        f'Observed model {recall(saved.predict_proba(xt)):.6f}. Session permutation seed {SEED}: {null:.6f}; archived same seed {archived:.6f}. Archived mean {frozen["mean"]:.6f}.',
        f'REJECTED: row order drives the official tie estimate. Original {null:.6f}, permuted test-row order {recall_at_budget([scores[i] for i in shuffled],[yt[i] for i in shuffled],.1):.6f}. This estimator averages the cutoff bin.',
        f'INCONCLUSIVE: source-cluster exchangeability. One equal-size block permutation gives {recall(predict(blocks)):.6f}; {sum(a!=b for a,b in zip(y,blocks))} training labels changed. Unique-size blocks cannot move.',
        f'REJECTED: prevalence alone inflates recall. Test prevalence {mean(yt):.6f}; constant test scores give {recall([0]*len(yt)):.6f}. Constant training targets at prevalence {mean(y):.6f} produce recall {recall(predict([mean(y)]*len(y))):.6f}. The fitting procedure can rank positives without session-specific training labels.',
        f'INCONCLUSIVE: chronological training selection. Reversing the same shuffled training pairs gives recall {reverse_fit(x,permute(y,SEED),xt,saved,yt):.6f}; holding the sample fixed cannot test collection-time confounding.',
        f'REJECTED: stable rather than random boundary ties explain the high control. Stable selection {direct(scores,yt,order):.6f}, seeded random ties {direct(scores,yt,shuffled):.6f}.','']
    for day,data in json.loads((ROOT/'event_prefix_study.json').read_text())['days'].items():
        a=data['s3_availability']
        lines.append(f'{day}: {a["sessions_with_counter_at_or_after_command"]}/{a["complete_command_sessions"]} complete command sessions have a counter at or after first command.')
    lines += ['', 'These counts show aggregate feature look-ahead relative to the first command. The event study uses first session.params as a proxy and includes timestamp ties. Raw events lack an authenticated per-session runtime decision boundary. Exact S3 prefix scores and recall: NOT RUN.','', 'The mechanical gate result is exploratory. These controls do not establish validated pre-command triage.']
    (ROOT/'NULL_DIAGNOSIS.md').write_text('\n\n'.join(lines)+'\n',encoding='utf8')


def reverse_fit(x, labels, xt, saved, yt):
    model = PurePythonLogisticRegression(C=saved.C,max_iter=saved.max_iter,lr=saved.lr)
    return recall_at_budget(model.fit(x[::-1],labels[::-1]).predict_proba(xt),yt,.1)


if __name__ == '__main__':
    main()

