"""
Active liveness (Component 3) as a streamlit-webrtc video processor.

Flow per attempt
----------------
1. CALIBRATE  user looks straight at the camera. We record their personal
              baseline (neutral yaw/pitch, eye openness, mouth width) and
              keep clean frames for passive anti-spoofing + face matching.
2. CHALLENGE  two random challenges in sequence, each judged *relative to
              the baseline* (so it works for every face shape / camera tilt).
3. PASSED / FAILED

Continuity: one live face must stay in view from calibration to the last
challenge. Otherwise an attacker can show a photo or phone during
calibration (the frames that are scored for anti-spoofing and identity) and
then step in to perform the challenges - a swap seen in testing on 10 Oct.
  * calibration restarts (and drops its frames) if the face disappears for
    more than GAP_LIMIT or jumps to a different position/size;
  * during the challenges the same events fail the attempt;
  * frames are also sampled during the challenges, so the server can check
    they show the same person and pass anti-spoofing too.

Signals come from the MediaPipe FaceLandmarker:
  * head pose  - the 4x4 facial transformation matrix (true yaw/pitch in °)
  * blink      - eyeBlinkLeft/Right blendshapes + classic EAR for the plot
  * smile      - mouthSmileLeft/Right blendshapes + mouth-width ratio

Every frame's signals are kept in `timeline` so the XAI page can plot
exactly what the verifier saw.
"""

import logging
import math
import random
import sys
import threading
import time

import av
import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions
from streamlit_webrtc import VideoProcessorBase

CHALLENGES = {
    "BLINK": "Blink twice",
    "TURN_LEFT": "Turn your head LEFT",
    "TURN_RIGHT": "Turn your head RIGHT",
    "SMILE": "Smile",
    "LOOK_UP": "Look UP",
}
N_CHALLENGES = 2
CALIBRATION_FRAMES = 20
CLEAN_FRAMES_KEPT = 10
CHALLENGE_TIMEOUT = 9.0

YAW_DELTA = 18.0        # degrees away from the user's neutral yaw
PITCH_DELTA = 12.0
BLINK_CLOSED = 0.45     # eyeBlink blendshape score
BLINK_OPEN = 0.25
SMILE_SCORE = 0.45      # mouthSmile blendshape score

GAP_LIMIT = 0.7         # seconds without a face before continuity is broken
JUMP_SHIFT = 0.5        # face-box centre moving more than this x face width between detections
JUMP_SCALE = 1.5        # or the face box growing/shrinking by more than this factor
CHALLENGE_FRAME_EVERY = 3
CHALLENGE_FRAMES_MAX = 24

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

log = logging.getLogger("vaulttrust.liveness")
if not log.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(asctime)s LIVENESS %(message)s", "%H:%M:%S"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)

_landmarker = None
from mediapipe_face import MP_LOCK as _lm_lock  # one re-entrant lock for every MediaPipe call in the process


def _get_landmarker():
    global _landmarker
    with _lm_lock:
        if _landmarker is None:
            _landmarker = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path="face_landmarker.task"),
                num_faces=2,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
            ))
    return _landmarker


def _ear(pts):
    d = lambda a, b: math.dist(pts[a], pts[b])
    return (d(1, 5) + d(2, 4)) / (2.0 * d(0, 3) + 1e-6)


def measure(rgb: np.ndarray):
    """Run the landmarker on one RGB frame; returns a dict of signals or None."""
    h, w = rgb.shape[:2]
    small = cv2.resize(rgb, (480, int(480 * h / w))) if w > 480 else rgb
    with _lm_lock:
        res = _get_landmarker().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=small))
    if not res.face_landmarks:
        return None
    lm = res.face_landmarks[0]
    px = lambda i: (lm[i].x * w, lm[i].y * h)
    bs = {b.category_name: b.score for b in res.face_blendshapes[0]}
    rot = np.array(res.facial_transformation_matrixes[0])[:3, :3]
    xs = [p.x * w for p in lm]
    ys = [p.y * h for p in lm]
    return {
        "faces": len(res.face_landmarks),
        "yaw": float(np.degrees(np.arctan2(rot[0, 2], rot[2, 2]))),     # + = nose to image-right
        "pitch": float(np.degrees(np.arcsin(-rot[1, 2]))),               # + = looking down
        "blink": (bs["eyeBlinkLeft"] + bs["eyeBlinkRight"]) / 2,
        "smile": (bs["mouthSmileLeft"] + bs["mouthSmileRight"]) / 2,
        "ear": (_ear([px(i) for i in LEFT_EYE]) + _ear([px(i) for i in RIGHT_EYE])) / 2,
        "mouth_ratio": math.dist(px(61), px(291)) / (math.dist(px(33), px(263)) + 1e-6),
        "box": (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))),
    }


def face_jump(prev_box, box):
    """True if the face box moved or rescaled too much to be the same face moving naturally."""
    pw, cw = max(prev_box[2] - prev_box[0], 1), max(box[2] - box[0], 1)
    pc = ((prev_box[0] + prev_box[2]) / 2, (prev_box[1] + prev_box[3]) / 2)
    cc = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    scale = cw / pw
    return math.dist(pc, cc) / pw > JUMP_SHIFT or scale > JUMP_SCALE or scale < 1 / JUMP_SCALE


class LivenessProcessor(VideoProcessorBase):
    def __init__(self):
        self.state = "CALIBRATE"           # CALIBRATE -> CHALLENGE -> PASSED | FAILED
        self.challenges = random.sample(list(CHALLENGES), N_CHALLENGES)
        self.idx = 0
        self.results = []                  # per challenge: {name, passed, seconds, peak}
        self.fail_reason = None
        self.clean_frames = []             # RGB frames captured while neutral
        self.challenge_frames = []         # (RGB frame, signals) sampled during the challenges
        self.continuity = {"restarts": 0, "max_gap": 0.0, "max_shift": 0.0}
        self._last_box = None
        self._last_seen = None
        self._challenge_count = 0
        self.timeline = []                 # per-frame signals for the XAI plot
        self.baseline = None
        self._calib = []
        self._t0 = time.time()
        self._challenge_start = None
        self._blinks = 0
        self._eyes_closed = False
        self._peak = 0.0
        self._frames_seen = 0
        self._frames_with_face = 0
        self.lock = threading.Lock()

    # ------------------------------------------------------------ helpers
    def _restart_calibration(self, why):
        if self._calib or self.clean_frames:
            self.continuity["restarts"] += 1
            log.info("calibration restarted: %s", why)
        self._calib.clear()
        self.clean_frames.clear()

    def _continuity(self, m, now):
        """Track the face between frames. Returns a reason string if continuity broke."""
        if m is None:
            if self._last_seen is not None and now - self._last_seen > GAP_LIMIT:
                self.continuity["max_gap"] = max(self.continuity["max_gap"], round(now - self._last_seen, 2))
                return f"face out of view for {now - self._last_seen:.1f}s"
            return None
        reason = None
        if self._last_box is not None:
            pw = max(self._last_box[2] - self._last_box[0], 1)
            pc = ((self._last_box[0] + self._last_box[2]) / 2, (self._last_box[1] + self._last_box[3]) / 2)
            cc = ((m["box"][0] + m["box"][2]) / 2, (m["box"][1] + m["box"][3]) / 2)
            self.continuity["max_shift"] = max(self.continuity["max_shift"], round(math.dist(pc, cc) / pw, 2))
            if face_jump(self._last_box, m["box"]):
                reason = "face jumped to a different position"
        if self._last_seen is not None:
            self.continuity["max_gap"] = max(self.continuity["max_gap"], round(now - self._last_seen, 2))
        self._last_box, self._last_seen = m["box"], now
        return reason

    def _start_challenge(self):
        self._challenge_start = time.time()
        self._blinks, self._eyes_closed, self._peak = 0, False, 0.0
        self._frames_seen = self._frames_with_face = 0

    def _check_challenge(self, m):
        """Returns (passed, progress 0..1) for the current challenge."""
        name, b = self.challenges[self.idx], self.baseline
        if name == "BLINK":
            # relative to the user's resting eye closure (glasses / looking down raise it)
            closed = min(0.85, max(BLINK_CLOSED, b["blink"] + 0.3))
            opened = max(BLINK_OPEN, b["blink"] + 0.1)
            if m["blink"] > closed and not self._eyes_closed:
                self._eyes_closed = True
            elif m["blink"] < opened and self._eyes_closed:
                self._eyes_closed = False
                self._blinks += 1
            self._peak = max(self._peak, m["blink"])
            return self._blinks >= 2, self._blinks / 2
        if name in ("TURN_LEFT", "TURN_RIGHT"):
            delta = m["yaw"] - b["yaw"]
            # Display is mirrored: the user's left is the image's left (negative yaw).
            signed = -delta if name == "TURN_LEFT" else delta
            self._peak = max(self._peak, signed)
            return signed > YAW_DELTA, max(0.0, signed) / YAW_DELTA
        if name == "LOOK_UP":
            up = b["pitch"] - m["pitch"]
            self._peak = max(self._peak, up)
            return up > PITCH_DELTA, max(0.0, up) / PITCH_DELTA
        if name == "SMILE":
            self._peak = max(self._peak, m["smile"])
            need = max(SMILE_SCORE, b["smile"] + 0.25)
            return m["smile"] > need, m["smile"] / need
        return False, 0.0

    # ------------------------------------------------------------ main loop
    def recv(self, frame):
        bgr = cv2.flip(frame.to_ndarray(format="bgr24"), 1)  # mirror for natural UX
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        t = time.time() - self._t0

        with self.lock:
            m = measure(rgb) if self.state in ("CALIBRATE", "CHALLENGE") else None
            progress = 0.0

            if m is not None:
                self.timeline.append({"t": round(t, 3), "phase": self.state if self.state != "CHALLENGE"
                                      else self.challenges[self.idx], **{k: m[k] for k in
                                      ("yaw", "pitch", "blink", "smile", "ear", "mouth_ratio")}})

            broken = self._continuity(m, time.time()) if self.state in ("CALIBRATE", "CHALLENGE") else None

            if self.state == "CALIBRATE":
                if broken or (m is not None and m["faces"] > 1):
                    # A different presentation may have replaced the first one: start again from scratch.
                    self._restart_calibration(broken or "more than one face")
                    if broken and m is None:
                        self._last_seen = None          # wait quietly for a face to come back
                frontal = m is not None and m["faces"] == 1 and abs(m["yaw"]) < 15 and abs(m["pitch"]) < 20
                if frontal:
                    self._calib.append(m)
                    if len(self._calib) % 2 == 0 and len(self.clean_frames) < CLEAN_FRAMES_KEPT:
                        self.clean_frames.append(rgb.copy())
                elif self._calib:
                    self._calib.pop(0)  # must hold still; decay instead of hard reset
                progress = len(self._calib) / CALIBRATION_FRAMES
                if len(self._calib) >= CALIBRATION_FRAMES:
                    self.baseline = {k: float(np.median([c[k] for c in self._calib]))
                                     for k in ("yaw", "pitch", "blink", "smile", "ear", "mouth_ratio")}
                    self.state = "CHALLENGE"
                    self._start_challenge()
                    log.info("calibrated baseline=%s challenges=%s",
                             {k: round(v, 3) for k, v in self.baseline.items()}, self.challenges)

            elif self.state == "CHALLENGE":
                self._frames_seen += 1
                if broken:
                    self.state = "FAILED"
                    self.fail_reason = ("Face left the view during the check" if m is None
                                        else "A different face appeared during the check")
                    self.results.append({"name": self.challenges[self.idx], "passed": False,
                                         "seconds": round(time.time() - self._challenge_start, 2),
                                         "peak": round(self._peak, 3)})
                    log.info("failed: continuity broken (%s)", broken)
                elif m is not None:
                    self._challenge_count += 1
                    if self._challenge_count % CHALLENGE_FRAME_EVERY == 0:
                        self.challenge_frames.append((rgb.copy(), {k: m[k] for k in ("yaw", "pitch", "blink",
                                                                                     "smile")}))
                        if len(self.challenge_frames) > CHALLENGE_FRAMES_MAX:
                            self.challenge_frames = self.challenge_frames[::2]   # keep them spread out
                    self._frames_with_face += 1
                    if m["faces"] > 1:
                        self.state, self.fail_reason = "FAILED", "More than one face in view"
                        log.info("failed: more than one face")
                    else:
                        passed, progress = self._check_challenge(m)
                        if passed:
                            self.results.append({"name": self.challenges[self.idx], "passed": True,
                                                 "seconds": round(time.time() - self._challenge_start, 2),
                                                 "peak": round(self._peak, 3)})
                            log.info("passed %s in %.1fs peak=%.2f", *(self.results[-1][k] for k in
                                                                     ("name", "seconds", "peak")))
                            self.idx += 1
                            if self.idx >= len(self.challenges):
                                self.state = "PASSED"
                            else:
                                self._start_challenge()
                if self.state == "CHALLENGE" and time.time() - self._challenge_start > CHALLENGE_TIMEOUT:
                    self.results.append({"name": self.challenges[self.idx], "passed": False,
                                         "seconds": CHALLENGE_TIMEOUT, "peak": round(self._peak, 3)})
                    self.state = "FAILED"
                    self.fail_reason = f"Timed out on '{CHALLENGES[self.challenges[self.idx]]}'"
                    last = self.timeline[-1] if self.timeline else {}
                    log.info("timed out on %s peak=%.2f last=%s", self.challenges[self.idx], self._peak,
                             {k: round(last[k], 3) for k in ("yaw", "pitch", "blink", "smile") if k in last})

            self._draw(bgr, m, progress)
        return av.VideoFrame.from_ndarray(bgr, format="bgr24")

    # ------------------------------------------------------------ overlay
    def _draw(self, img, m, progress):
        h, w = img.shape[:2]
        if m is not None:
            x1, y1, x2, y2 = m["box"]
            colour = (191, 212, 45) if self.state != "FAILED" else (113, 113, 248)
            cv2.rectangle(img, (x1, y1), (x2, y2), colour, 2)

        strip = img[:64]                     # darken only the banner area (no full-frame copy)
        strip[:] = (strip * 0.25 + np.array((32, 18, 11)) * 0.75).astype(np.uint8)

        if self.state == "CALIBRATE":
            title = "Look straight at the camera" if m is not None else "No face detected"
            sub = "Calibrating to your face..."
        elif self.state == "CHALLENGE":
            title = f"{self.idx + 1}/{len(self.challenges)}  {CHALLENGES[self.challenges[self.idx]]}"
            left = max(0.0, CHALLENGE_TIMEOUT - (time.time() - self._challenge_start))
            sub = f"{left:.0f}s left"
        elif self.state == "PASSED":
            title, sub, progress = "Liveness confirmed", "Processing...", 1.0
        else:
            title, sub = "Liveness failed", self.fail_reason or ""

        cv2.putText(img, title, (16, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, sub, (16, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (189, 155, 138), 1, cv2.LINE_AA)
        cv2.rectangle(img, (0, 62), (int(w * min(1.0, progress)), 64), (191, 212, 45), -1)

    # ------------------------------------------------------------ result
    def status(self):
        """Cheap progress summary for the instruction panel (no frames copied)."""
        with self.lock:
            left = None
            if self.state == "CHALLENGE" and self._challenge_start is not None:
                left = max(0.0, CHALLENGE_TIMEOUT - (time.time() - self._challenge_start))
            return {"state": self.state, "challenges": list(self.challenges), "idx": self.idx,
                    "passed": [r["name"] for r in self.results if r["passed"]],
                    "calibration": min(1.0, len(self._calib) / CALIBRATION_FRAMES),
                    "seconds_left": left, "fail_reason": self.fail_reason,
                    "restarts": self.continuity["restarts"]}

    def snapshot(self):
        with self.lock:
            return {
                "state": self.state,
                "challenges": list(self.challenges),
                "results": list(self.results),
                "fail_reason": self.fail_reason,
                "baseline": dict(self.baseline) if self.baseline else None,
                "timeline": list(self.timeline),
                "clean_frames": list(self.clean_frames),
                "challenge_frames": list(self.challenge_frames),
                "continuity": dict(self.continuity),
            }
