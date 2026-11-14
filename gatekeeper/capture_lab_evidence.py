"""Capture isolated loopback lab observations before choosing demo policy rules."""
import json
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from analysis.live_sensor_proof import independent_lab
from gatekeeper.feature_extractor import SessionFeatureExtractor
from sensor.run_sensor import LifecycleBridge


class CaptureClient:
    """Observe adapter inputs without making replay decisions or changing memory."""
    def __init__(self):
        self.rows = []

    def decide(self, **kwargs):
        self.rows.append({'stage': kwargs['stage'], 'features': kwargs['features']})
        return {'tier': 'T1'}

    def record_session(self, **kwargs):
        return {}


def main():
    root = Path(__file__).resolve().parents[1]
    result = {'provenance': 'LAB: captured events and stored decisions; replay vectors explicitly labelled',
              'date': datetime.now(timezone.utc).isoformat(),
              'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              'command': 'python -m gatekeeper.capture_lab_evidence', 'scenarios': []}
    original = subprocess.Popen

    def lab_process(command, **kwargs):
        if 'gatekeeper.decision_api' in command:
            command = [*command, '--lab-mode']
        return original(command, **kwargs)

    for scenario in ('bot_like', 'interactive', 'transfer_like'):
        with tempfile.TemporaryDirectory(prefix='lab-capture-') as folder:
            with patch('subprocess.Popen', side_effect=lab_process), independent_lab(root, folder) as db:
                command = [sys.executable, '-m', 'harness.attackers.' + scenario,
                           '--host', '127.0.0.1', '--port', '12222']
                run = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=90)
            log = Path(folder) / 'sensor/var/log/cowrie/cowrie.json'
            events = [json.loads(line) for line in log.read_text().splitlines()]
            with sqlite3.connect(db) as conn:
                conn.row_factory = sqlite3.Row
                decisions = [dict(r) for r in conn.execute('SELECT * FROM decision_log ORDER BY id')]
            sessions = list(dict.fromkeys(r['session_id'] for r in decisions))
            output = {'scenario': scenario, 'returncode': run.returncode, 'sessions': []}
            for i, sid in enumerate(sessions):
                subset = [e for e in events if e.get('session') == sid]
                client = CaptureClient()
                bridge = LifecycleBridge(client)
                extractor = SessionFeatureExtractor()
                vectors = []
                commands = 0
                for event in subset:
                    extractor.ingest_event(event)
                    bridge.event(event)
                    name = event.get('eventid')
                    stage = None
                    if name in ('cowrie.login.success', 'cowrie.login.failed'):
                        stage = 'S2'
                    elif name == 'cowrie.session.params':
                        stage = 'S3'
                    elif name == 'cowrie.command.input':
                        commands += 1
                        stage = 'S4' if commands == 1 else 'S5'
                    if stage:
                        vectors.append({'stage': stage, 'features': extractor.extract_stage_features(stage)})
                output['sessions'].append({
                    'session': f'session-{i+1}', 'events': [e.get('eventid') for e in subset],
                    'command_count': commands, 'extractor_replay': vectors,
                    'adapter_replay': client.rows,
                    'decisions': [{k: r[k] for k in ('stage','score','tier_decided','provenance')}
                                  for r in decisions if r['session_id'] == sid],
                    'limitations': 'S1 NEWKEYS is a transport hook, not reconstructed from JSON. Score source is not stored in this decision schema.'})
            result['scenarios'].append(output)
    target = root / 'results/exp0/lab_policy_evidence.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    fixture = root / 'harness/demo/fixtures/lab_policy_capture.json'
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(json.dumps(result, indent=2) + '\n')
    for scenario in result['scenarios']:
        print(scenario['scenario'], 'returncode', scenario['returncode'],
              'sessions', len(scenario['sessions']))


if __name__ == '__main__':
    main()
