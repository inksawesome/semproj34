import math

def _euclidean_distance(p1, p2):
    """Calculate Euclidean distance between two points."""
    if hasattr(p1, 'x') and hasattr(p2, 'x'):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def calculate_mar(mouth_landmarks):
    """
    Computes Mouth Aspect Ratio (MAR) or a smile ratio.
    Assuming mouth_landmarks has at least 6 points:
    0: Left corner
    1, 2: Top lip points
    3: Right corner
    4, 5: Bottom lip points
    """
    if len(mouth_landmarks) < 6:
        return 0.0
    
    # Compute distances between vertical mouth landmarks
    v1 = _euclidean_distance(mouth_landmarks[1], mouth_landmarks[5])
    v2 = _euclidean_distance(mouth_landmarks[2], mouth_landmarks[4])
    
    # Compute distance between horizontal mouth landmarks
    h = _euclidean_distance(mouth_landmarks[0], mouth_landmarks[3])
    
    avg_v = (v1 + v2) / 2.0
    
    # For a smile, we can check the ratio of width to height.
    # Or standard MAR is avg_v / h. 
    # Since smiles widen the mouth, we will return the ratio of width / height,
    # or just the width itself if we normalize it by face size elsewhere.
    # Let's return h / avg_v as a basic smile index (higher means wider smile).
    if avg_v == 0:
        return h
        
    return h / avg_v

def verify_smile(landmark_sequence, smile_threshold=2.5, consecutive_frames=3) -> tuple[bool, float]:
    """
    Verifies if a smile occurred based on the sequence of mouth landmarks.
    landmark_sequence: A list of frames, where each frame contains mouth_landmarks.
    Returns (Passed, Confidence) based on MAR/width expansion.
    """
    smile_detected = False
    smile_frame_count = 0
    max_ratio = 0.0
    
    for mouth_landmarks in landmark_sequence:
        ratio = calculate_mar(mouth_landmarks)
        max_ratio = max(max_ratio, ratio)
        
        if ratio > smile_threshold:
            smile_frame_count += 1
        else:
            if smile_frame_count >= consecutive_frames:
                smile_detected = True
            smile_frame_count = 0
            
    if smile_frame_count >= consecutive_frames:
        smile_detected = True
        
    confidence = 0.0
    if smile_detected:
        confidence = min(1.0, max(0.0, (max_ratio - smile_threshold) / smile_threshold))
        
    return smile_detected, confidence
