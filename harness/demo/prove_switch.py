"""Capture real same-connection transition and command visibility evidence."""
import json, sqlite3, subprocess, tempfile
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
from analysis.live_sensor_proof import independent_lab
from harness.attackers.slow_recon import run_slow_recon

def main():
    root=Path(__file__).resolve().parents[2]
    original=subprocess.Popen
    def launch(command,**kwargs):
        if 'gatekeeper.decision_api' in command: command=[*command,'--lab-mode']
        return original(command,**kwargs)
    with tempfile.TemporaryDirectory(prefix='s2-proof-') as folder:
        with patch('subprocess.Popen',side_effect=launch),independent_lab(root,folder) as db:
            observation=run_slow_recon(port=12222,source_ip='127.0.0.4',delay=.2)
            with sqlite3.connect(db) as c:
                rows=c.execute('SELECT session_id,stage,tier_decided,score_source FROM decision_log ORDER BY id').fetchall()
        ids={sid:'session-'+str(i+1) for i,sid in enumerate(dict.fromkeys(r[0] for r in rows))}
        tiers=[r[2] for r in rows]
        visible=[r['file_visible'] for r in observation['commands']]
        result={'label':'LAB_DEMO_NOT_ML','command':'python -m harness.demo.prove_switch',
            'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'date':datetime.now(timezone.utc).isoformat(),
            'observation':observation,'decisions':[{'session':ids[s],'stage':g,'tier':t,'score_source':src} for s,g,t,src in rows],
            'passed':len(ids)==1 and 'T1' in tiers and 'T2' in tiers and not visible[0] and visible[-1] and not observation['returncode']}
        target=root/'results/demo/s2_mid_session_switch_proof.json';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
        if not result['passed']: raise SystemExit(1)
if __name__=='__main__':main()
