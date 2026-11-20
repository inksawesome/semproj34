"""
Cancelable biometric template (chaos-based key schedule).

The raw ArcFace embedding is never stored. At enrolment each user gets a
random 256-bit key. The key seeds a logistic map (x <- r·x·(1-x), r ≈ 3.99,
the chaotic regime whose bifurcation diagram is fractal). The chaotic
sequence drives:

  1. a permutation of the 512 embedding dimensions, and
  2. a 256x512 projection matrix, orthonormalised so cosine similarity is
     (approximately) preserved - Johnson-Lindenstrauss.

    template = normalise( W_key · e[perm_key] )        (512-D -> 256-D)

Properties (all demonstrated in the Model Lab page):
  * Non-invertible: 512 unknowns, 256 equations - infinitely many
    embeddings map to the same template.
  * Cancelable / revocable: if the database leaks, issue a new key; the old
    template is useless.
  * Unlinkable: the same face under two keys gives templates with cosine
    ≈ 0, so templates cannot be cross-matched between systems.
  * Matching happens entirely in the transformed domain.
"""

import functools
import hashlib
import hmac
import secrets

import numpy as np

EMBED_DIM = 512
TEMPLATE_DIM = 256
_BURN_IN = 500


def new_key() -> bytes:
    return secrets.token_bytes(32)


def _logistic_sequence(key: bytes, label: bytes, n: int) -> np.ndarray:
    """n samples of a key-seeded logistic map, returned centred in (-0.5, 0.5)."""
    h = hmac.new(key, label, hashlib.sha256).digest()
    x = 0.01 + 0.98 * (int.from_bytes(h[:8], "big") / 2 ** 64)       # x0 in (0.01, 0.99)
    r = 3.99 + 0.0099 * (int.from_bytes(h[8:10], "big") / 65535)    # r in [3.99, 3.9999]
    for _ in range(_BURN_IN):
        x = r * x * (1 - x)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        x = r * x * (1 - x)
        out[i] = x
    return out - 0.5


@functools.lru_cache(maxsize=64)
def _transform(key: bytes):
    perm = np.argsort(_logistic_sequence(key, b"perm", EMBED_DIM))
    raw = _logistic_sequence(key, b"proj", TEMPLATE_DIM * EMBED_DIM).reshape(EMBED_DIM, TEMPLATE_DIM)
    q, _ = np.linalg.qr(raw)              # orthonormal columns -> angle-preserving projection
    return perm, q.T.astype(np.float32)   # (256, 512)


def protect(embedding: np.ndarray, key: bytes) -> np.ndarray:
    perm, w = _transform(key)
    t = w @ embedding[perm]
    return (t / (np.linalg.norm(t) + 1e-9)).astype(np.float32)


def match(embedding: np.ndarray, template: np.ndarray, key: bytes) -> float:
    """Cosine similarity computed in the protected domain."""
    return float(np.dot(protect(embedding, key), template))
