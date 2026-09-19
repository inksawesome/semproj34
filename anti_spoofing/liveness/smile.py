import numpy as np

def calculate_mar(mouth_landmarks):
    """
    Computes Mouth Aspect Ratio (MAR).
    mouth_landmarks: list of (x,y) coordinates for mouth.
    """
    if len(mouth_landmarks) < 8:
        return 0.0
    A = np.linalg.norm(np.array(mouth_landmarks[2]) - np.array(mouth_landmarks[6]))
    B = np.linalg.norm(np.array(mouth_landmarks[3]) - np.array(mouth_landmarks[5]))
    C = np.linalg.norm(np.array(mouth_landmarks[0]) - np.array(mouth_landmarks[4]))
    
    if C == 0:
        return 0.0
        
    mar = (A + B) / (2.0 * C)
    return mar

def verify_smile(landmark_sequence, mar_threshold=0.5) -> tuple[bool, float]:
    """
    Returns (Passed, Confidence) based on MAR expansion.
    """
    max_mar = 0.0
    for mouth in landmark_sequence:
        mar = calculate_mar(mouth)
        if mar > max_mar:
            max_mar = mar
            
    if max_mar > mar_threshold:
        return True, min(1.0, max_mar / (mar_threshold * 1.5))
        
    return False, 0.0
