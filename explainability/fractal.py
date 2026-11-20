"""
Fractal dimension of facial texture - Differential Box Counting
(Sarkar & Chaudhuri, 1994).

A grey-level image is treated as a 3-D surface (x, y, intensity). Its
fractal dimension FD in [2, 3] measures how "rough" that surface is across
scales. Live skin has fine multi-scale texture (pores, hair, shading);
re-captured faces lose it to print dots, screen pixel grids, blur and
compression, which shifts FD. FD is reported as an interpretable texture
signal next to the CNN score.
"""

import cv2
import numpy as np

_SIZE = 128
_BOX_SIZES = (2, 4, 8, 16, 32)


def _center_gray(face_rgb: np.ndarray) -> np.ndarray:
    h, w = face_rgb.shape[:2]
    # inner 70%: skip hair / background / clothing at the crop border
    y0, y1, x0, x1 = int(h * .15), int(h * .85), int(w * .15), int(w * .85)
    gray = cv2.cvtColor(face_rgb[y0:y1, x0:x1], cv2.COLOR_RGB2GRAY)
    return cv2.resize(gray, (_SIZE, _SIZE), interpolation=cv2.INTER_AREA).astype(np.float64)


def fractal_dimension(face_rgb: np.ndarray) -> float:
    img = _center_gray(face_rgb)
    M, G = _SIZE, 256.0
    log_inv_r, log_n = [], []
    for s in _BOX_SIZES:
        h = s * G / M                                   # box height in grey levels
        blocks = img.reshape(M // s, s, M // s, s).swapaxes(1, 2)
        mx = blocks.max(axis=(2, 3))
        mn = blocks.min(axis=(2, 3))
        n_r = (np.ceil((mx + 1) / h) - np.ceil((mn + 1) / h) + 1).sum()
        log_inv_r.append(np.log(M / s))
        log_n.append(np.log(n_r))
    slope, _ = np.polyfit(log_inv_r, log_n, 1)
    return float(slope)
