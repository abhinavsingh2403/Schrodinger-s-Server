"""Exercise the parquet export with censored, tied and future-only fixture sessions."""
import gzip
import hashlib
import json
import re

import duckdb

from analysis.experiment1_dataset import build


def test_prefix_cohorts_and_privacy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    audit_dir=tmp_path/'results/exp0'
    audit_dir.mkdir(parents=True)
    day='2025-01-01'
    member=tmp_path/(day+'.json.gz')
    with gzip.open(member,'wt') as out:
        for sid,extra,tie in [('base',False,False),('extended',True,False),('tie',False,True),('missing',False,False)]:
            events=[(0,'session.connect'),(1,'login.success')]
            if sid!='missing':
                events.extend((i,'command.input') for i in range(2,7))
            if extra:
                events.append((7,'session.file_upload'))
            if tie:
                events.append((2,'client.var'))
            events.append((9,'session.closed'))
            for i,event in events:
                row=dict(sensor='fixture',session=sid,ts=f'{day} 00:00:0{i}',eventid='cowrie.'+event,
                         src_ip='fixture-source',username='fixture-name',input=str(i))
                out.write(json.dumps(row)+'\n')
    (audit_dir/'event_prefix_study.json').write_text(json.dumps({'days':{day:{
        'sha256':hashlib.sha256(member.read_bytes()).hexdigest()}}}))
    dest=tmp_path/'tables'
    build(tmp_path,dest)
    counts=json.loads((dest/'cohorts.json').read_text())[day]['S4']['counts']
    assert counts=={'eligible':2,'missing':1,'tied':1}
    with duckdb.connect() as db:
        rows=db.execute("select * exclude(key,label),label from read_parquet(?) order by label",
                        [str(dest/(day+'_S4.parquet'))]).fetchall()
    assert rows[0][:-1]==rows[1][:-1]
    assert [r[-1] for r in rows]==[False,True]
    assert re.fullmatch('[a-f0-9]{16}',rows[0][0])
    assert 'fixture' not in str(rows)
