"""Check launcher identity overrides against the declared YAML scalar values."""
from pathlib import Path
from sensor.run_sensor import identity_overrides


def test_identity_overrides():
    root = Path(__file__).resolve().parents[1]
    config = {}
    for line in (root / 'config/identity.yaml').read_text().splitlines():
        if line and line[0].isalpha() and ':' in line:
            k, v = line.split(':', 1)
            config[k] = v.strip().strip('"')
    overrides = identity_overrides()
    for env, key in [('HONEYPOT_HOSTNAME','hostname'), ('SHELL_KERNEL_VERSION','kernel'),
                     ('SHELL_HARDWARE_PLATFORM','arch'), ('SSH_VERSION','banner')]:
        assert overrides['COWRIE_'+env] == config[key]
    assert overrides['COWRIE_SHELL_KERNEL_BUILD_STRING'] == config['kernel_build_string']
    assert Path(overrides['COWRIE_HONEYPOT_CONTENTS_PATH']) == root / 'sensor/honeyfs'
