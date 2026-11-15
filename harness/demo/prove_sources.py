"""Prove distinct loopback SSH sources yield distinct masked visitors."""
import json, sqlite3, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path
from analysis.live_sensor_proof import independent_lab
from harness.attackers.bot_like import run_bot_like

def main():
    root=Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='s1-proof-') as folder:
        with independent_lab(root,folder) as db:
            runs=[run_bot_like(port=12222,source_ip=ip)['returncode'] for ip in ('127.0.0.2','127.0.0.3')]
            with sqlite3.connect(db) as c:
                visitors=['vis_'+r[0][:8] for r in c.execute('SELECT DISTINCT visitor_id FROM decision_log')]
        result={'label':'LAB_DEMO_NOT_ML','command':'python -m harness.demo.prove_sources',
                'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                'date':datetime.now(timezone.utc).isoformat(),'attacker_returncodes':runs,
                'masked_visitor_ids':visitors,'visitor_id_count':len(visitors),'passed':len(visitors)==2 and not any(runs)}
        target=root/'results/demo/s1_multi_visitor_proof.json';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
        if not result['passed']: raise SystemExit(1)
if __name__=='__main__': main()
