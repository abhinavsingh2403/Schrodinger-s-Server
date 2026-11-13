"""Ensure fixed bootstrap seeds survive Python's per-process string hash randomization."""
import os
import subprocess
import sys


def test_bootstrap_is_independent_of_python_hash_seed():
    code = '''from analysis.exp0_train import paired_cluster_bootstrap_delta
n=60
print(paired_cluster_bootstrap_delta([i%7 for i in range(n)], [i%3 for i in range(n)], [int(i%4==0) for i in range(n)], [str(i%13) for i in range(n)], n_resamples=100))'''
    results = [subprocess.check_output([sys.executable, '-c', code], env={**os.environ, 'PYTHONHASHSEED': seed}, text=True)
               for seed in ('1', '2')]
    assert results[0] == results[1]
