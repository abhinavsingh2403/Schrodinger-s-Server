"""Select whole test-day traces by exact hashes of audited read-only commands."""
import hashlib
import json
import sys
from pathlib import Path
import duckdb

OUT = Path("results/replay")
def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()

SAFE = {digest(cmd):cmd for cmd in ("hostname","id","whoami","pwd","uname","uname -a","ls","ls /")}

def allowed(sequence):
    return 0 < len(sequence) <= 2 and all(h in SAFE for h in sequence)

def select(cache):
    days = json.loads(Path("results/exp0/event_prefix_study.json").read_text())["days"]
    day = max(days)
    path = cache/(day+".json.gz")
    with path.open("rb") as stream:
        if hashlib.file_digest(stream,"sha256").hexdigest() != days[day]["sha256"]:
            raise ValueError("cache mismatch")
    with duckdb.connect() as db:
        db.execute("""create table traces as select sha256(to_json([sensor,session])) key,
          min(ts::timestamp) filter(where eventid='cowrie.session.connect') c,
          max(ts::timestamp) filter(where eventid='cowrie.session.closed') z,
          list(ts::timestamp order by ts::timestamp) filter(where eventid='cowrie.command.input') times,
          list(sha256(input) order by ts::timestamp) filter(where eventid='cowrie.command.input') sequence
          from read_json(?,format='newline_delimited',columns={sensor:'varchar',session:'varchar',ts:'varchar',eventid:'varchar',input:'varchar'})
          where sensor is not null and session is not null group by sensor,session""",[str(path)])
        counts={}
        selected=[]
        for key,c,z,times,seq in db.execute("select * from traces where times is not null order by key").fetchall():
            if not c or not z or None in times or min(times)<c or max(times)>z:
                reason="incomplete"
            elif len(seq)>2:
                reason="length_cap"
            elif len(set(times))!=len(times):
                reason="tied_time"
            elif not allowed(seq):
                reason="outside_exact_allowlist"
            else:
                reason="eligible"
                if len(selected)<5:
                    selected.append(dict(key=key,commands=seq))
            counts[reason]=counts.get(reason,0)+1
    OUT.mkdir(exist_ok=True)
    (OUT/"selection.json").write_text(json.dumps(dict(day=day,counts=counts,traces=selected),indent=2)+"\n")
    print(counts,len(selected))
if __name__=="__main__":
    select(Path(sys.argv[1]))
