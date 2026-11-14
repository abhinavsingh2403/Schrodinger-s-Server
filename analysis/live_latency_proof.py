"""Measure the unchanged latency benchmark repeatedly, storing portable evidence."""
import json
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import sys

def main():
    rows = []
    for _ in range(5):
        result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-s',
            'gatekeeper/test_model_inference_parity.py::test_decision_latency_benchmark'], capture_output=True, text=True,
            env={**os.environ, 'SCHRODINGER_RUN_TIMING': '1'})
        matches = re.findall(r'Pipeline\] p50=([\d.]+)ms, p95=([\d.]+)ms, p99=([\d.]+)ms', result.stdout)
        if not matches:
            raise RuntimeError('Benchmark percentiles missing; no measurement inferred')
        rows.append(dict(zip(['p50_ms','p95_ms','p99_ms'], map(float, matches[0])), exit_code=result.returncode))
    out = {'platform': platform.system(), 'runs': rows,
        'median_p50_ms': statistics.median(r['p50_ms'] for r in rows),
        'max_p99_ms': max(r['p99_ms'] for r in rows),
        'scope': 'Maximum reported p99 across runs, not maximum individual request latency; localhost HTTP overhead excluded.'}
    Path('results/exp0', 'live_latency_' + platform.system().lower() + '.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out))

if __name__ == '__main__':
    main()
