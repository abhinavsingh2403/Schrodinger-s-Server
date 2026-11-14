"""Record actual loopback SSH identity output from a fresh launcher."""
import argparse
import json
import tempfile
from pathlib import Path
from analysis.live_sensor_proof import independent_lab
from harness.attackers.common import execute_ssh_command


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='identity-proof-') as folder:
        with independent_lab(root, folder):
            command = 'hostname; cat /etc/os-release; uname -a'
            run = execute_ssh_command('127.0.0.1', 12222, 'root', 'password', command=command)
        out = {'provenance': 'LAB actual SSH stdout', 'command': command,
               'returncode': run.returncode, 'stdout': run.stdout}
        args.output.write_text(json.dumps(out, indent=2)+'\n')
        print(run.stdout)


if __name__ == '__main__':
    main()
