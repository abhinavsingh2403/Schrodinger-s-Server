"""Verify whole-trace rejection and exact canonical digest matching."""
import hashlib
import pytest
from analysis.replay_selection import allowed,digest


@pytest.mark.parametrize("token","wget curl tftp ftp scp nc ncat bash /dev/tcp ssh python perl http:// base64 | ;".split())
def test_unapproved_token_rejects_whole_trace(token):
    assert not allowed([digest("id"),digest("id "+token)])


def test_exact_digest_and_cap():
    key=hashlib.sha256(b"pwd").hexdigest()
    assert allowed([key,key])
    assert not allowed([key]*3)
    assert not allowed([None])
    assert not allowed([])
