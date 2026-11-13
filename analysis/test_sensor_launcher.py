"""Lifecycle tests without a running Cowrie; live proof is a separate lab run."""
from sensor.run_sensor import LifecycleBridge
from sensor.adaptive_server import PersonaManager
from gatekeeper.decision_api import GatekeeperClient


def test_real_events_drive_stages_and_cleanup(tmp_path):
    calls = []
    class Engine:
        def decide(self, **kw):
            calls.append(kw)
            return {'target_tier': 'T2' if kw['stage'] == 'S3' else 'T1'}
        def record_session(self, **kw):
            pass
    bridge = LifecycleBridge(Engine(), PersonaManager(base_dir=str(tmp_path)))
    def event(name):
        bridge.event({'session': 'lab-test', 'src_ip': '127.0.0.1', 'eventid': name})
    event('cowrie.session.connect')
    bridge.stage('lab-test', 'S1')
    event('cowrie.login.failed')
    event('cowrie.login.success')
    event('cowrie.client.size')
    event('cowrie.session.params')
    assert [c['stage'] for c in calls] == ['S1', 'S2', 'S2', 'S3']
    assert calls[-1]['features']['cnt_session_params'] == 1
    assert bridge.sessions['lab-test'][0].current_tier == 'T2'
    event('cowrie.session.closed')
    assert not bridge.sessions


def test_unavailable_gatekeeper_stays_cheap(tmp_path, monkeypatch):
    import urllib.request
    def down(*args, **kwargs):
        assert kwargs['timeout'] == .2
        raise ConnectionRefusedError('lab service unavailable')
    monkeypatch.setattr(urllib.request, 'urlopen', down)
    bridge = LifecycleBridge(GatekeeperClient(timeout=.2), PersonaManager(base_dir=str(tmp_path)))
    bridge.event({'session': 'down', 'src_ip': '127.0.0.1', 'eventid': 'cowrie.session.connect'})
    bridge.stage('down', 'S1')
    assert bridge.sessions['down'][0].current_tier == 'T1'
