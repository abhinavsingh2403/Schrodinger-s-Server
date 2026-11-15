"""Same-session S5 rule is lab-only and leaves fresh default admission unchanged."""
import pytest
from gatekeeper.decision_api import DecisionEngine

@pytest.mark.parametrize('lab',[False,True])
def test_s5_rule(tmp_path,lab):
    engine=DecisionEngine(db_path=tmp_path/'test.db',lab_mode=lab)
    tiers=[]
    current='T1'
    for count in range(1,5):
        result=engine.decide('same',stage='S4' if count==1 else 'S5',features={'session_command_count':count},current_tier=current)
        tiers.append(result['tier']);current=result['tier']
    assert tiers==(['T1','T1','T2','T2'] if lab else ['T1']*4)
    if lab: assert result['score_source']=='LAB_DEMO_NOT_ML_s5_command_count'
