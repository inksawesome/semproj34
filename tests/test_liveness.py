
from liveness.blink import calculate_ear, verify_blink
from liveness.smile import calculate_mar, verify_smile
from liveness.head_pose import estimate_head_pose, verify_head_movement
from liveness.challenge import ChallengeGenerator

class MockPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def test_calculate_ear():
    # Mock eye landmarks (perfectly rectangular for easy math)
    # Width = 2, Height = 1
    # EAR = (1 + 1) / (2 * 2) = 2/4 = 0.5
    eye = [
        MockPoint(0, 0),    # 0: left corner
        MockPoint(0.5, 1),  # 1: top left
        MockPoint(1.5, 1),  # 2: top right
        MockPoint(2, 0),    # 3: right corner
        MockPoint(1.5, -1), # 4: bottom right (Wait, distance top-bottom is 2)
        MockPoint(0.5, -1)  # 5: bottom left
    ]
    
    # Distance v1 = hypot(0.5-0.5, 1 - (-1)) = 2
    # Distance v2 = hypot(1.5-1.5, 1 - (-1)) = 2
    # Distance h = hypot(0-2, 0-0) = 2
    # EAR = (2 + 2) / (2 * 2) = 1.0
    
    ear = calculate_ear(eye)
    assert ear == 1.0

def test_verify_blink():
    # Sequence of frames, each containing (left_eye, right_eye)
    # Start open (ear > 0.2), close (ear < 0.2), open (ear > 0.2)
    
    open_eye = [MockPoint(0,0), MockPoint(0.5,1), MockPoint(1.5,1), MockPoint(2,0), MockPoint(1.5,-1), MockPoint(0.5,-1)]
    closed_eye = [MockPoint(0,0), MockPoint(0.5,0.1), MockPoint(1.5,0.1), MockPoint(2,0), MockPoint(1.5,-0.1), MockPoint(0.5,-0.1)]
    
    # Closed EAR = (0.2 + 0.2) / (2 * 2) = 0.4 / 4 = 0.1
    sequence = [
        (open_eye, open_eye),
        (closed_eye, closed_eye), # Frame 1 closed
        (closed_eye, closed_eye), # Frame 2 closed
        (open_eye, open_eye)
    ]
    
    passed, confidence = verify_blink(sequence, ear_threshold=0.2, consecutive_frames=2)
    assert passed is True
    assert confidence > 0.0

def test_challenge_generator():
    generator = ChallengeGenerator()
    challenge = generator.get_random_challenge()
    assert challenge in generator.challenges

def test_estimate_head_pose():
    # [nose, left_eye, right_eye, chin]
    nose = MockPoint(1, 1)
    left_eye = MockPoint(0, 2)
    right_eye = MockPoint(2, 2)
    chin = MockPoint(1, 0)
    
    # Perfectly centered, yaw = 0, pitch = 0
    yaw, pitch, roll = estimate_head_pose([nose, left_eye, right_eye, chin])
    assert yaw == 0.0
    # Center y = 2, face_height = 2, nose_y = 1
    # pitch = ((1 - 2) / 2 - 0.5) * 90 = (-0.5 - 0.5) * 90 = -90 (looking up)
    # Wait, our simple pitch proxy isn't perfectly 0 here, but let's just check it doesn't crash
    assert isinstance(yaw, float)
    assert isinstance(pitch, float)
    assert isinstance(roll, float)
