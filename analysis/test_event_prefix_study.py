"""Check timestamp prefix exclusion on controlled events before analysing real logs."""
import duckdb
import zlib
import struct
import pytest
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


def test_strict_order_availability_and_repeated_command_label():
    conn = duckdb.connect()
    conn.execute('CREATE TABLE events(sensor VARCHAR, session VARCHAR, ts TIMESTAMP, eventid VARCHAR, command_hash VARCHAR)')
    events = [(0, 'cowrie.session.connect', None), (1, 'cowrie.session.params', None),
              (2, 'cowrie.command.input', 'repeat'), (2, 'cowrie.client.size', None),
              (3, 'cowrie.client.var', None), *[(i, 'cowrie.command.input', 'repeat') for i in range(3, 7)],
              (7, 'cowrie.session.closed', None)]
    conn.executemany('INSERT INTO events VALUES (?, ?, ?, ?, ?)',
        [('lab', 'session', f'2025-01-01 00:00:0{i}', event, command) for i,event,command in events])
    result = summarize(conn)
    assert result['event_order']['cowrie.session.params']['before_first_command'] == 1
    assert result['event_order']['cowrie.client.size']['same_timestamp'] == 1
    assert result['event_order']['cowrie.client.var']['after_first_command'] == 1
    assert result['event_order']['cowrie.client.var']['sessions_with_both'] == 1
    assert result['s3_availability']['whole_vector_strictly_before'] == 0
    assert result['stages']['S3']['future_positive'] == 0
    assert summarize(conn, distinct=False)['stages']['S3']['future_positive'] == 1


def test_member_download_retries_truncation_and_reuses_compressed_prefix(tmp_path, monkeypatch):
    from analysis import event_prefix_study as study
    payload = b'lab gzip bytes' * 100
    compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    compressed = compressor.compress(payload) + compressor.flush()
    entry = {'name': 'lab.json.gz', 'crc32': zlib.crc32(payload), 'local_header_offset': 0,
             'compression_method': 8, 'compressed_size': len(compressed), 'uncompressed_size': len(payload)}
    header = bytearray(64)
    header[:4] = b'PK\x03\x04'
    header[26:30] = struct.pack('<HH', 0, 0)
    calls = []
    def truncated_once(url, start, end):
        if start == 0:
            return bytes(header)
        calls.append((start, end))
        return compressed[:-1] if len(calls) == 1 else compressed
    monkeypatch.setattr(study, 'bounded_range', truncated_once)
    path = study.download(entry, tmp_path)
    assert path.read_bytes() == payload
    assert len(calls) == 2
    # Rebuild the member from its validated compressed prefix without another data read.
    path.unlink()
    calls.clear()
    assert study.download(entry, tmp_path).read_bytes() == payload
    assert calls == []
