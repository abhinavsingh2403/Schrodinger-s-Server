"""Test a clean local clone in a disposable virtual environment."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def check(root, work, run=subprocess.run):
    clone = work/'repo'
    env = work/'venv'
    python = env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    steps = [('clone',['git','clone','--quiet','--no-local',str(root),str(clone)]),
             ('venv',[sys.executable,'-m','venv',str(env)]),
             ('install',[str(python),'-m','pip','install','-r','requirements.txt']),
             ('pytest',[str(python),'-m','pytest','-q'])]
    rows = []
    ok = True
    for name, command in steps:
        status = 'NOT RUN'
        if ok:
            ok = run(command,cwd=clone if name in ('pytest','install') else work).returncode == 0
            status = 'PASS' if ok else 'FAIL'
        rows.append((name,status))
    return rows


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as temp:
        rows = check(root,Path(temp))
    table = 'step status\n'+''.join(f'{name} {status}\n' for name,status in rows)
    print(table)
    (root/'results/repro_check.txt').write_text(table)
    sys.exit(any(status!='PASS' for _,status in rows))
