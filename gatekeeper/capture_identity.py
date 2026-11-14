"""Record actual loopback SSH identity output from a fresh launcher."""
import argparse
import json
import tempfile
import subprocess
from unittest.mock import patch
from pathlib import Path
from analysis.live_sensor_proof import independent_lab
from harness.attackers.common import execute_ssh_command


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--t2', action='store_true')
    parser.add_argument('--default-file', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    original = subprocess.Popen
    def launch(command, **kwargs):
        if args.t2 and 'gatekeeper.decision_api' in command:
            command = [*command, '--lab-mode']
        return original(command, **kwargs)
    with tempfile.TemporaryDirectory(prefix='identity-proof-') as folder:
        with patch('subprocess.Popen', side_effect=launch), independent_lab(root, folder):
            command = 'cat /opt/deploy/config.env' if args.t2 or args.default_file else 'hostname; cat /etc/os-release; uname -a'
            run = execute_ssh_command('127.0.0.1', 12222, 'root', 'password', command=command, allocate_pty=args.t2 or args.default_file)
        out = {'provenance': 'LAB actual SSH stdout', 'command': command,
               'returncode': run.returncode, 'stdout': run.stdout}
        events = [json.loads(line) for line in (Path(folder)/'sensor/var/log/cowrie/cowrie.json').read_text().splitlines()]
        out['cowrie_command_inputs'] = [e['input'] for e in events if e.get('eventid')=='cowrie.command.input']
        args.output.write_text(json.dumps(out, indent=2)+'\n')
        print(run.stdout)


if __name__ == '__main__':
    main()
