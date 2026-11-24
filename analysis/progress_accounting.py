"""Compute the user-specified weighted checklist from explicit evidence judgements."""
import json
from analysis.render_status import render_status
from pathlib import Path

ITEMS = [
    ('S3 aggregate base rates', 2, 'Done', 'results/base_rates.json and analysis/s3_base_rates.py'),
    ('Event-schema check and group field', 2, 'Done', 'results/s3_event_schema.json; event order remains unverified'),
    ('Experiment 0 aggregate stages S1-S3 with leakage controls', 2, 'Partial', 'NULL_DIAGNOSIS.md reproduces the label-independent ranking; ML validation remains open'),
    ('Experiment 0 event-level S4/S5', 2, 'Not done', 'NOT_EVALUABLE on aggregate data'),
    ('T1/T2 personas and real Cowrie integration on Linux', 2, 'Done', 'Native same-session proof and Docker login, database and dashboard checks in HANDOFF.md'),
    ('Real hardware cost measurement (Spike S2)', 2, 'Not done', 'Mixed in-process personas in results/cost_model.json; no isolated tier comparison'),
    ('Gatekeeper trained model and offline/live parity', 1, 'Done', 'Offline/live score parity tested in gatekeeper/test_real_row_parity.py'),
    ('Escalation budget enforcement', 1, 'Done', 'Durable session accounting tested in gatekeeper/test_session_budget.py'),
    ('Persona-effect natural experiment', 1, 'Not done', 'Pending event-level group data'),
    ('Third-party detector evaluation (EVAL H4)', 1, 'Not done', 'Internal checks are not an independent detector evaluation'),
    ('Replay of real held-out traces', 1, 'Not done', 'SYNTHETIC command templates reconstructed from counters'),
    ('Dashboard using only script-generated numbers', 1, 'Done', 'Decision-backed live view, provenance and empty-state tests in dashboard/'),
    ('Public-sensor shadow run under SAFETY checklist', 1, 'Not done', 'No verified run'),
    ('Final report, slides and viva pack', 1, 'Partial', 'Working reports exist; final reviewed pack is absent'),
]


def main():
    credit = {'Done': 1, 'Partial': .5, 'Not done': 0}
    earned = sum(weight * credit[status] for _, weight, status, _ in ITEMS)
    total = sum(weight for _, weight, _, _ in ITEMS)
    percentage = 100 * earned / total
    Path('results/progress.json').write_text(json.dumps({'items': ITEMS, 'earned': earned, 'total': total, 'percentage': percentage}, indent=2) + '\n')
    render_status()
    print(f'Weighted completion: {percentage:.1f}% ({earned:g}/{total:g})')


if __name__ == '__main__':
    main()
