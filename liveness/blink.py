import math

def _euclidean_distance(p1, p2):
    """Calculate Euclidean distance between two points (objects with x,y or tuples)."""
    if hasattr(p1, 'x') and hasattr(p2, 'x'):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def calculate_ear(eye_landmarks):
    """
    Computes Eye Aspect Ratio (EAR).
    eye_landmarks: A list of 6 landmarks for a single eye.
    Order: 
    0: Left/Right corner
    1: Top left
    2: Top right
    3: Right/Left corner
    4: Bottom right
    5: Bottom left
    """
    if len(eye_landmarks) < 6:
        return 0.0
    
    # Compute distances between vertical eye landmarks
    v1 = _euclidean_distance(eye_landmarks[1], eye_landmarks[5])
    v2 = _euclidean_distance(eye_landmarks[2], eye_landmarks[4])
    
    # Compute distance between horizontal eye landmarks
    h = _euclidean_distance(eye_landmarks[0], eye_landmarks[3])
    
    if h == 0:
        return 0.0
        
    ear = (v1 + v2) / (2.0 * h)
    return ear

def verify_blink(landmark_sequence, ear_threshold=0.2, consecutive_frames=2) -> tuple[bool, float]:
    """
    Verifies if a blink occurred in the given sequence of landmarks.
    landmark_sequence: A list of frames, where each frame contains (left_eye_landmarks, right_eye_landmarks).
    Returns (Passed, Confidence)
    """
    blink_detected = False
    blink_frame_count = 0
    min_ear = 1.0
    
    for frame_data in landmark_sequence:
        if len(frame_data) == 2:
            left_eye, right_eye = frame_data
            left_ear = calculate_ear(left_eye)
            right_ear = calculate_ear(right_eye)
            avg_ear = (left_ear + right_ear) / 2.0
            
            min_ear = min(min_ear, avg_ear)
            
            if avg_ear < ear_threshold:
                blink_frame_count += 1
            else:
                if blink_frame_count >= consecutive_frames:
                    blink_detected = True
                blink_frame_count = 0
                
    if blink_frame_count >= consecutive_frames:
        blink_detected = True
        
    confidence = 0.0
    if blink_detected:
        confidence = min(1.0, max(0.0, (ear_threshold - min_ear) / ear_threshold))
        
    return blink_detected, confidence
