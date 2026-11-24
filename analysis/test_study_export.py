"""Verify that participant labels join only to matching persisted S3 sessions."""
import json
import sqlite3
import csv
import pytest
from analysis.study_export import export
from gatekeeper.features import stage_counters
from gatekeeper.visitor_memory import derive_visitor_id


def test_label_join(tmp_path,monkeypatch):
    monkeypatch.setenv("SENSOR_PREFIX_JOIN_KEY","fixture")
    key=derive_visitor_id("raw-session",b"fixture")
    events,db,labels,out=[tmp_path/p for p in ("events","db","labels","out")]
    with sqlite3.connect(db) as conn:
        conn.execute("create table decision_log(session_id,stage)")
        conn.execute("insert into decision_log values ('raw-session','S3')")
    counts=stage_counters("S3",{"cnt_session_params":1})
    rows=[dict(session=key,event="cowrie.session.params",seq=1),dict(session=key,stage="S3",last_seq=1,features=counts)]
    events.write_text("\n".join(map(json.dumps,rows)))
    header="participant_code,instruction,session_hint\n"
    labels.write_text(header)
    with pytest.raises(ValueError,match="Missing label"):
        export(events,db,labels,out)
    labels.write_text(header+f"P01,B,{key}\n")
    export(events,db,labels,out)
    row=next(csv.DictReader(out.read_text().splitlines()))
    assert (row["session"],row["label"],row["instruction"])==(key,"0","B")
    assert "raw-session" not in out.read_text()
