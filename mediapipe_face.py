import threading

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

_GLOBAL_LANDMARKER = None

# Serialises MediaPipe inference across threads (WebRTC worker + Streamlit script thread).
MP_LOCK = threading.RLock()

def get_landmarker():
    global _GLOBAL_LANDMARKER
    if _GLOBAL_LANDMARKER is None:
        base_options = BaseOptions(model_asset_path='face_landmarker.task')
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5)
        _GLOBAL_LANDMARKER = vision.FaceLandmarker.create_from_options(options)
    return _GLOBAL_LANDMARKER


# ============================================================
# MEDIAPIPE FACE MESH
# ============================================================

def detect_and_crop_face(image_rgb):
    """
    Detect a face and return:

        face_crop, bounding_box

    The returned face_crop is an RGB numpy array.
    """

    height, width, _ = image_rgb.shape

    with MP_LOCK:
        landmarker = get_landmarker()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(image_rgb))
        results = landmarker.detect(mp_image)

    if not results.face_landmarks:
        return None, None

    landmarks = results.face_landmarks[0]

    # --------------------------------------------------------
    # Get face bounding box from all landmarks
    # --------------------------------------------------------

    x_coords = [
        int(lm.x * width)
        for lm in landmarks
    ]

    y_coords = [
        int(lm.y * height)
        for lm in landmarks
    ]

    x = max(0, min(x_coords))
    y = max(0, min(y_coords))

    x2 = min(width, max(x_coords))
    y2 = min(height, max(y_coords))

    if x >= x2 or y >= y2:
        return None, None

    # Add some margin around the face
    margin_x = int((x2 - x) * 0.20)
    margin_y = int((y2 - y) * 0.20)

    x = max(0, x - margin_x)
    y = max(0, y - margin_y)

    x2 = min(width, x2 + margin_x)
    y2 = min(height, y2 + margin_y)

    face_crop = image_rgb[y:y2, x:x2]

    return face_crop, (x, y, x2 - x, y2 - y)


# ============================================================
# WEBCAM IMAGE PROCESSING
# ============================================================

def capture_and_detect(camera_image):
    """
    Convert a Streamlit camera image to RGB and
    detect/crop the face.
    """

    image_bytes = camera_image.getvalue()

    image_array = np.frombuffer(
        image_bytes,
        np.uint8,
    )

    image_bgr = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR,
    )

    if image_bgr is None:
        return None

    image_rgb = cv2.cvtColor(
        image_bgr,
        cv2.COLOR_BGR2RGB,
    )

    face_crop, _ = detect_and_crop_face(image_rgb)

    return face_crop