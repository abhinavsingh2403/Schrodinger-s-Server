"""Check balanced gradients, the convergence criterion and the aggregate ablation."""
import pytest

from analysis.exp0_rules import PurePythonLogisticRegression
from analysis.posthoc_ml_eval import balanced_mass, columns, optimize


def test_balanced_gradient():
    assert balanced_mass(4,1) == pytest.approx((2/3,2))
    m = PurePythonLogisticRegression(C=.01,lr=.1)
    fits = list(optimize([(0.,)]*3+[(1.,)], [0,0,0,1], m, checkpoints=(1,),tol=1))
    assert fits[0][2] == pytest.approx((.025,))
    assert fits[0][3] == pytest.approx(0.)


def test_flat_loss_stops_at_final_requested_checkpoint():
    m = PurePythonLogisticRegression()
    fits = list(optimize([(0.,),(1.,)], [.25,.25], m, checkpoints=(1,4)))
    assert [v[0] for v in fits] == [1,4]
    assert fits[0][1:] == fits[-1][1:]


def test_ablation_retains_order():
    names = ["cnt_client_size","cnt_login_success","cnt_client_var","cnt_session_params","cnt_client_kex"]
    assert columns(names,True) == [1,4]
    assert columns(names,False) == list(range(5))
