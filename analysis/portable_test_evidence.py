"""Migrate historical test command metadata without inventing new test runs."""
import json
from pathlib import Path


def main():
    for path in Path('results/exp0').glob('*_tests.json'):
        data = json.loads(path.read_text())
        command = data.get('command')
        if isinstance(command, list):
            data['command'] = ['python', *command[1:]]
        elif isinstance(command, str):
            data['command'] = 'python -m pytest' + command.split('-m pytest', 1)[1]
        data['interpreter'] = 'wsl-venv python' if 'wsl' in path.name else 'python'
        data['metadata_note'] = 'Historical test output retained; interpreter path normalized for portability. This migration is not a new test run.'
        path.write_text(json.dumps(data, indent=2) + '\n')


if __name__ == '__main__':
    main()
