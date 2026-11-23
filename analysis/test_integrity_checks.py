"""Audit fixtures verify redacted findings and stop-on-failure reproduction."""
from types import SimpleNamespace
from analysis.safety_check import scan
from analysis.repro_check import check


def test_findings():
    assert scan('sample', '127.0.0.1 192.0.2.1') == []
    assert [x[0] for x in scan('sample','.'.join(['10','1','2','3'])+' '+'a'*40)] == ['ipv4','secret_candidate']


def test_failed_install(tmp_path):
    codes = iter([0,0,1])
    rows = check(tmp_path,tmp_path,lambda *a,**kw: SimpleNamespace(returncode=next(codes)))
    assert rows[-2:] == [('install','FAIL'),('pytest','NOT RUN')]
