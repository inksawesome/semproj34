"""
Offline tests for the parts that normally need a webcam.

    python -m pytest tests/test_pipeline.py -q
"""

import glob
import os
import re
import sys

import av
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ["VT_SAVE_CAPTURES"] = "0"

import liveness_engine as le  # noqa: E402

NEUTRAL = {"faces": 1, "yaw": 2.0, "pitch": 5.0, "blink": 0.05, "smile": 0.05, "ear": 0.3,
           "mouth_ratio": 0.8, "box": (100, 100, 300, 300)}


def _frame():
    return av.VideoFrame.from_ndarray(np.zeros((480, 640, 3), np.uint8), format="bgr24")


def _run(proc, monkeypatch, signals):
    for s in signals:
        monkeypatch.setattr(le, "measure", lambda rgb, s=s: None if s is None else {**NEUTRAL, **s})
        proc.recv(_frame())


ACTIONS = {
    "BLINK": [{"blink": 0.8}, {"blink": 0.05}, {"blink": 0.8}, {"blink": 0.05}],
    "TURN_LEFT": [{"yaw": -10}, {"yaw": -20}],          # baseline yaw 2 -> delta -22
    "TURN_RIGHT": [{"yaw": 15}, {"yaw": 25}],
    "SMILE": [{"smile": 0.7}],
    "LOOK_UP": [{"pitch": -3}, {"pitch": -10}],          # baseline pitch 5 -> 15° up
}


@pytest.mark.parametrize("first,second", [("BLINK", "TURN_LEFT"), ("SMILE", "LOOK_UP"), ("TURN_RIGHT", "BLINK")])
def test_liveness_passes_when_actions_performed(monkeypatch, first, second):
    p = le.LivenessProcessor()
    p.challenges = [first, second]
    _run(p, monkeypatch, [{}] * le.CALIBRATION_FRAMES)
    assert p.state == "CHALLENGE" and p.baseline["yaw"] == 2.0
    _run(p, monkeypatch, ACTIONS[first] + ACTIONS[second])
    snap = p.snapshot()
    assert snap["state"] == "PASSED", snap["fail_reason"]
    assert [r["name"] for r in snap["results"]] == [first, second]
    assert len(snap["clean_frames"]) == le.CLEAN_FRAMES_KEPT
    assert snap["timeline"] and snap["timeline"][-1]["phase"] == second


def test_wrong_direction_does_not_pass(monkeypatch):
    p = le.LivenessProcessor()
    p.challenges = ["TURN_LEFT", "BLINK"]
    _run(p, monkeypatch, [{}] * le.CALIBRATION_FRAMES)
    _run(p, monkeypatch, ACTIONS["TURN_RIGHT"] * 5)
    assert p.state == "CHALLENGE" and p.idx == 0


def test_timeout_fails(monkeypatch):
    p = le.LivenessProcessor()
    _run(p, monkeypatch, [{}] * le.CALIBRATION_FRAMES)
    p._challenge_start -= le.CHALLENGE_TIMEOUT + 1
    _run(p, monkeypatch, [{}])
    assert p.state == "FAILED" and "Timed out" in p.fail_reason


def test_second_face_fails(monkeypatch):
    p = le.LivenessProcessor()
    _run(p, monkeypatch, [{}] * le.CALIBRATION_FRAMES)
    _run(p, monkeypatch, [{"faces": 2}])
    assert p.state == "FAILED"


def test_calibration_requires_frontal_face(monkeypatch):
    p = le.LivenessProcessor()
    _run(p, monkeypatch, [{"yaw": 30}] * 40 + [None] * 10)
    assert p.state == "CALIBRATE" and not p.clean_frames


def test_real_landmarker_runs_in_worker_thread():
    """recv() must return a processed frame with the real MediaPipe model (no stubbed measure)."""
    import threading

    import cv2
    path = sorted(glob.glob("LCC_FASD_development/real/*_id48_*"))[0]
    img = cv2.resize(cv2.copyMakeBorder(cv2.imread(path), 60, 60, 120, 120, cv2.BORDER_REPLICATE), (640, 480))
    p = le.LivenessProcessor()
    out = []
    t = threading.Thread(target=lambda: out.append(p.recv(av.VideoFrame.from_ndarray(img, format="bgr24"))))
    t.start()
    t.join(timeout=30)
    assert not t.is_alive(), "recv() hung (lock deadlock?)"
    assert out and p.timeline, "landmarker produced no measurement"
    assert le.measure(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))["faces"] == 1


# ------------------------------------------------------------------ verification pipeline

def _subject_images():
    import cv2
    by = {}
    for path in sorted(glob.glob("LCC_FASD_development/real/*")):
        m = re.search(r"_id(\d+)_", path)
        if m:
            by.setdefault(m.group(1), []).append(path)
    subjects = [s for s in sorted(by) if len(by[s]) >= 8][:2]
    load = lambda p: cv2.copyMakeBorder(cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB), 40, 40, 40, 40,
                                        cv2.BORDER_REPLICATE)
    return [[load(p) for p in by[s][:8]] for s in subjects]


NEUTRAL_SIG = {"yaw": 0.0, "pitch": 0.0, "blink": 0.1, "smile": 0.1}


@pytest.mark.slow
def test_verify_presence_genuine_and_impostor():
    import biometric_template
    import face_engine
    from ui_components import verify_presence

    a, b = _subject_images()
    key = biometric_template.new_key()
    user = {"template": biometric_template.protect(face_engine.embed_best(a[:4]), key), "template_key": key}
    snap = {"state": "PASSED", "challenges": ["BLINK", "SMILE"], "fail_reason": None, "baseline": None,
            "results": [{"name": "BLINK", "passed": True, "seconds": 1.2, "peak": 0.8},
                        {"name": "SMILE", "passed": True, "seconds": 0.9, "peak": 0.7}],
            "timeline": [], "clean_frames": a[4:],
            "challenge_frames": [(f, NEUTRAL_SIG) for f in a[4:]]}

    genuine = verify_presence(snap, user)
    assert genuine["match_passed"], genuine["match_score"]
    assert genuine["continuity_passed"] and genuine["continuity"]["identity"] > 0.35
    # swap: the account owner's face at calibration, somebody else during the challenges
    swap = verify_presence({**snap, "challenge_frames": [(f, NEUTRAL_SIG) for f in b[:4]]}, user)
    assert swap["match_passed"] and not swap["continuity_passed"] and not swap["passed"]
    assert any("not the face seen at the start" in r for r in swap["reasons"])
    nothing = verify_presence({**snap, "challenge_frames": []}, user)
    assert not nothing["passed"] and any("No frames were captured during the challenges" in r
                                         for r in nothing["reasons"])
    impostor = verify_presence({**snap, "clean_frames": b[:4]}, user)
    assert not impostor["match_passed"] and not impostor["passed"]
    assert any("does not match" in r for r in impostor["reasons"])
    failed = verify_presence({**snap, "state": "FAILED", "fail_reason": "Timed out on 'Smile'"}, user)
    assert not failed["passed"] and "Timed out" in failed["reasons"][0]


def test_blink_with_high_resting_eye_closure(monkeypatch):
    """Glasses / looking down give a high resting eyeBlink score; blinking must still register."""
    p = le.LivenessProcessor()
    p.challenges = ["BLINK", "SMILE"]
    _run(p, monkeypatch, [{"blink": 0.45}] * le.CALIBRATION_FRAMES)
    _run(p, monkeypatch, [{"blink": 0.5}] * 3)                      # resting noise: no blink
    assert p.idx == 0
    _run(p, monkeypatch, [{"blink": 0.9}, {"blink": 0.45}, {"blink": 0.9}, {"blink": 0.45}])
    assert p.idx == 1


# ------------------------------------------------------------------ continuity (swap attacks)

def test_face_jump_during_challenge_fails(monkeypatch):
    p = le.LivenessProcessor()
    _run(p, monkeypatch, [{}] * le.CALIBRATION_FRAMES)
    _run(p, monkeypatch, [{"box": (400, 100, 600, 300)}])            # same size, 1.5 face-widths away
    assert p.state == "FAILED" and "different face" in p.fail_reason


def test_face_rescale_during_challenge_fails(monkeypatch):
    p = le.LivenessProcessor()
    _run(p, monkeypatch, [{}] * le.CALIBRATION_FRAMES)
    _run(p, monkeypatch, [{"box": (150, 150, 250, 250)}])            # half the size, same centre
    assert p.state == "FAILED"


def test_face_gap_during_challenge_fails(monkeypatch):
    p = le.LivenessProcessor()
    _run(p, monkeypatch, [{}] * le.CALIBRATION_FRAMES)
    p._last_seen -= le.GAP_LIMIT + 0.1                              # the face vanished a moment ago
    _run(p, monkeypatch, [None])
    assert p.state == "FAILED" and "left the view" in p.fail_reason


def test_short_detection_dropout_is_tolerated(monkeypatch):
    p = le.LivenessProcessor()
    p.challenges = ["BLINK", "SMILE"]
    _run(p, monkeypatch, [{}] * le.CALIBRATION_FRAMES)
    _run(p, monkeypatch, [None, None, {}])                          # a couple of missed frames, same face
    assert p.state == "CHALLENGE"


def test_natural_movement_is_not_a_jump(monkeypatch):
    p = le.LivenessProcessor()
    p.challenges = ["TURN_RIGHT", "BLINK"]
    _run(p, monkeypatch, [{}] * le.CALIBRATION_FRAMES)
    drift = [{"box": (100 + 8 * i, 100 + 3 * i, 300 + 8 * i, 300 + 3 * i), "yaw": 2 + 3 * i} for i in range(1, 9)]
    _run(p, monkeypatch, drift)                                      # head turning and drifting smoothly
    assert p.state == "CHALLENGE" and p.idx == 1


def test_swap_during_calibration_restarts_it(monkeypatch):
    p = le.LivenessProcessor()
    _run(p, monkeypatch, [{}] * 12)                                  # e.g. a phone held up
    assert len(p.clean_frames) == 6
    _run(p, monkeypatch, [{"box": (420, 120, 620, 320)}])            # ...then a different face appears
    assert p.state == "CALIBRATE" and len(p.clean_frames) == 0 and p.continuity["restarts"] == 1


def test_challenge_frames_are_sampled(monkeypatch):
    p = le.LivenessProcessor()
    p.challenges = ["BLINK", "SMILE"]
    _run(p, monkeypatch, [{}] * le.CALIBRATION_FRAMES)
    _run(p, monkeypatch, [{}] * 30 + ACTIONS["BLINK"] + ACTIONS["SMILE"])
    snap = p.snapshot()
    assert snap["state"] == "PASSED" and 1 <= len(snap["challenge_frames"]) <= le.CHALLENGE_FRAMES_MAX
    frame, signals = snap["challenge_frames"][0]
    assert frame.shape == (480, 640, 3) and set(signals) == {"yaw", "pitch", "blink", "smile"}
