"""Prove real same-transport T1-to-T2 switching and unavailable-service fallback.

LAB policy raises S2/S3 thresholds to keep the first channel at T1, then uses
the existing command-chain placeholder score to trigger T2 on the next channel.
This tests integration only, never ML efficacy. No third-party traffic is used.
"""
import http.server
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import threading
import time
from gatekeeper.decision_api import DecisionEngine, GatekeeperHTTPHandler
from analysis.live_sensor_proof import masked


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='same-session-proof-') as folder:
        base = Path(folder)
        engine = DecisionEngine(db_path=base / 'decisions.db')
        engine.policy.thresholds_v2.update(S2=1.1, S3=1.1)
        engine.policy.max_escalation_fraction = 1.0  # LAB integration isolation
        server = http.server.HTTPServer(('127.0.0.1', 5001), GatekeeperHTTPHandler)
        server.decision_engine = engine
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        ask = base / 'askpass'
        ask.write_text('#!/bin/sh\nprintf "%s\\n" root\n')
        ask.chmod(0o700)
        env = {**os.environ, 'SSH_ASKPASS': str(ask), 'SSH_ASKPASS_REQUIRE': 'force', 'DISPLAY': ':lab'}
        sensor_log = (base / 'sensor.log').open('w')
        proc = subprocess.Popen([str(root / '.venv/bin/python'), '-m', 'sensor.run_sensor',
            '--state-dir', str(base / 'cowrie'), '--port', '2223', '--gatekeeper-url', 'http://127.0.0.1:5001'],
            cwd=root, stdout=sensor_log, stderr=subprocess.STDOUT)
        common = ['ssh', '-p', '2223', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
                  '-o', 'LogLevel=ERROR', '-o', 'ConnectTimeout=5']
        def run(args):
            return subprocess.run(common + args, env=env, capture_output=True, text=True, timeout=15)
        try:
            for _ in range(100):
                try:
                    with socket.create_connection(('127.0.0.1', 2223), timeout=.1):
                        break
                except OSError:
                    if proc.poll() is not None:
                        raise RuntimeError((base / 'sensor.log').read_text())
                    time.sleep(.1)
            control = str(base / 'control')
            master = run(['-M', '-N', '-f', '-S', control, 'admin@127.0.0.1'])
            assert master.returncode == 0, master.stderr
            before = run(['-S', control, 'admin@127.0.0.1', 'cat /opt/deploy/config.env'])
            after = run(['-S', control, 'admin@127.0.0.1', 'echo lab; cat /opt/deploy/config.env'])
            run(['-S', control, '-O', 'exit', 'admin@127.0.0.1'])
            with sqlite3.connect(base / 'decisions.db') as conn:
                rows = conn.execute('SELECT session_id,stage,tier_decided FROM decision_log ORDER BY id').fetchall()
            ids = {r[0] for r in rows}
            server.shutdown()
            server.server_close()
            down = run(['admin@127.0.0.1', 'cat /opt/deploy/config.env'])
            out = {'scope': 'LAB controlled thresholds; same real SSH transport, sequential channels; not ML evidence',
                'policy_overrides': {'S2': 1.1, 'S3': 1.1, 'max_escalation_fraction': 1.0},
                'before': masked(before.stdout + before.stderr), 'after': masked(after.stdout + after.stderr),
                'gatekeeper_down': masked(down.stdout + down.stderr), 'unique_decision_sessions': len(ids),
                'decisions': [{'stage': stage, 'tier': tier} for _,stage,tier in rows],
                'passed': len(ids) == 1 and 'No such file' in before.stdout + before.stderr
                    and 'DB_USER=app_user' in after.stdout and 'No such file' in down.stdout + down.stderr}
            (root / 'results/exp0/live_switch_proof.json').write_text(json.dumps(out, indent=2) + '\n')
            print(json.dumps(out, indent=2))
            assert out['passed']
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            if worker.is_alive():
                server.shutdown()
                server.server_close()
            sensor_log.close()


if __name__ == '__main__':
    main()
