"""Audit fixtures verify redacted findings and stop-on-failure reproduction."""
from types import SimpleNamespace
from analysis.safety_check import scan
from analysis.repro_check import check


def test_findings():
    assert scan('sample', '127.0.0.1 192.0.2.1') == []
    assert [x[0] for x in scan('sample','.'.join(['10','1','2','3'])+' '+'a'*40)] == ['ipv4','hash_like_info']
    assert scan('sub/test_fixture.py', '10.1.2.3') == []
    assert scan('sensor/adaptive_server.py', '10.0.0.4') == []
    assert scan('sensor/adaptive_server.py', '10.0.0.5')[0][0] == 'ipv4'
    assert scan('key', '-----BEGIN ' + 'PRIVATE KEY-----')[0][0] == 'secret_candidate'
    assert all(scan('sample', 'f'*n)[0][0] == 'hash_like_info' for n in (32,40,64))


def test_failed_install(tmp_path):
    codes = iter([0,0,1])
    rows = check(tmp_path,tmp_path,lambda *a,**kw: SimpleNamespace(returncode=next(codes)))
    assert rows[-2:] == [('install','FAIL'),('pytest','NOT RUN')]
