"""Check timestamp prefix exclusion on controlled events before analysing real logs."""
import duckdb
from analysis.event_prefix_study import summarize


def test_prefix_excludes_already_positive_and_censored_sessions():
    conn = duckdb.connect()
    conn.execute('CREATE TABLE events(sensor VARCHAR, session VARCHAR, ts TIMESTAMP, eventid VARCHAR, command_hash VARCHAR)')
    events = [('cowrie.session.connect', None), ('cowrie.session.params', None),
              ('cowrie.session.file_download', None), ('cowrie.command.input', 'a'),
              ('cowrie.command.input', 'b'), ('cowrie.command.input', 'c'), ('cowrie.session.closed', None)]
    conn.executemany('INSERT INTO events VALUES (?, ?, ?, ?, ?)',
                     [('fixture', 'complete', f'2025-01-01 00:00:0{i}', ev, cmd) for i, (ev, cmd) in enumerate(events)])
    conn.execute("INSERT INTO events VALUES ('fixture','censored','2025-01-01','cowrie.command.input','x')")
    result = summarize(conn)
    assert result['complete_sessions'] == 1
    assert result['stages']['S3']['eligible'] == 1
    assert result['stages']['S4']['prefix_positive_excluded'] == 1
    assert result['stages']['S5']['prefix_positive_excluded'] == 1
