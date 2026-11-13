"""Distribution and budget invariants independent of the experiment outcome."""
import random
import statistics
from analysis.exp0_rules import recall_at_budget


def test_equal_scores_average_is_budget():
    labels = [1]*100 + [0]*900
    mean = statistics.mean(recall_at_budget([0.0]*1000,labels,.1,seed=s) for s in range(300))
    assert abs(mean-.1)<.015


def test_random_scores_average_is_budget():
    labels = [1]*100 + [0]*900
    values=[]
    for seed in range(300):
        rng=random.Random(seed)
        values.append(recall_at_budget([rng.random() for _ in labels],labels,.1))
    assert abs(statistics.mean(values)-.1)<.015


def test_perfect_separation_and_exact_budget():
    labels=[1]*100+[0]*900
    assert recall_at_budget(labels,labels,.1)==1
    assert recall_at_budget([0]*1000,[1]*1000,.1)==.1
