"""Check observed event ordering in a bounded range sample of one archive day.

Raw events remain in memory; only aggregate counts are written to the audit report.
"""
from collections import defaultdict
import json
from pathlib import Path
import urllib.request
from analysis import s3_event_sample


def bounded_range(url, start, end):
    """Require HTTP partial content and refuse oversized responses."""
    request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 206:
            raise ValueError('Server did not honor byte range; refusing full archive')
        body = response.read(end - start + 2)
        if len(body) > end - start + 1:
            raise ValueError('Range response exceeds requested byte count')
        return body


def inspect_order(events):
    """Count feature events before/after first command only within sampled sessions."""
    sessions = defaultdict(list)
    for event in events:
        if event.get('session') is not None:
            sessions[(event.get('sensor'), event['session'])].append(event.get('eventid'))
    out = {}
    for name in ('cowrie.client.size', 'cowrie.client.var', 'cowrie.session.params'):
        row = {'before_first_command': 0, 'after_first_command': 0, 'sessions_with_command_and_feature': 0}
        for sequence in sessions.values():
            if 'cowrie.command.input' not in sequence or name not in sequence:
                continue
            first = sequence.index('cowrie.command.input')
            row['sessions_with_command_and_feature'] += 1
            row['before_first_command'] += sum(ev == name for ev in sequence[:first])
            row['after_first_command'] += sum(ev == name for ev in sequence[first + 1:])
        out[name] = row
    return out


def main():
    s3_event_sample.fetch_range = bounded_range
    entry = s3_event_sample.list_zip_entries()[0]
    events = s3_event_sample.sample_first_day_events(entry)
    out = {'sampled_day': entry['name'], 'sample_events': len(events), 'order': inspect_order(events),
           'limitation': 'Partial one-day stream; ordering is stored log order, not independently timestamp-validated chronology. It is not a guarantee that whole-session counters are prefix-only. TODO(verify): complete per-session prefix comparison.'}
    Path('results/exp0/event_order.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
