import time
import sys, os
# Ensure project root in path for test imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.ai_core.drowsiness_fusion import get_fusion


def test_eye_closure_accumulates_score():
    f = get_fusion()
    f.score = 0
    # simulate 30 frames of eye closed
    t = time.time()
    for i in range(30):
        # use small positive EAR to avoid triggering sunglasses heuristic in tests
        res = f.update(ear=0.12, mar=0.0, is_yawning=False, pitch=0.0, timestamp=t + i*0.033)
    assert res['score'] >= 10


def test_yawn_adds_weight():
    f = get_fusion()
    f.score = 0
    t = time.time()
    res = f.update(ear=0.3, mar=0.8, is_yawning=True, pitch=0.0, timestamp=t)
    assert res['score'] >= 3


def test_nod_detection_adds_score():
    f = get_fusion()
    f.score = 0
    # create a small sequence to trigger nod detector: up -> down -> up
    t = time.time()
    seq = [0.0, -12.0, 0.0]
    for i, p in enumerate(seq):
        res = f.update(ear=0.3, mar=0.0, is_yawning=False, pitch=p, timestamp=t + i*0.5)
    assert res['nod'] is True or res['score'] >= 1
