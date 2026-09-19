import numpy as np
import cv2

def estimate_head_pose(landmarks, image_shape):
    """
    Returns (Yaw, Pitch, Roll) using PnP.
    landmarks: list of (x,y) facial landmarks (e.g. nose, eyes, mouth).
    image_shape: (height, width) of the frame.
    """
    yaw, pitch, roll = 0.0, 0.0, 0.0
    
    if len(landmarks) == 0:
        return yaw, pitch, roll
        
    # Placeholder for actual PnP implementation.
    return yaw, pitch, roll

def verify_head_movement(landmark_sequence, challenge_type, image_shape) -> tuple[bool, float]:
    """
    Verifies if yaw/pitch changes match the challenge (TURN_LEFT, TURN_RIGHT, LOOK_UP).
    """
    if not landmark_sequence or len(landmark_sequence) < 2:
        return False, 0.0
        
    start_yaw, start_pitch, _ = estimate_head_pose(landmark_sequence[0], image_shape)
    end_yaw, end_pitch, _ = estimate_head_pose(landmark_sequence[-1], image_shape)
    
    yaw_diff = end_yaw - start_yaw
    pitch_diff = end_pitch - start_pitch
    
    threshold = 15.0 # Degrees
    
    if challenge_type == "TURN_LEFT" and yaw_diff < -threshold:
        return True, min(1.0, abs(yaw_diff)/45.0)
    elif challenge_type == "TURN_RIGHT" and yaw_diff > threshold:
        return True, min(1.0, abs(yaw_diff)/45.0)
    elif challenge_type == "LOOK_UP" and pitch_diff > threshold:
        return True, min(1.0, abs(pitch_diff)/45.0)
        
    return False, 0.0
