"""Read-only decision ticker with safe legacy-column fallbacks."""
import argparse,json,sqlite3,time
from pathlib import Path

def read_rows(db,after=0):
    with sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro',uri=True) as c:
        c.row_factory=sqlite3.Row
        rows=[dict(r) for r in c.execute('SELECT * FROM decision_log WHERE id>? ORDER BY id',(after,))]
    return [{'id':r['id'],'time':r.get('timestamp','UNKNOWN'),'visitor':'vis_'+str(r.get('visitor_id','unknown')).removeprefix('vis_')[:8],
             'session':r.get('session_id','UNKNOWN'),'stage':r.get('stage','UNKNOWN'),'tier':r.get('tier_decided','UNKNOWN'),
             'policy_profile':r.get('policy_profile','UNKNOWN'),'label':'LAB_DEMO_NOT_ML'} for r in rows]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--db',required=True);parser.add_argument('--once',action='store_true');args=parser.parse_args();after=0
    try:
        while True:
            try:
                for row in read_rows(args.db,after):
                    print(json.dumps(row),flush=True);after=row['id']
            except sqlite3.Error:
                if args.once: raise
            if args.once: break
            time.sleep(.2)
    except KeyboardInterrupt: pass
if __name__=='__main__':main()
