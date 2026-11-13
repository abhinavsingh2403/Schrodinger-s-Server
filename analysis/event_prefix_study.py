"""Three-day reporting-only timestamp-prefix feasibility study; never runs payloads.

Downloads only the selected archive members, validates ZIP CRC, and keeps raw logs
under ignored data/. Official experiment splits and metrics are not overwritten.
"""
import hashlib
import json
from pathlib import Path
import struct
import zlib
import duckdb
from analysis import s3_event_sample as archive
from analysis.exp0_event_order import bounded_range


def download(entry, folder):
    """Extract one ZIP member with bounded requests and validate its stored CRC."""
    path = folder / Path(entry['name']).name
    if path.exists() and zlib.crc32(path.read_bytes()) == entry['crc32']:
        return path
    offset = entry['local_header_offset']
    header = bounded_range(archive.ZENODO_DATA_ALL_URL, offset, offset + 63)
    if header[:4] != b'PK\x03\x04' or entry['compression_method'] != 8:
        raise ValueError('Unsupported or invalid ZIP member')
    name_len, extra_len = struct.unpack('<HH', header[26:30])
    start = offset + 30 + name_len + extra_len
    inflater = zlib.decompressobj(-zlib.MAX_WBITS)
    partial = path.with_suffix('.part')
    crc, size = 0, 0
    with partial.open('wb') as output:
        for relative in range(0, entry['compressed_size'], 16 * 1024 * 1024):
            length = min(16 * 1024 * 1024, entry['compressed_size'] - relative)
            chunk = bounded_range(archive.ZENODO_DATA_ALL_URL, start + relative, start + relative + length - 1)
            if len(chunk) != length:
                raise ValueError('Truncated range response')
            decoded = inflater.decompress(chunk)
            output.write(decoded)
            crc, size = zlib.crc32(decoded, crc), size + len(decoded)
            print(path.name, relative + length, '/', entry['compressed_size'], flush=True)
    if not inflater.eof or crc != entry['crc32'] or size != entry['uncompressed_size']:
        raise ValueError('ZIP member integrity mismatch')
    partial.replace(path)
    return path


def summarize(conn):
    """Compute stage eligibility using complete-session timestamps and future outcomes."""
    conn.execute('''CREATE OR REPLACE TEMP TABLE sessions AS
        SELECT sensor, session,
        min(ts) FILTER(WHERE eventid='cowrie.session.connect') AS connected,
        max(ts) FILTER(WHERE eventid='cowrie.session.closed') AS closed,
        min(ts) FILTER(WHERE eventid='cowrie.session.params') AS s3,
        min(ts) FILTER(WHERE eventid='cowrie.command.input') AS s4,
        list(ts ORDER BY ts) FILTER(WHERE eventid='cowrie.command.input') AS commands,
        count(DISTINCT command_hash) FILTER(WHERE eventid='cowrie.command.input') >= 5
          OR count(*) FILTER(WHERE eventid IN ('cowrie.session.file_download','cowrie.session.file_upload','cowrie.direct-tcpip.request')) > 0 AS value
        FROM events GROUP BY sensor, session''')
    count = conn.execute('SELECT count(*) FROM sessions WHERE connected IS NOT NULL AND closed IS NOT NULL AND closed>=connected').fetchone()[0]
    out = {'complete_sessions': count, 'stages': {}, 'event_order': {}}
    for stage, expression in [('S3', 's3'), ('S4', 's4'), ('S5', 'commands[3]')]:
        rows = conn.execute(f'''WITH anchors AS (
          SELECT *, {expression} AS anchor FROM sessions
          WHERE connected IS NOT NULL AND closed IS NOT NULL AND closed>=connected),
        prefixes AS (
          SELECT a.sensor,a.session,a.value,
          count(DISTINCT e.command_hash) FILTER(WHERE e.eventid='cowrie.command.input') >= 5
          OR count(*) FILTER(WHERE e.eventid IN ('cowrie.session.file_download','cowrie.session.file_upload','cowrie.direct-tcpip.request'))>0 AS prefix_positive
          FROM anchors a LEFT JOIN events e ON e.sensor=a.sensor AND e.session=a.session AND e.ts<=a.anchor
          WHERE a.anchor IS NOT NULL AND a.anchor>=a.connected AND a.anchor<=a.closed
          {'AND (a.s4 IS NULL OR a.anchor<a.s4)' if stage == 'S3' else ''}
          GROUP BY a.sensor,a.session,a.value)
        SELECT count(*),count(*) FILTER(WHERE prefix_positive),
          count(*) FILTER(WHERE NOT prefix_positive),count(*) FILTER(WHERE NOT prefix_positive AND value) FROM prefixes''').fetchone()
        out['stages'][stage] = dict(zip(['reached','prefix_positive_excluded','eligible','future_positive'], rows))
    for eventid in ('cowrie.client.size', 'cowrie.client.var', 'cowrie.session.params'):
        row = conn.execute('''SELECT count(*) FILTER(WHERE e.ts<s.s4),count(*) FILTER(WHERE e.ts=s.s4),count(*) FILTER(WHERE e.ts>s.s4)
          FROM events e JOIN sessions s USING(sensor,session)
          WHERE s.connected IS NOT NULL AND s.closed IS NOT NULL AND s.closed>=s.connected AND s.s4 IS NOT NULL AND e.eventid=?''', [eventid]).fetchone()
        out['event_order'][eventid] = dict(zip(['before_first_command','same_timestamp','after_first_command'], row))
    return out


def main():
    folder = Path('data/event_prefix_study')
    folder.mkdir(parents=True, exist_ok=True)
    splits = json.loads(Path('results/exp0/splits.json').read_text())['splits']
    days = [splits[s][0] for s in ('train','validation','test')]
    archive.fetch_range = bounded_range
    entries = archive.list_zip_entries()
    out = {'status': 'RUNNING', 'selection': 'First listed day of each unchanged official fold, fixed before event outcomes', 'days': {},
           'limitations': ['Reporting-only feasibility study; no model performance or new Gate 0 verdict.',
             'S3 anchor is first session.params before first command, a diagnostic proxy requiring runtime mapping review.',
             'Only sessions with connect and close in the same sampled day are included; boundary censoring remains.',
             'Same-timestamp ordering is ambiguous; prefixes conservatively include all events at the anchor timestamp.',
             'No cross-day train/test model is fitted; source-group leakage evaluation remains required before fitting.']}
    output = Path('results/exp0/event_prefix_study.json')
    for day in days:
        entry = next(e for e in entries if e['name'].endswith(day + '.json.gz'))
        path = download(entry, folder)
        conn = duckdb.connect()
        conn.execute("SET memory_limit='1GB'")
        conn.execute('''CREATE TABLE events AS SELECT sensor,session,TRY_CAST(ts AS TIMESTAMP) AS ts,eventid,
            CASE WHEN eventid='cowrie.command.input' THEN sha256(input) END AS command_hash
            FROM read_json(?,format='newline_delimited',compression='gzip',columns={ts:'VARCHAR',sensor:'VARCHAR',session:'VARCHAR',eventid:'VARCHAR',input:'VARCHAR'})''', [path.as_posix()])
        invalid = conn.execute('SELECT count(*) FROM events WHERE ts IS NULL OR sensor IS NULL OR session IS NULL').fetchone()[0]
        total = conn.execute('SELECT count(*) FROM events').fetchone()[0]
        conn.execute('DELETE FROM events WHERE ts IS NULL OR sensor IS NULL OR session IS NULL')
        out['days'][day] = {'events': total, 'invalid_key_or_timestamp': invalid, 'zip_crc32': entry['crc32'],
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), **summarize(conn)}
        conn.close()
        output.write_text(json.dumps(out, indent=2) + '\n')
        print(day, json.dumps(out['days'][day]), flush=True)
    out['status'] = 'COMPLETE'
    output.write_text(json.dumps(out, indent=2) + '\n')


if __name__ == '__main__':
    main()
