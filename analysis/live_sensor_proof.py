"""Run existing loopback SSH scenarios and capture masked real decision evidence.

Starts isolated gatekeeper and adaptive Cowrie processes in WSL per scenario.
Uses installed OpenSSH and a temporary askpass for the lab-only dummy password.
"""
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import sys
import time
from contextlib import contextmanager


@contextmanager
def independent_lab(root, folder):
    """Own isolated loopback processes; readiness does not create SSH sessions."""
    processes = []
    db = Path(folder) / 'memory.db'
    with (Path(folder) / 'process.log').open('w') as log:
        try:
            for command, port in (
                ([sys.executable, '-m', 'gatekeeper.decision_api', '--host', '127.0.0.1',
                  '--port', '15000', '--db', str(db)], 15000),
                ([sys.executable, '-m', 'sensor.run_sensor', '--state-dir', str(Path(folder) / 'sensor'),
                  '--gatekeeper-url', 'http://127.0.0.1:15000', '--port', '12222'], 12222),
            ):
                if listening(port):
                    raise RuntimeError('Lab proof port already occupied')
                process = subprocess.Popen(command, cwd=root, stdout=log, stderr=log)
                processes.append(process)
                deadline = time.monotonic() + 30
                while not listening(port):
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('Lab process failed to start; inspect temporary process log')
                    time.sleep(.1)
            yield db
        finally:
            for process in reversed(processes):
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def listening(port):
    """Read Linux listener state without consuming a honeypot session."""
    return any(row.split()[1].endswith(f':{port:04X}') and row.split()[3] == '0A'
               for row in Path('/proc/net/tcp').read_text().splitlines()[1:])


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
        decisions = []
        for scenario in ('bot_like', 'interactive', 'transfer_like'):
            command = [str(root / '.venv/bin/python'), '-m', 'harness.attackers.' + scenario,
                       '--host', '127.0.0.1', '--port', '12222', '--username', 'admin']
            with tempfile.TemporaryDirectory(prefix='scenario-') as state, independent_lab(root, state) as db:
                run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=90, cwd=root)
                with sqlite3.connect(db) as conn:
                    rows = conn.execute('SELECT session_id,stage,tier_decided,score FROM decision_log ORDER BY id').fetchall()
                identifiers = {sid: 'session-' + str(i + 1) for i, sid in enumerate(dict.fromkeys(r[0] for r in rows))}
                decisions.extend({'scenario': scenario, 'session': identifiers[sid], 'stage': stage,
                                  'tier': tier, 'score': score} for sid, stage, tier, score in rows)
            runs.append({'scenario': scenario, 'returncode': run.returncode,
                         'output': masked(run.stdout + run.stderr)})
            if run.returncode:
                break
        out = {'scope': 'LAB: real pinned Cowrie, default gatekeeper, loopback only; outbound denied',
            'harness_runs': runs, 'harness_limitation': 'The harness ignores its password argument and does not check SSH return codes. Its two labelled failed-login attempts may authenticate under default Cowrie userdb. Trust the real event/decision log, not action labels.',
            'memory_scope': 'Fresh database and budget ledger per scenario; shared within each scenario',
            'decisions': decisions}
        from gatekeeper.decision_api import DecisionEngine
        engine = DecisionEngine(db_path=Path(folder) / 'replay.db')
        out['s2_replay'] = {
            'scope': 'Current default successful-auth replay; historical exact inputs and budget are unavailable',
            'features': {'s2_has_success': 1, 's2_failed_logins': 0},
            'memory_before': {'highest_tier_served': engine.memory.get_visitor('127.0.0.1')['highest_tier_served']},
            'decision': engine.decide('replay', source_ip='127.0.0.1', stage='S2',
                                      features={'s2_has_success': 1, 's2_failed_logins': 0})}
        (root / 'results/exp0/live_sensor_proof.json').write_text(json.dumps(out, indent=2) + '\n')
        print('Recorded', len(decisions), 'decisions across', len(runs), 'scenarios')


if __name__ == '__main__':
    main()
