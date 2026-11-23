"""Audit tracked lab files and effective Compose publication without exposing values."""
import argparse
import ipaddress
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDRESS = re.compile(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])')
SECRET = re.compile(r'-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----|(?<![\w])[a-fA-F0-9]{32,}(?![\w])')
ALLOWED = [ipaddress.ip_network(net) for net in
           ('127.0.0.0/8', '192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24')]


def scan(name, content):
    findings = []
    for number, line in enumerate(content.splitlines(), 1):
        for match in ADDRESS.finditer(line):
            try:
                addr = ipaddress.IPv4Address(match.group())
            except ValueError:
                continue
            if any(addr in net for net in ALLOWED):
                continue
            bind = addr.is_unspecified and ('--host' in line or 'interface=' in line or 'start_server(' in line) and (name.startswith('infra/') or name == 'sensor/run_sensor.py')
            findings.append(('bind_warning' if bind else 'ipv4', number, match.start()+1))
        findings.extend(('secret_candidate', number, m.start()+1) for m in SECRET.finditer(line))
    return findings


def audit(root):
    def run(*args):
        return subprocess.check_output(args, cwd=root)
    paths = run('git','ls-files','-z').decode().rstrip('\0').split('\0')
    hits = {key: [] for key in ('ports','ipv4','secret_candidate','archives','ignore','bind_warning')}
    compose = json.loads(run('docker','compose','-f','infra/docker-compose.yml','config','--format','json'))
    for name, service in compose['services'].items():
        for port in service.get('ports', []):
            if port.get('host_ip') != '127.0.0.1':
                hits['ports'].append(name)
    for name in paths:
        if re.search(r'transfer.*\.(zip|tar|gz|7z|xz)$', name, re.I):
            hits['archives'].append(name)
        data = (root/name).read_bytes()
        if b'\0' in data:
            continue
        for kind, line, column in scan(name, data.decode('utf8', errors='replace')):
            hits[kind].append(f'{name}:{line}:{column}')
    for sample in ('state/etc/config','sensor/state/etc/config','local.sqlite','local.sqlite3','local.db','local.db-wal','local.db-shm'):
        if subprocess.run(['git','check-ignore','--no-index','-q',sample],cwd=root).returncode:
            hits['ignore'].append(sample)
    return {k: {'status': ('NOT_APPLICABLE' if k=='bind_warning' else 'FAIL' if v else 'PASS'), 'findings':v} for k,v in hits.items()}


if __name__ == '__main__':
    report = audit(ROOT)
    (ROOT/'results/safety_check.json').write_text(json.dumps(report,indent=2)+'\n')
    for key, item in report.items():
        print(key,item['status'],len(item['findings']))
    raise SystemExit(any(item['status']=='FAIL' for item in report.values()))
