"""Capture actual test output and source fingerprints for task evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    args = parser.parse_args()
    command = [sys.executable, '-m', 'pytest', '-q']
    run = subprocess.run(command, capture_output=True, text=True)
    output = run.stdout + run.stderr
    output = output.replace(str(Path.cwd()), '<repo>').replace(str(Path.home()), '<home>')
    result = {'command': ['python', '-m', 'pytest', '-q'], 'interpreter': 'python', 'exit_code': run.returncode, 'output': output,
        'python': platform.python_version(), 'platform': platform.system(),
        'source_sha256': {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('analysis', 'gatekeeper', 'sensor') for p in Path(folder).glob('*.py')}}
    Path('results/exp0', args.name + '_tests.json').write_text(json.dumps(result, indent=2) + '\n')
    print(output)
    sys.exit(run.returncode)


if __name__ == '__main__':
    main()
