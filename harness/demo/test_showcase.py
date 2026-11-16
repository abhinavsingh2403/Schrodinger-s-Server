"""Exercise scene verdicts and legacy ticker reading without network traffic."""
import sqlite3
from harness.demo.showcase import check_scene
from harness.demo.ticker import read_rows

def test_checker_requires_same_connection():
    rows=[{'session':'a','stage':'S1','tier':'T1','policy_profile':'LAB_DEMO'}, {'session':'b','stage':'S5','tier':'T2','policy_profile':'LAB_DEMO'}]
    assert not check_scene('switch',rows)
    rows[1]['session']='a'
    assert check_scene('switch',rows)
    assert not check_scene('bot',rows)
    assert not check_scene('returning',rows,0)
    assert not check_scene('interactive',[])

def test_legacy_ticker(tmp_path):
    db=tmp_path/'old.db'
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE decision_log(id INTEGER,visitor_id TEXT,session_id TEXT,stage TEXT,tier_decided TEXT)')
        c.execute("INSERT INTO decision_log VALUES(1,'abcdef123456','session','S1','T1')")
    rows=read_rows(db)
    assert rows[0]['visitor']=='vis_abcdef12'
    assert rows[0]['policy_profile']=='UNKNOWN'
    assert read_rows(db,1)==[]
