"""Four isolated-source LAB_DEMO_NOT_ML scenes checked using persisted evidence."""
import argparse,json,sqlite3,subprocess,tempfile,time
from pathlib import Path
from unittest.mock import patch
from analysis.live_sensor_proof import independent_lab
from harness.attackers.bot_like import run_bot_like
from harness.attackers.interactive import run_interactive
from harness.attackers.slow_recon import run_slow_recon
from harness.demo.ticker import read_rows

def check_scene(name,rows,prior_seen=0):
    if not rows or any(r['policy_profile']!='LAB_DEMO' for r in rows): return False
    if name=='bot': return all(r['tier']=='T1' for r in rows)
    if name=='interactive': return any(r['stage']=='S3' and r['tier']=='T2' for r in rows)
    if name=='switch':
        for sid in {r['session'] for r in rows}:
            tiers=[r['tier'] for r in rows if r['session']==sid]
            if 'T1' in tiers and 'T2' in tiers and tiers.index('T1')<tiers.index('T2'): return True
        return False
    if name=='returning': return prior_seen>0 and any(r['stage']=='S1' and r['tier']=='T2' for r in rows)
    return False

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fast',action='store_true');parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    if args.dry_run:
        print('LAB_DEMO_NOT_ML: start fresh loopback services; bot .2; PTY interactive .3; no-PTY slow recon .4; returning .3; DB checks; cleanup');return
    root=Path(__file__).resolve().parents[2];original=subprocess.Popen
    def launch(command,**kwargs):
        if 'gatekeeper.decision_api' in command: command=[*command,'--lab-mode']
        return original(command,**kwargs)
    results=[]
    try:
        with tempfile.TemporaryDirectory(prefix='showcase-') as folder:
            with patch('subprocess.Popen',side_effect=launch),independent_lab(root,folder) as db:
                print('LAB_DEMO_NOT_ML services ready; live ticker follows each scene',flush=True)
                print('Temporary decision DB:',db,flush=True)
                after=0;returning_id=None
                for name in ('bot','interactive','switch','returning'):
                    prior_seen=0
                    if name=='returning':
                        with sqlite3.connect(db) as c:
                            value=c.execute('SELECT n_sessions FROM visitors WHERE visitor_id=?',(returning_id,)).fetchone()
                            prior_seen=value[0] if value else 0
                    if name=='bot': run_bot_like(port=12222,source_ip='127.0.0.2')
                    elif name in ('interactive','returning'): run_interactive(port=12222,source_ip='127.0.0.3')
                    else: run_slow_recon(port=12222,source_ip='127.0.0.4',delay=.2 if args.fast else 2)
                    time.sleep(.1)
                    rows=read_rows(db,after)
                    for row in rows: print(json.dumps(row),flush=True)
                    if name=='interactive':
                        with sqlite3.connect(db) as c: returning_id=c.execute('SELECT visitor_id FROM decision_log ORDER BY id DESC LIMIT 1').fetchone()[0]
                    if rows: after=rows[-1]['id']
                    passed=check_scene(name,rows,prior_seen)
                    results.append({'scene':name,'passed':passed,'decisions':rows,'prior_seen_sessions':prior_seen})
                    print(name+': '+('PASS' if passed else 'FAIL'),flush=True)
    except KeyboardInterrupt:
        raise SystemExit(130)
    out=root/'results/demo/s3_showcase.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'label':'LAB_DEMO_NOT_ML','scenes':results},indent=2)+'\n')
    failed=[r['scene'] for r in results if not r['passed']]
    print('ALL SCENES PASS' if not failed else 'FAIL: '+', '.join(failed))
    if failed: raise SystemExit(1)
if __name__=='__main__':main()
