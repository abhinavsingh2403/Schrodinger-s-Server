"""Verify whole-group shuffling and stable boundary selection."""
from analysis.null_diagnosis import block_shuffle, direct


def test_vectors_remain_whole():
    y = [1,1,0,0,1]
    out = block_shuffle(y,['a','a','b','b','c'])
    assert sorted([out[:2],out[2:4]]) == [[0,0],[1,1]]
    assert out[4] == 1


def test_direct_respects_tie_order():
    y = [1]+[0]*9
    assert direct([0]*10,y,range(10)) == 1
    assert direct([0]*10,y,reversed(range(10))) == 0
