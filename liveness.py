"""
Passive and active liveness helpers for the Streamlit camera flow.

The checks in this module are deliberately local and explainable. They raise
the bar against low-effort attacks (blurred screenshots, printed images and
single replayed captures), but they are not a replacement for a trained PAD
(presentation-attack-detection) model in a high-security deployment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


_GLOBAL_LANDMARKER = None


# ============================================================
# FACE LANDMARK CONFIGURATION
# ============================================================

LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)

NOSE_TIP = 1
FACE_LEFT = 234
FACE_RIGHT = 454


# ============================================================
# RESULT OBJECT
# ============================================================

@dataclass
class LivenessResult:
    passed: bool
    reasons: list[str]
    metrics: dict[str, float]
    landmarks: Any | None = None


# ============================================================
# BASIC GEOMETRY
# ============================================================

def _distance(a: Any, b: Any) -> float:
    return float(np.hypot(a.x - b.x, a.y - b.y))


def _eye_aspect_ratio(
    landmarks: Any,
    indices: tuple[int, ...]
) -> float:

    p1, p2, p3, p4, p5, p6 = (
        landmarks[index] for index in indices
    )

    horizontal = _distance(p1, p4)

    if horizontal <= 1e-6:
        return 0.0

    return (
        _distance(p2, p6)
        + _distance(p3, p5)
    ) / (2.0 * horizontal)


# ============================================================
# LANDMARK METRICS
# ============================================================

def landmark_metrics(landmarks: Any) -> dict[str, float]:
    """
    Return normalized, frame-size-independent face measurements.
    """

    left = landmarks[FACE_LEFT]
    right = landmarks[FACE_RIGHT]

    face_width = max(
        abs(right.x - left.x),
        1e-6
    )

    nose_position = (
        landmarks[NOSE_TIP].x
        - min(left.x, right.x)
    ) / face_width

    ear = (
        _eye_aspect_ratio(
            landmarks,
            LEFT_EYE
        )
        +
        _eye_aspect_ratio(
            landmarks,
            RIGHT_EYE
        )
    ) / 2.0

    return {
        "ear": float(ear),
        "nose_position": float(nose_position),
    }


# ============================================================
# PASSIVE LIVENESS
# ============================================================

def passive_liveness_check(
    image_rgb: np.ndarray
) -> LivenessResult:

    """
    Run lightweight passive checks and obtain landmarks
    for active liveness checks.
    """

    if image_rgb is None or image_rgb.size == 0:

        return LivenessResult(
            False,
            ["The camera image could not be read."],
            {}
        )

    gray = cv2.cvtColor(
        image_rgb,
        cv2.COLOR_RGB2GRAY
    )

    brightness = float(np.mean(gray))

    sharpness = float(
        cv2.Laplacian(
            gray,
            cv2.CV_64F
        ).var()
    )

    reasons: list[str] = []

    # --------------------------------------------------------
    # Brightness
    # --------------------------------------------------------

    if brightness < 45:

        reasons.append(
            "Image is too dark. Improve front lighting."
        )

    elif brightness > 220:

        reasons.append(
            "Image is overexposed. Reduce direct lighting."
        )

    # --------------------------------------------------------
    # Sharpness
    # --------------------------------------------------------

    if sharpness < 35:

        reasons.append(
            "Image is too blurry. Hold the camera still and retry."
        )

    # --------------------------------------------------------
    # MediaPipe FaceLandmarker
    # --------------------------------------------------------
    
    global _GLOBAL_LANDMARKER
    if _GLOBAL_LANDMARKER is None:
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision import FaceLandmarkerOptions, FaceLandmarker
        
        base_options = BaseOptions(model_asset_path='face_landmarker.task')
        options = FaceLandmarkerOptions(
            base_options=base_options,
            num_faces=2,
            min_face_detection_confidence=0.6,
            min_face_presence_confidence=0.6,
            min_tracking_confidence=0.6)
        _GLOBAL_LANDMARKER = FaceLandmarker.create_from_options(options)

    import mediapipe as mp
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
    result = _GLOBAL_LANDMARKER.detect(mp_image)

    faces = result.face_landmarks or []

    # --------------------------------------------------------
    # Face count
    # --------------------------------------------------------

    if len(faces) != 1:

        reasons.append(
            "Show exactly one face to the camera."
            if faces
            else
            "No face was detected. Face the camera and retry."
        )

        return LivenessResult(
            False,
            reasons,
            {
                "brightness": brightness,
                "sharpness": sharpness,
                "face_count": float(len(faces)),
            }
        )

    # --------------------------------------------------------
    # Face landmarks
    # --------------------------------------------------------

    landmarks = faces[0]

    xs = [point.x for point in landmarks]
    ys = [point.y for point in landmarks]

    face_area = (
        max(xs) - min(xs)
    ) * (
        max(ys) - min(ys)
    )

    if face_area < 0.08:

        reasons.append(
            "Move closer to the camera so your face fills more of the frame."
        )

    elif face_area > 0.82:

        reasons.append(
            "Move slightly back so your entire face is visible."
        )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    metrics = {
        "brightness": brightness,
        "sharpness": sharpness,
        "face_area": float(face_area),
        "face_count": float(len(faces)),
    }

    metrics.update(
        landmark_metrics(landmarks)
    )

    return LivenessResult(
        not reasons,
        reasons,
        metrics,
        landmarks
    )


# ============================================================
# NEUTRAL BASELINE VALIDATION
# ============================================================

def validate_neutral_baseline(
    metrics: dict[str, float]
) -> LivenessResult:

    """
    Validate the metrics collected during the neutral
    baseline stage.
    """

    reasons: list[str] = []

    if not metrics:

        return LivenessResult(
            False,
            ["Neutral baseline could not be captured."],
            {}
        )

    # --------------------------------------------------------
    # Required metrics
    # --------------------------------------------------------

    required = [
        "brightness",
        "sharpness",
        "face_area",
        "ear",
        "nose_position",
    ]

    missing = [
        key
        for key in required
        if key not in metrics
    ]

    if missing:

        reasons.append(
            "Missing baseline measurements: "
            + ", ".join(missing)
        )

        return LivenessResult(
            False,
            reasons,
            metrics
        )

    # --------------------------------------------------------
    # Brightness
    # --------------------------------------------------------

    if metrics["brightness"] < 45:

        reasons.append(
            "Neutral baseline is too dark."
        )

    elif metrics["brightness"] > 220:

        reasons.append(
            "Neutral baseline is overexposed."
        )

    # --------------------------------------------------------
    # Sharpness
    # --------------------------------------------------------

    if metrics["sharpness"] < 35:

        reasons.append(
            "Neutral baseline is too blurry."
        )

    # --------------------------------------------------------
    # Face size
    # --------------------------------------------------------

    if metrics["face_area"] < 0.08:

        reasons.append(
            "Face is too small. Move closer."
        )

    elif metrics["face_area"] > 0.82:

        reasons.append(
            "Face is too large. Move slightly back."
        )

    # --------------------------------------------------------
    # EAR
    # --------------------------------------------------------

    if not (
        0.05 < metrics["ear"] < 0.8
    ):

        reasons.append(
            "Neutral eye measurement is unreliable. "
            "Look directly at the camera with both eyes open."
        )

    # --------------------------------------------------------
    # Nose position
    # --------------------------------------------------------

    if not (
        0.15 < metrics["nose_position"] < 0.85
    ):

        reasons.append(
            "Face position is unreliable. Center your face."
        )

    return LivenessResult(
        passed=not reasons,
        reasons=reasons,
        metrics=metrics
    )


# ============================================================
# SINGLE ACTIVE CHALLENGE
# ============================================================

def active_challenge_check(
    challenge: str,
    baseline: dict[str, float],
    current: dict[str, float]
) -> LivenessResult:

    """
    Verify a blink or horizontal head turn against
    the neutral baseline.
    """

    if challenge == "blink":

        if "ear" not in baseline or "ear" not in current:

            return LivenessResult(
                False,
                ["Eye measurements are unavailable."],
                {}
            )

        passed = (
            current["ear"]
            <
            baseline["ear"] * 0.78
        )

        reason = (
            "Blink was not detected. "
            "Close both eyes fully, then capture again."
        )

        metrics = {
            "baseline_ear": baseline["ear"],
            "challenge_ear": current["ear"],
        }

    elif challenge == "turn":

        if (
            "nose_position" not in baseline
            or
            "nose_position" not in current
        ):

            return LivenessResult(
                False,
                ["Head-position measurements are unavailable."],
                {}
            )

        movement = abs(
            current["nose_position"]
            -
            baseline["nose_position"]
        )

        passed = movement >= 0.055

        reason = (
            "Head turn was not detected. "
            "Turn your head clearly to either side."
        )

        metrics = {
            "head_turn": movement,
        }

    else:

        return LivenessResult(
            False,
            ["Unknown liveness challenge."],
            {}
        )

    return LivenessResult(
        passed,
        [] if passed else [reason],
        metrics
    )


# ============================================================
# SEQUENCE CHALLENGE
# ============================================================

def sequence_challenge_check(
    challenge: str,
    frames: list[np.ndarray]
) -> LivenessResult:

    """
    Analyze the consecutive webcam frames captured during
    the active liveness challenge.

    The first valid frame is treated as the neutral reference.
    Later frames are compared against it.

    Expected call from app.py:

        sequence_challenge_check(challenge, frames)
    """

    if not frames:

        return LivenessResult(
            False,
            ["No webcam frames were captured."],
            {}
        )

    # --------------------------------------------------------
    # Analyze frames
    # --------------------------------------------------------

    analyzed: list[LivenessResult] = []

    for frame in frames:

        if frame is None:
            continue

        result = passive_liveness_check(frame)

        if result.landmarks is not None:

            analyzed.append(result)

    if len(analyzed) < 2:

        return LivenessResult(
            False,
            [
                "Not enough valid face frames were captured. "
                "Keep your face visible and try again."
            ],
            {}
        )

    # --------------------------------------------------------
    # Establish baseline from early frames
    # --------------------------------------------------------

    baseline_candidates = [
        result.metrics
        for result in analyzed[:min(10, len(analyzed))]
        if result.passed
    ]

    if not baseline_candidates:

        return LivenessResult(
            False,
            ["Unable to establish a neutral face position."],
            {}
        )

    baseline = {
        key: float(
            np.median(
                [
                    metrics[key]
                    for metrics in baseline_candidates
                    if key in metrics
                ]
            )
        )
        for key in (
            "ear",
            "nose_position",
        )
    }

    # --------------------------------------------------------
    # Challenge analysis
    # --------------------------------------------------------

    if challenge == "blink":

        # Find the minimum EAR observed during the sequence.
        valid_ear_values = [
            result.metrics["ear"]
            for result in analyzed
            if "ear" in result.metrics
        ]

        if not valid_ear_values:

            return LivenessResult(
                False,
                ["Could not measure eye movement."],
                {}
            )

        minimum_ear = min(valid_ear_values)

        passed = (
            minimum_ear
            <
            baseline["ear"] * 0.78
        )

        metrics = {
            "baseline_ear": baseline["ear"],
            "minimum_ear": minimum_ear,
            "ear_drop": baseline["ear"] - minimum_ear,
        }

        if passed:

            return LivenessResult(
                True,
                [],
                metrics
            )

        return LivenessResult(
            False,
            [
                "Blink was not detected. "
                "Blink once naturally while the camera is running."
            ],
            metrics
        )

    # --------------------------------------------------------
    # Head turn
    # --------------------------------------------------------

    if challenge == "turn":

        valid_positions = [
            result.metrics["nose_position"]
            for result in analyzed
            if "nose_position" in result.metrics
        ]

        if not valid_positions:

            return LivenessResult(
                False,
                ["Could not measure head movement."],
                {}
            )

        maximum_movement = max(
            abs(
                position
                -
                baseline["nose_position"]
            )
            for position in valid_positions
        )

        passed = maximum_movement >= 0.055

        metrics = {
            "baseline_nose_position":
                baseline["nose_position"],
            "maximum_head_turn":
                maximum_movement,
        }

        if passed:

            return LivenessResult(
                True,
                [],
                metrics
            )

        return LivenessResult(
            False,
            [
                "Head turn was not detected. "
                "Turn your head clearly to either side."
            ],
            metrics
        )

    # --------------------------------------------------------
    # Unknown challenge
    # --------------------------------------------------------

    return LivenessResult(
        False,
        ["Unknown liveness challenge."],
        {}
    )