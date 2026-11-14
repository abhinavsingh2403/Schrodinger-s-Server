"""Explain captured live S3 scores against the identical offline counter vector."""
import json
import tempfile
from pathlib import Path
from gatekeeper.decision_api import DecisionEngine
from gatekeeper.features import stage_vector, STAGE_ALLOWED_FEATURES


def diagnose(root):
    proof = json.loads((root/'results/exp0/lab_policy_proof.json').read_text())['DEFAULT']
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        engine = DecisionEngine(db_path=Path(folder)/'diagnostic.db')
        for scenario in proof['scenarios']:
            for session in scenario['sessions']:
                live = [r for r in session['adapter_replay'] if r['stage']=='S3']
                offline = [r for r in session['extractor_replay'] if r['stage']=='S3']
                stored = [r for r in session['decisions'] if r['stage']=='S3']
                for a,b,c in zip(live,offline,stored):
                    vector = stage_vector('S3',a['features'])
                    other = stage_vector('S3',b['features'])
                    score, source, _ = engine.score_features('S3',a['features'])
                    assert vector == other
                    assert abs(score-c['score']) < 1e-12
                    rows.append({'scenario':scenario['scenario'],'session':session['session'],
                        'live_vector':vector,'offline_vector':other,'all_zero':not any(vector),
                        'missing_fields':[k for k in STAGE_ALLOWED_FEATURES['S3'] if k not in a['features']],
                        'stored_score':c['score'],'recomputed_score':score,'score_source':source})
        zero_score = engine.score_features('S3',{})[0]
        pty_index = STAGE_ALLOWED_FEATURES['S3'].index('cnt_client_size')
        pty_effect = {'feature':'cnt_client_size', 'weight':engine.model.weights[pty_index],
                      'range':engine.model.ranges[pty_index],
                      'logit_change_per_event':engine.model.weights[pty_index]/engine.model.ranges[pty_index]}
    return {'provenance':'LAB captured DEFAULT proof; no model or feature changes',
            'features':STAGE_ALLOWED_FEATURES['S3'],'zero_vector_score':zero_score,
            'pty_model_effect':pty_effect,'rows':rows}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    result = diagnose(root)
    (root/'results/exp0/lab_s3_diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    for name in dict.fromkeys(r['scenario'] for r in result['rows']):
        rows = [r for r in result['rows'] if r['scenario']==name]
        print(name, sorted({tuple(r['live_vector']) for r in rows}), sorted({r['stored_score'] for r in rows}))
