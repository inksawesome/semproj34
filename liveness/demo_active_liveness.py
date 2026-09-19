import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions
import time
from liveness.challenge import ChallengeGenerator
from liveness.blink import verify_blink
from liveness.smile import verify_smile
from liveness.head_pose import verify_head_movement, verify_neutral

def main():
    generator = ChallengeGenerator()
    challenge = generator.get_random_challenge()
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
        
    landmark_buffer = []
    max_buffer_size = 30
    passed = False
    confidence = 0.0
    
    # New Two-Phase State Machine
    state = "ALIGNING"
    alignment_frames = 0
    REQUIRED_ALIGNMENT_FRAMES = 20
    
    base_options = BaseOptions(model_asset_path='face_landmarker.task')
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5)
        
    with vision.FaceLandmarker.create_from_options(options) as landmarker:
        start_time = time.time()
        timeout = 10.0
        
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                continue

            image = cv2.flip(image, 1)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            result = landmarker.detect(mp_image)
            
            if result.face_landmarks:
                for face_landmarks in result.face_landmarks:
                    if state == "ALIGNING":
                        # Require the user to look straight ahead for several frames
                        pose_points = [face_landmarks[1], face_landmarks[33], face_landmarks[263], face_landmarks[152]]
                        if verify_neutral(pose_points):
                            alignment_frames += 1
                        else:
                            alignment_frames = 0
                            
                        if alignment_frames >= REQUIRED_ALIGNMENT_FRAMES:
                            state = "TESTING"
                            start_time = time.time() # Start the 10s timeout ONLY after alignment
                            print(f"User aligned. Current Challenge: {challenge}")
                            
                    elif state == "TESTING" and not passed:
                        if challenge == "BLINK":
                            left_eye = [face_landmarks[33], face_landmarks[160], face_landmarks[158], face_landmarks[133], face_landmarks[153], face_landmarks[144]]
                            right_eye = [face_landmarks[362], face_landmarks[385], face_landmarks[387], face_landmarks[263], face_landmarks[373], face_landmarks[380]]
                            landmark_buffer.append((left_eye, right_eye))
                            passed, confidence = verify_blink(landmark_buffer, ear_threshold=0.2, consecutive_frames=2)
                            
                        elif challenge == "SMILE":
                            mouth = [face_landmarks[61], face_landmarks[37], face_landmarks[267], face_landmarks[291], face_landmarks[314], face_landmarks[84]]
                            landmark_buffer.append(mouth)
                            passed, confidence = verify_smile(landmark_buffer, smile_threshold=2.5, consecutive_frames=5)
                            
                        elif challenge in ["TURN_LEFT", "TURN_RIGHT", "LOOK_UP", "LOOK_DOWN"]:
                            pose_points = [face_landmarks[1], face_landmarks[33], face_landmarks[263], face_landmarks[152]]
                            landmark_buffer.append(pose_points)
                            passed, confidence = verify_head_movement(landmark_buffer, challenge)
                            
                        if len(landmark_buffer) > max_buffer_size:
                            landmark_buffer.pop(0)
            
            # Rendering UX based on state
            if state == "ALIGNING":
                cv2.putText(image, "Step 1: Look Straight", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                progress = int((alignment_frames / REQUIRED_ALIGNMENT_FRAMES) * 100)
                cv2.putText(image, f"Aligning: {progress}%", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            elif state == "TESTING" or state == "FAILED":
                elapsed = time.time() - start_time
                if state == "TESTING" and elapsed > timeout and not passed:
                    state = "FAILED"
                    
                cv2.putText(image, f"Step 2: {challenge}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                
                if passed:
                    cv2.putText(image, f"PASSED! Conf: {confidence:.2f}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                elif state == "FAILED":
                    cv2.putText(image, "FAILED (Timeout)", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    cv2.putText(image, f"Time left: {max(0, timeout - elapsed):.1f}s", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            cv2.imshow('Active Liveness Demo', image)
            
            if cv2.waitKey(5) & 0xFF == ord('q'):
                break
                
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
