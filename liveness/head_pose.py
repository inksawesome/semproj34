import math

def estimate_head_pose(landmarks) -> tuple[float, float, float]:
    """
    Estimates head pose (Yaw, Pitch, Roll).
    In a full implementation, this would use cv2.solvePnP with a 3D face model.
    For Phase 3.1, this is a proxy implementation based on 2D coordinates.
    Expects landmarks to contain at least (nose_tip, left_eye, right_eye, chin).
    """
    if len(landmarks) < 4:
        return 0.0, 0.0, 0.0
        
    # Proxy mapping:
    # 0: nose tip
    # 1: left eye center/corner
    # 2: right eye center/corner
    # 3: chin
    nose = landmarks[0]
    left_eye = landmarks[1]
    right_eye = landmarks[2]
    chin = landmarks[3]
    
    def get_x(p): return p.x if hasattr(p, 'x') else p[0]
    def get_y(p): return p.y if hasattr(p, 'y') else p[1]
    
    # Yaw proxy: horizontal offset of nose relative to eye center
    eye_center_x = (get_x(left_eye) + get_x(right_eye)) / 2.0
    eye_dist = abs(get_x(right_eye) - get_x(left_eye))
    
    if eye_dist > 0:
        yaw = ((get_x(nose) - eye_center_x) / eye_dist) * 90.0
    else:
        yaw = 0.0
        
    # Pitch proxy: vertical offset of nose relative to eye center and chin
    eye_center_y = (get_y(left_eye) + get_y(right_eye)) / 2.0
    face_height = abs(get_y(chin) - eye_center_y)
    
    if face_height > 0:
        # A rough heuristic for pitch
        pitch = ((get_y(nose) - eye_center_y) / face_height - 0.5) * 90.0
    else:
        pitch = 0.0
        
    # Roll proxy: angle of the line connecting the eyes
    dx = get_x(right_eye) - get_x(left_eye)
    dy = get_y(right_eye) - get_y(left_eye)
    roll = math.degrees(math.atan2(dy, dx)) if dx != 0 else 0.0
    
    return yaw, pitch, roll

def verify_head_movement(landmark_sequence, challenge_type) -> tuple[bool, float]:
    """
    Verifies if yaw/pitch changes match the challenge.
    challenge_type: "TURN_LEFT", "TURN_RIGHT", "LOOK_UP", "LOOK_DOWN"
    """
    passed = False
    confidence = 0.0
    
    max_yaw, min_yaw = 0.0, 0.0
    max_pitch, min_pitch = 0.0, 0.0
    
    for landmarks in landmark_sequence:
        yaw, pitch, roll = estimate_head_pose(landmarks)
        max_yaw = max(max_yaw, yaw)
        min_yaw = min(min_yaw, yaw)
        max_pitch = max(max_pitch, pitch)
        min_pitch = min(min_pitch, pitch)
        
    yaw_threshold = 15.0
    pitch_threshold = 15.0
    
    if challenge_type == "TURN_LEFT":
        # Nose moves left -> negative yaw in mirrored camera
        if min_yaw < -yaw_threshold:
            passed = True
            confidence = min(1.0, abs(min_yaw) / 45.0)
    elif challenge_type == "TURN_RIGHT":
        # Nose moves right -> positive yaw in mirrored camera
        if max_yaw > yaw_threshold:
            passed = True
            confidence = min(1.0, max_yaw / 45.0)
    elif challenge_type == "LOOK_UP":
        # Nose moves up closer to eyes -> pitch decreases in image coords (y goes down)
        if min_pitch < -pitch_threshold:
            passed = True
            confidence = min(1.0, abs(min_pitch) / 45.0)
    elif challenge_type == "LOOK_DOWN":
        if max_pitch > pitch_threshold:
            passed = True
            confidence = min(1.0, max_pitch / 45.0)
            
    return passed, confidence

def verify_neutral(landmarks, yaw_threshold=10.0, pitch_threshold=10.0) -> bool:
    """
    Verifies if the face is looking straight ahead (neutral position).
    """
    yaw, pitch, roll = estimate_head_pose(landmarks)
    return abs(yaw) < yaw_threshold and abs(pitch) < pitch_threshold
