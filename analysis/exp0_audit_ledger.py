"""Generate the pre-registration ledger from Git, preserving historical table values."""
import csv
import io
from pathlib import Path
import subprocess


def git(*args):
    return subprocess.check_output(['git', *args], text=True, encoding='utf-8')


def main():
    lines = ['### 2026-11-13: Reproducible pre-registration audit ledger', '',
             'Decision: present S3 as exploratory-confirmatory, not a clean pre-registered confirmation.',
             'Reason: test results were visible before later feature, rule and bootstrap changes.',
             'Alternative rejected: treating later tags as proof of prospective registration.', '',
             'Annotated tag creation timestamps and target commits (from Git objects):', '']
    for tag in ('exp0-v1', 'eval-v1', 'exp0-v2', 'eval-v2'):
        info = git('for-each-ref', f'refs/tags/{tag}', '--format=%(refname:short) | %(taggerdate:iso-strict) | %(*objectname)').strip()
        lines.append('- ' + info)
    commits = git('log', '85134c6', '--reverse', '--format=%H', '--', 'analysis/exp0_train.py', 'analysis/exp0_rules.py', 'analysis/export_s3_model.py', 'results/exp0/table.csv', 'EXP0_RESULT.md', 'HANDOFF.md', 'README.md').splitlines()
    previous = None
    changes = {
        '2084d58': 'Exact chosen-rule scoring and bootstrap empty-draw guards added; duration removed, but the new S1 feature list still included post-authentication size/var counters.',
        '208f780': 'Stage allowlists and stage-specific rule inputs introduced; fixed random tie-breaking and custom logistic-regression fallback added; training changed to a seeded reservoir sample; aggregate S4/S5 disabled.',
        '72b9f12': 'Reports regenerated after the preceding code change; compare the stage rows below with the preceding committed table.',
        '22629af': 'Bootstrap changed to include zero-positive clusters and recalculate the budget per draw, using fractional capture within tied score bins.',
        'd099848': 'Separate S3 exporter and serving integration added; exported calibration/evaluation use unfiltered sessions, unlike the official stage-filtered evaluation.',
    }
    for commit in commits:
        summary = git('show', '-s', '--format=%h %aI %s', commit).strip()
        lines += ['', '**' + summary + '**', '']
        if commit[:7] in changes:
            lines.append(changes[commit[:7]])
        exists = git('ls-tree', '-r', '--name-only', commit, 'results/exp0/table.csv').strip()
        if not exists:
            lines.append('No committed table yet.')
            continue
        table = git('show', f'{commit}:results/exp0/table.csv')
        rows = list(csv.DictReader(io.StringIO(table)))
        if table == previous:
            lines.append('Committed stage rows unchanged; inspect source diff for implementation changes.')
        else:
            lines += ['Historical values copied by this script; not independently rerun:', '',
                      '| Stage | Rule | Rule test | ML | ML test | Delta | CI |', '|---|---|---:|---|---:|---:|---|']
            for r in rows:
                if r['stage'] in ('S1', 'S2', 'S3'):
                    lines.append(f"| {r['stage']} | {r['best_rule']} | {r['best_rule_test_recall']} | {r['ml_candidate']} | {r['ml_test_recall']} | {r['delta_k']} | [{r['ci_lower']}, {r['ci_upper']}] |")
        previous = table
    lines += ['', 'The first committed table already contains test-rule recalls; its commit precedes the second tag timestamps above.',
              'Later history changes stage allowlists, exact baseline scoring, deterministic ties, model fallback, and bootstrap cluster inclusion/budget cutoffs.',
              'The historical narrative claiming a different FAIL-stage point table does not match the committed table shown here; prefer Git evidence. The earlier summary before the first table has empty test-recall mappings, not measured recalls.',
              'Proposed tags for human review only: exp0-v3 and eval-v3. No tags created, moved, or deleted.', '']
    path = Path('DECISIONS.md')
    text = path.read_text(encoding='utf-8')
    marker = lines[0]
    if marker in text:
        text = text[:text.index(marker)].rstrip() + '\n'
    path.write_text(text + '\n' + '\n'.join(lines), encoding='utf-8')
    print('Generated chronological Git ledger in DECISIONS.md')


if __name__ == '__main__':
    main()
