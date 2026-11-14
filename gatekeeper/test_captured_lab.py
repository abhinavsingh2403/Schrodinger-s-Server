"""Check semantic lab behaviour and default parity using real captured inputs."""
import hashlib
import json
import subprocess
from pathlib import Path

from gatekeeper.decision_api import DecisionEngine

ROOT = Path(__file__).resolve().parents[1]


def test_captured_profiles(tmp_path):
    capture = json.loads((ROOT / 'harness/demo/fixtures/lab_policy_capture.json').read_text())
    prior = subprocess.check_output(['git', 'show', 'b21810f:gatekeeper/decision_api.py'], text=True)
    scope = {'__file__': str(ROOT / 'gatekeeper/decision_api.py'), '__name__': 'prior_engine'}
    exec(compile(prior, 'prior_engine', 'exec'), scope)
    old_config = subprocess.check_output(['git', 'show', 'b21810f:config/policy.yaml'])
    assert hashlib.sha256(old_config.replace(b'\r\n', b'\n')).digest() == hashlib.sha256(
        (ROOT / 'config/policy.yaml').read_bytes().replace(b'\r\n', b'\n')).digest()
    for scenario in capture['scenarios']:
        name = scenario['scenario']
        lab = DecisionEngine(db_path=tmp_path / (name+'lab.db'), lab_mode=True)
        default = DecisionEngine(db_path=tmp_path / (name+'default.db'))
        old = scope['DecisionEngine'](db_path=tmp_path / (name+'old.db'))
        assert default.policy.thresholds_v2 == old.policy.thresholds_v2
        assert lab.policy.get_threshold_t2('S3') == .5
        tiers = []
        for session in scenario['sessions']:
            current = ['T1'] * 3
            for row in session['adapter_replay']:
                responses = [engine.decide(session['session'], stage=row['stage'], features=row['features'],
                                           current_tier=current[i]) for i, engine in enumerate((lab,default,old))]
                current = [r['tier'] for r in responses]
                assert [(responses[1][k], responses[2][k]) for k in ('score','tier','threshold_applied')] == [
                    (responses[1][k], responses[1][k]) for k in ('score','tier','threshold_applied')]
                tiers.append(current[0])
        assert ('T2' in tiers) == (name == 'interactive')
