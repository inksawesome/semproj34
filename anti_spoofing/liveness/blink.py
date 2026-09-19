import numpy as np

def calculate_ear(eye_landmarks):
    """
    Computes Eye Aspect Ratio (EAR) using standard formulas.
    eye_landmarks: List of coordinates [(x,y), ...] for a single eye.
    """
    if len(eye_landmarks) < 6:
        return 0.0
    
    A = np.linalg.norm(np.array(eye_landmarks[1]) - np.array(eye_landmarks[5]))
    B = np.linalg.norm(np.array(eye_landmarks[2]) - np.array(eye_landmarks[4]))
    C = np.linalg.norm(np.array(eye_landmarks[0]) - np.array(eye_landmarks[3]))
    
    if C == 0:
        return 0.0
        
    ear = (A + B) / (2.0 * C)
    return ear

def verify_blink(landmark_sequence, ear_threshold=0.2, min_frames=2) -> tuple[bool, float]:
    """
    Returns (Passed, Confidence) based on EAR drop and recovery.
    landmark_sequence: list of (left_eye_landmarks, right_eye_landmarks) per frame
    """
    blink_detected = False
    frames_below_threshold = 0
    confidence = 0.0

    for left_eye, right_eye in landmark_sequence:
        left_ear = calculate_ear(left_eye)
        right_ear = calculate_ear(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0

        if avg_ear < ear_threshold:
            frames_below_threshold += 1
        else:
            if frames_below_threshold >= min_frames:
                blink_detected = True
                confidence = min(1.0, 0.5 + (frames_below_threshold * 0.1))
                break
            frames_below_threshold = 0

    return blink_detected, confidence
