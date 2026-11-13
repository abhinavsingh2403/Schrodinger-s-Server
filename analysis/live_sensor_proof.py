"""Run existing loopback SSH scenarios and capture masked real decision evidence.

Requires the separately started gatekeeper and adaptive Cowrie launcher in WSL.
Uses installed OpenSSH and a temporary askpass for the lab-only dummy password.
"""
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile


def masked(text):
    return re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[masked-address]', text)


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='adaptive-proof-') as folder:
        ask = Path(folder) / 'askpass'
        ask.write_text('#!/bin/sh\nprintf "%s\\n" root\n')
        ask.chmod(0o700)
        env = {**os.environ, 'SSH_ASKPASS': str(ask), 'SSH_ASKPASS_REQUIRE': 'force', 'DISPLAY': ':lab'}
        runs = []
        for scenario in ('bot_like', 'interactive', 'transfer_like'):
            command = [str(root / '.venv/bin/python'), '-m', 'harness.attackers.' + scenario,
                       '--host', '127.0.0.1', '--port', '2222', '--username', 'admin']
            run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=90, cwd=root)
            runs.append({'scenario': scenario, 'returncode': run.returncode,
                         'output': masked(run.stdout + run.stderr)})
            if run.returncode:
                break
        command = ['ssh', '-p', '2222', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
                   'admin@127.0.0.1', 'cat /opt/deploy/config.env']
        run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
        conn = sqlite3.connect('/tmp/schrodinger-p1.db')
        rows = conn.execute('SELECT session_id,stage,tier_decided FROM decision_log ORDER BY id').fetchall()
        identifiers = {sid: 'session-' + str(i + 1) for i, sid in enumerate(dict.fromkeys(r[0] for r in rows))}
        out = {'scope': 'LAB: real pinned Cowrie, default gatekeeper, loopback only; outbound denied',
            'harness_runs': runs, 'harness_limitation': 'The harness ignores its password argument and does not check SSH return codes. Its two labelled failed-login attempts may authenticate under default Cowrie userdb. Trust the real event/decision log, not action labels.',
            't2_file_transcript': masked(run.stdout + run.stderr),
            'transcript_returncode': run.returncode,
            'decisions': [{'session': identifiers[sid], 'stage': stage, 'tier': tier} for sid,stage,tier in rows]}
        (root / 'results/exp0/live_sensor_proof.json').write_text(json.dumps(out, indent=2) + '\n')
        print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
