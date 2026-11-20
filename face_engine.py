"""
Face recognition: InsightFace buffalo_l (RetinaFace detector + ArcFace R50).

Unlike the old arcface_model.get_embedding (which resized an unaligned
MediaPipe crop to 112x112), this runs RetinaFace and the 5-point similarity
alignment ArcFace was trained with, so genuine/impostor scores separate
cleanly.
"""

import threading

import cv2
import numpy as np

# Cosine similarity on aligned ArcFace embeddings. Genuine pairs typically
# score 0.5-0.8 on a webcam, different people stay below ~0.25.
MATCH_THRESHOLD = 0.40

_app = None
_lock = threading.Lock()


def _face_app():
    global _app
    with _lock:
        if _app is None:
            from insightface.app import FaceAnalysis
            app = FaceAnalysis(
                name="buffalo_l",
                providers=["CPUExecutionProvider"],
                allowed_modules=["detection", "recognition"],
            )
            app.prepare(ctx_id=-1, det_size=(320, 320))
            _app = app
    return _app


def embed(image_rgb: np.ndarray):
    """
    Returns (embedding[512] L2-normalised, bbox) for the largest face,
    or (None, None) if no face is found.
    """
    if image_rgb is None or image_rgb.size == 0:
        return None, None
    faces = _face_app().get(cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))
    if not faces:
        return None, None
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return face.normed_embedding.astype(np.float32), face.bbox.astype(int)


def embed_best(frames):
    """Average the embeddings of several frames (more stable than one)."""
    embs = [e for e, _ in (embed(f) for f in frames) if e is not None]
    if not embs:
        return None
    mean = np.mean(embs, axis=0)
    return (mean / np.linalg.norm(mean)).astype(np.float32)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
