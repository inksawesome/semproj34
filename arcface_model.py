import cv2
import numpy as np
from insightface.app import FaceAnalysis


# ============================================================
# INSIGHTFACE / ARCFACE
# ============================================================

print("Loading InsightFace ArcFace model...")

face_app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"],
)

face_app.prepare(
    ctx_id=-1,
    det_size=(640, 640),
)

print("InsightFace ArcFace model loaded.")


# Get the ArcFace recognition model directly
recognition_model = face_app.models["recognition"]


# ============================================================
# GENERATE EMBEDDING
# ============================================================

def get_embedding(face_crop):

    if face_crop is None:
        return None

    # --------------------------------------------------------
    # MediaPipe gives RGB
    # ArcFace expects BGR
    # --------------------------------------------------------

    image_bgr = cv2.cvtColor(
        face_crop,
        cv2.COLOR_RGB2BGR
    )

    # --------------------------------------------------------
    # Resize face crop to ArcFace input size
    # --------------------------------------------------------

    face_112 = cv2.resize(
        image_bgr,
        (112, 112)
    )

    # --------------------------------------------------------
    # Generate embedding DIRECTLY
    #
    # Do NOT use face_app.get()
    # because that runs face detection again.
    # --------------------------------------------------------

    embedding = recognition_model.get_feat(
        face_112
    )

    if embedding is None:
        print("ArcFace returned no embedding.")
        return None

    embedding = np.asarray(
        embedding,
        dtype=np.float32
    )

    # get_feat may return shape (1, 512)
    embedding = embedding.flatten()

    print("Embedding shape:", embedding.shape)

    if embedding.shape != (512,):
        raise ValueError(
            f"Expected 512-dimensional embedding, "
            f"got {embedding.shape}"
        )

    return embedding


# ============================================================
# VALIDATION
# ============================================================

def generate_embedding(face_crop):

    embedding = get_embedding(face_crop)

    if embedding is None:
        return None

    return embedding