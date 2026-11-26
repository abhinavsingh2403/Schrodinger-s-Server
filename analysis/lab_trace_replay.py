"""Replay canonical read-only queries in the dedicated loopback Docker lab."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from analysis.replay_selection import SAFE, OUT, allowed
from analysis.tier_cost_study import COMPOSE
from harness.attackers.common import execute_ssh_command

DB = """import sqlite3,json
rows=sqlite3.connect('/app/data/gatekeeper.db').execute('select session_id,tier_decided from decision_log order by rowid')
print(json.dumps(dict(rows)))"""
LOG = """import json,hashlib,sys
events=(json.loads(line) for line in open('/state/var/log/cowrie/cowrie.json') if line.strip())
print(json.dumps([hashlib.sha256(e.get('input','').encode()).hexdigest() for e in events if e.get('session')==sys.argv[1] and e.get('eventid')=='cowrie.command.input']))"""


def run(compose):
    selection=json.loads((OUT/'selection.json').read_text())
    traces=selection['traces']
    if len(traces)!=5 or not all(allowed(t['commands']) for t in traces):
        raise ValueError("selection outside frozen protocol")
    rows=[]
    for arm in ('T1','T2'):
        for repeat in range(1,4):
            subprocess.run(compose+['down','-v'],check=True)
            try:
                subprocess.run(compose+['up','-d','--build'],env=dict(os.environ,GATEKEEPER_PROFILE='LAB_DEMO'),check=True)
                endpoint=subprocess.check_output(compose+['port','edge','2222'],text=True).strip()
                if endpoint!='127.0.0.1:2222':
                    raise RuntimeError('loopback binding unavailable')
                for _ in range(60):
                    if subprocess.run(compose+['exec','-T','sensor','python','-c',"import socket;socket.create_connection(('127.0.0.1',2222),1).close()"],capture_output=True).returncode==0:
                        break
                    time.sleep(1)
                else:
                    raise RuntimeError('readiness timeout')
                def tiers():
                    return json.loads(subprocess.check_output(compose+['exec','-T','gatekeeper','python','-c',DB]))
                for trace in traces:
                    before=tiers()
                    seq=trace['commands']
                    result=execute_ssh_command('127.0.0.1',2222,'root','password',allocate_pty=arm=='T2',
                            input_lines=[SAFE[h] for h in seq]+['exit'],line_delay=.3)
                    after=tiers()
                    new=set(after)-set(before)
                    if len(new)!=1:
                        raise RuntimeError('ambiguous decision join')
                    sid=new.pop()
                    observed=json.loads(subprocess.check_output(compose+['exec','-T','sensor','python','-c',LOG,sid]))
                    rows.append(dict(arm=arm,repeat=repeat,trace=trace['key'],final=after[sid],
                                     complete=observed[:len(seq)]==seq,ssh_exit=result.returncode))
            finally:
                subprocess.run(compose+['down','-v'],check=True)
    (OUT/'observations.json').write_text(json.dumps(rows,indent=2)+'\n')
    lines=['# Docker replay result','Proposed receipt metric, pending human review. Counts cover the selected test day.',
           str(selection['counts']),'','| Arm | Repeat | Attempts | Correct final tier | Complete on correct tier |','|---|---:|---:|---:|---:|']
    for arm in ('T1','T2'):
        for repeat in range(1,4):
            group=[r for r in rows if r['arm']==arm and r['repeat']==repeat]
            correct=[r for r in group if r['final']==arm]
            lines.append(f"| {arm} | {repeat} | {len(group)} | {len(correct)} | {sum(r['complete'] for r in correct)} |")
    lines+=['','One archive, exact read-only allowlist, recorded inputs. Receipt alone cannot establish response fidelity or adaptive behavior.']
    (OUT/'REPLAY_RESULT.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    with tempfile.TemporaryDirectory() as folder:
        override=Path(folder)/'compose.yml'
        override.write_text('services:\n  sensor:\n    container_name: schrodinger-final-replay-sensor\n')
        run(COMPOSE+['-f',str(override)])
