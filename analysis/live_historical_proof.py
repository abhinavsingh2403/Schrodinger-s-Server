"""Inspect preserved lab decision evidence read-only without exporting identities."""
import argparse
import json
import sqlite3
import subprocess
from pathlib import Path


def inspect(path):
    """Keep historical observations distinct from missing decision-time state."""
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as conn:
        tables = [r[0] for r in conn.execute('SELECT name FROM sqlite_master')]
        rows = conn.execute('SELECT id,session_id,visitor_id,stage,score,tier_decided,timestamp FROM decision_log ORDER BY id').fetchall()
        first = next(r for r in rows if r[3] == 'S2')
        same = [r for r in rows if r[1] == first[1] and r[0] <= first[0]]
        earlier = [r for r in rows if r[2] == first[2] and r[0] < first[0]]
        return {
            'scope': 'LAB historical SQLite read-only inspection; identifiers omitted',
            'decision_count': len(rows),
            'first_session_through_s2': [dict(zip(('id','stage','score','tier','timestamp'), (r[0],*r[3:]))) for r in same],
            'earlier_same_visitor_decisions': len(earlier),
            'schema': {t: [r[1] for r in conn.execute('PRAGMA table_info(' + t + ')')]
                       for t in ('decision_log','visitors','session_budget','budget_metadata') if t in tables},
            'limitations': 'Decision log does not record input features, prior visitor snapshot, or budget snapshot. Current visitor rows are mutable and cannot establish prior state.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.db)
    revision = '3390400^'
    source = subprocess.check_output(['git', 'show', revision + ':gatekeeper/policy.py'], text=True)
    namespace = {'__file__': str(Path(__file__).resolve().parents[1] / 'gatekeeper/policy.py')}
    exec(compile(source, 'historical_policy', 'exec'), namespace)
    policy = namespace['EscalationPolicy']()
    replay = []
    tier = 'T1'
    for row in result['first_session_through_s2']:
        before = {'total_decisions': policy.total_decisions, 'escalated_decisions': policy.escalated_decisions}
        tier = policy.decide_tier(current_tier=tier, model_score=row['score'],
                                  visitor_profile={'highest_tier_served': 'T1'}, stage=row['stage'])
        replay.append({'stage': row['stage'], 'score': row['score'],
                       'threshold': policy.get_threshold_t2(row['stage']), 'tier': tier,
                       'budget_before': before})
    result['historical_policy_replay'] = {
        'revision': subprocess.check_output(['git','rev-parse',revision], text=True).strip(),
        'assumptions': 'Fresh policy counters, T1 memory, recorded scores; not a recovered process snapshot',
        'rows': replay,
        'interpretation': 'Historical policy treats budget rate as zero through its startup decision window. This permits score-based S2 escalation under the stated assumptions.'}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
