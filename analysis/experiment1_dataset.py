"""Build masked stage snapshots from one local event member at a time."""
import argparse
import hashlib
import json
import secrets
from pathlib import Path

import duckdb
from gatekeeper.visitor_memory import derive_visitor_id

AUTH = "eventid in ('cowrie.login.failed','cowrie.login.success')"
CMD = "eventid='cowrie.command.input'"
TRANSFER = "eventid in ('cowrie.session.file_download','cowrie.session.file_upload','cowrie.direct-tcpip.request')"
FEATURES = "elapsed activity attempts failures successes usernames commands length tokens bucket gap".split()


def extract(db, stage):
    anchor = {"S2":f"min(ts) filter(where {AUTH})","S4":f"min(ts) filter(where {CMD})",
              "S5":f"(list(ts order by ts) filter(where {CMD}))[3]"}[stage]
    db.execute(f"""create or replace temp table snapshot as
      with anchors as (select sensor,session,{anchor} a, min(ts) filter(where eventid='cowrie.session.connect') c,
      max(ts) filter(where eventid='cowrie.session.closed') z,count(distinct src_ip) sources,min(src_ip) src
      from events group by all), grouped as (
      select sensor,session,a,c,z,sources,src,count(*) filter(where ts=a) ties,
      count(distinct digest) filter(where ts<=a)>=5 or count(*) filter(where ts<=a and {TRANSFER})>0 resolved,
      count(distinct digest) filter(where ts>a and ts<=z)>=5 or count(*) filter(where ts>a and ts<=z and {TRANSFER})>0 label,
      floor(epoch(a-c)) elapsed,count(*) filter(where ts<a) activity,
      count(*) filter(where ts<a and {AUTH}) attempts,count(*) filter(where ts<a and eventid='cowrie.login.failed') failures,
      count(*) filter(where ts<a and eventid='cowrie.login.success') successes,count(distinct username) filter(where ts<a and {AUTH}) usernames,
      count(*) filter(where ts<a and {CMD}) commands,sum(chars) filter(where ts<a) length,sum(words) filter(where ts<a) tokens,
      list(digest order by ts desc,digest) filter(where ts<a and {CMD}) digests,
      list(ts order by ts desc) filter(where ts<a and {CMD}) times
      from anchors join events using(sensor,session) group by all)
      select sha256(to_json([sensor,session])) key,src,label,case when a is null then 'missing'
      when c is null or z is null or a not between c and z then 'incomplete'
      when ties<>1 then 'tied' when sources<>1 then 'source' when resolved then 'resolved' else 'eligible' end reason,
      * exclude(sensor,session,a,c,z,sources,src,label,ties,resolved,digests,times),
      strpos('0123456789abcdef',left(digests[1],1))-1 bucket,floor(epoch(times[1]-times[2])) gap
      from grouped""")


def build(cache, out):
    out.mkdir(parents=True,exist_ok=True)
    audit=json.loads(Path('results/exp0/event_prefix_study.json').read_text())['days']
    salt=secrets.token_bytes(32)
    stats={}
    with duckdb.connect() as db:
        db.execute("set threads=2")
        db.execute("set memory_limit='2GB'")

        db.execute("create table previous(src varchar)")
        for day,record in sorted(audit.items()):
            path=cache/(day+'.json.gz')
            with path.open('rb') as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=record['sha256']:
                    raise ValueError('cache checksum mismatch')
            db.execute(r"""create or replace temp table events as select sensor,session,ts::timestamp ts,eventid,
              nullif(src_ip,'') src_ip,username,case when eventid='cowrie.command.input' then sha256(input) end digest,
              case when eventid='cowrie.command.input' then length(input) end chars,
              case when eventid='cowrie.command.input' then len(regexp_extract_all(input,'\S+')) end words
              from read_json(?,format='newline_delimited',columns={ts:'varchar',sensor:'varchar',session:'varchar',
              src_ip:'varchar',username:'varchar',input:'varchar',eventid:'varchar'}) where session is not null and sensor is not null""",[str(path)])
            db.execute("create or replace temp table masks(src varchar,source varchar)")
            sources=db.execute("select distinct src_ip from events where src_ip is not null").fetchall()
            import csv
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                mapping=Path(tmp)/"masked.csv"
                with mapping.open("w",newline="",encoding="utf8") as fh:
                    writer=csv.writer(fh)
                    writer.writerows((hashlib.sha256(src.encode()).hexdigest(),derive_visitor_id(src,salt)) for src, in sources)
                db.execute("copy masks from ? (format csv,header false)",[str(mapping)])
            stats[day]={}
            for stage in ('S2','S4','S5'):
                extract(db,stage)
                db.execute("update snapshot set reason='overlap' where reason='eligible' and src in (select src from previous)")
                reasons=dict(db.execute("select reason,count(*) from snapshot group by reason").fetchall())
                features=FEATURES[:6] if stage=='S2' else FEATURES
                cols=', '.join(f'least(255,coalesce({f},0))::utinyint as {f}' for f in features)
                file=out/f'{day}_{stage}.parquet'
                db.execute(f"""copy (select key,source,'{day}' as day,'{stage}' stage,{cols},label
                    from snapshot join masks on sha256(snapshot.src)=masks.src where reason='eligible' order by key) to ? (format parquet,compression zstd)""",[str(file)])
                positives,sources=db.execute("select count(*) filter(where label),count(distinct src) from snapshot where reason='eligible'").fetchone()
                stats[day][stage]=dict(reached=sum(reasons.values())-reasons.get('missing',0),counts=reasons,
                    positives=positives,sources=sources,prevalence=positives/reasons['eligible'] if reasons.get('eligible') else None)
            db.execute("insert into previous select distinct src_ip from events where src_ip is not null")
    (out/'cohorts.json').write_text(json.dumps(stats,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--cache',type=Path,default=Path('data/event_prefix_study'))
    build(parser.parse_args().cache,Path('results/exp1'))


