"""Loopback-only source binding is validated before SSH execution."""
import argparse
import pytest
from harness.attackers.common import validate_source_ip, build_ssh_command

@pytest.mark.parametrize('value',['localhost','example.test','.'.join(['10','0','0','1']),'.'.join(['8','8','8','8'])])
def test_invalid_source(value):
    with pytest.raises(argparse.ArgumentTypeError):
        validate_source_ip(value)

def test_loopback_binding():
    assert validate_source_ip('127.0.0.2') == '127.0.0.2'
    cmd=build_ssh_command('127.0.0.1',2222,'root',source_ip='127.0.0.2')
    assert cmd[cmd.index('-b')+1]=='127.0.0.2'
    assert '-b' not in build_ssh_command('127.0.0.1',2222,'root')
