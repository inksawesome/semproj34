"""
walk_otp.py — Random-Walk OTP Core Module (v2)
===============================================
Implements a TOTP-style OTP system where the HMAC-SHA1 core of RFC 6238
is replaced by a **random walk on a graph**.

Algorithm overview
------------------
1.  Compute time counter  T = floor(unix_time / time_step)
2.  Derive a walk seed:   seed = HMAC-SHA256(K, T_be8 || SHA256(context))
        `context` binds the code to what is being authorised, e.g.
        "TX|<id>|<amount_cents>|<payee>" for a bank transfer ("dynamic
        linking"). An empty context gives a plain login OTP.
3.  Expand the seed into a byte stream  SHA256(seed || i_be4), i = 0, 1, ...
4.  Walk S steps on graph G: start node and every edge choice are drawn
    from the stream with rejection sampling (no modulo bias).
5.  Encode the path as bytes (each node ID as a 2-byte big-endian uint).
6.  Derive OTP: SHA256 over the *whole* encoded path, then RFC 4226
    dynamic truncation → int → mod 10^digits → zero-pad.

Why v2
------
v1 seeded Python's Mersenne Twister (`random.Random`) and truncated the raw
path bytes. Two problems:
  * a 4-byte truncation window only covered two node IDs (< 64 each), so
    the scheme could only ever emit ~8k distinct codes (we measured 768
    distinct codes over 20,000 random secrets) instead of 10^6;
  * Mersenne Twister cannot be reproduced cheaply outside CPython, so the
    JavaScript client produced different graphs and codes.
v2 uses only SHA-256 / HMAC-SHA256, which every platform has, and hashes
the full path so every step contributes to the code. Test vectors in
`tests/walk_otp_vectors.json` pin Python and JS to identical output.

Seed-swap point
---------------
The only secret input is the raw secret bytes `K`. To swap in a
fractal-derived seed later, pass those bytes as `K`; nothing else changes.

Graph
-----
A fixed, shared Watts–Strogatz-style graph is generated once from a public
seed. Both server and client build the same adjacency list. The graph is
NOT secret; the secrecy lives entirely in K.
"""

from __future__ import annotations

import hashlib
import hmac
import struct
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Default configuration — override by passing a GraphConfig / OTPConfig
# ---------------------------------------------------------------------------

DEFAULT_NUM_NODES: int = 64        # N — graph vertices
DEFAULT_DEGREE: int = 6            # k — base lattice degree
DEFAULT_WALK_STEPS: int = 16       # S — steps per OTP generation
DEFAULT_TIME_STEP: int = 30        # seconds, same as TOTP
DEFAULT_DIGITS: int = 6            # OTP length
DEFAULT_GRAPH_SEED: int = 0xDEADBEEF  # deterministic graph-gen seed (public)

ALGORITHM_VERSION: str = "walk-otp-v2"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GraphConfig:
    """
    Describes the shared graph.  Not secret — can be hard-coded or loaded
    from a config file on both server and client.
    """
    num_nodes: int = DEFAULT_NUM_NODES
    degree: int = DEFAULT_DEGREE
    graph_seed: int = DEFAULT_GRAPH_SEED
    # Adjacency list is built lazily / explicitly; stored as list-of-lists.
    _adjacency: Optional[List[List[int]]] = field(default=None, repr=False)

    def adjacency(self) -> List[List[int]]:
        """Return (or lazily build) the adjacency list."""
        if self._adjacency is None:
            self._adjacency = _build_graph(
                self.num_nodes, self.degree, self.graph_seed
            )
        return self._adjacency

    def to_dict(self) -> dict:
        return {
            "num_nodes": self.num_nodes,
            "degree": self.degree,
            "graph_seed": self.graph_seed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GraphConfig":
        return cls(
            num_nodes=d["num_nodes"],
            degree=d["degree"],
            graph_seed=d["graph_seed"],
        )


@dataclass
class OTPConfig:
    """Runtime configuration for the OTP scheme."""
    time_step: int = DEFAULT_TIME_STEP
    walk_steps: int = DEFAULT_WALK_STEPS
    digits: int = DEFAULT_DIGITS
    graph: GraphConfig = field(default_factory=GraphConfig)


# ---------------------------------------------------------------------------
# Deterministic byte stream (SHA-256 in counter mode)
# ---------------------------------------------------------------------------

class _ByteStream:
    """
    Expands a 32-byte key into an unbounded deterministic byte stream:
    SHA256(key || 0) || SHA256(key || 1) || ...
    Identical construction in walk_otp.js.
    """

    def __init__(self, key: bytes):
        self._key = key
        self._block = 0
        self._buf = b""

    def take(self, n: int) -> bytes:
        while len(self._buf) < n:
            self._buf += hashlib.sha256(
                self._key + struct.pack(">I", self._block)
            ).digest()
            self._block += 1
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def uint32(self) -> int:
        return struct.unpack(">I", self.take(4))[0]

    def below(self, n: int) -> int:
        """Uniform integer in [0, n) via rejection sampling (no modulo bias)."""
        limit = (1 << 32) - ((1 << 32) % n)
        while True:
            x = self.uint32()
            if x < limit:
                return x % n


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_graph(
    num_nodes: int, degree: int, seed: int
) -> List[List[int]]:
    """
    Build a deterministic small-world graph from a public seed.

    Strategy: circular lattice (each node i is connected to
    i±1, i±2, … i±(degree//2) mod N), then each edge is rewired with
    p = 0.3 to a random non-neighbour (Watts–Strogatz short-cuts).
    All randomness comes from a SHA-256 stream so any platform
    reproduces exactly the same graph.
    """
    rng = _ByteStream(
        hashlib.sha256(b"walk-otp-graph|" + struct.pack(">Q", seed)).digest()
    )
    half = degree // 2
    adj: List[set] = [set() for _ in range(num_nodes)]

    # Base: circular lattice
    for i in range(num_nodes):
        for d in range(1, half + 1):
            j = (i + d) % num_nodes
            adj[i].add(j)
            adj[j].add(i)

    # Rewire with p = 0.3 (300 / 1000) for small-world properties
    for i in range(num_nodes):
        for nb in sorted(adj[i]):
            if nb not in adj[i]:
                continue  # already rewired away earlier in this loop
            if rng.below(1000) < 300:
                candidates = [
                    v for v in range(num_nodes)
                    if v != i and v not in adj[i]
                ]
                if candidates and len(adj[nb]) > 1:
                    new_nb = candidates[rng.below(len(candidates))]
                    adj[i].discard(nb)
                    adj[nb].discard(i)
                    adj[i].add(new_nb)
                    adj[new_nb].add(i)

    return [sorted(s) for s in adj]


# ---------------------------------------------------------------------------
# Core OTP generation
# ---------------------------------------------------------------------------

def _current_time_step(time_step: int) -> int:
    """Return floor(unix_time / time_step)."""
    return int(time.time()) // time_step


def _derive_walk_seed(secret_k: bytes, counter: int, context: str = "") -> bytes:
    """
    HMAC-SHA256(K, counter_be8 || SHA256(context)).
    Returns 32 bytes that deterministically seed the walk.

    ── SEED-SWAP POINT ──────────────────────────────────────────────────────
    In the fractal-integrated version, `secret_k` can be replaced by bytes
    derived from the fractal/chaotic key schedule. The interface
    (bytes in → bytes out) is identical; nothing else changes.
    ─────────────────────────────────────────────────────────────────────────
    """
    counter_bytes = struct.pack(">Q", counter)  # 8-byte big-endian uint64
    context_hash = hashlib.sha256(context.encode("utf-8")).digest()
    return hmac.new(secret_k, counter_bytes + context_hash, hashlib.sha256).digest()


def _perform_walk(
    seed_bytes: bytes,
    adjacency: List[List[int]],
    num_nodes: int,
    walk_steps: int,
) -> List[int]:
    """
    Execute a deterministic random walk on the graph.

    Start node and each step are drawn from the SHA-256 stream of the seed.
    Returns the sequence of visited nodes (length = walk_steps + 1).
    """
    stream = _ByteStream(seed_bytes)
    current_node = stream.below(num_nodes)

    path: List[int] = [current_node]
    for _ in range(walk_steps):
        neighbours = adjacency[current_node]
        if not neighbours:
            break  # isolated node (cannot happen with our graph builder)
        current_node = neighbours[stream.below(len(neighbours))]
        path.append(current_node)

    return path


def _encode_path(path: List[int]) -> bytes:
    """
    Encode a list of node IDs as a big-endian 2-byte sequence.
    Max 65535 nodes — more than enough.
    """
    return b"".join(struct.pack(">H", node) for node in path)


def _truncate_to_otp(encoded: bytes, digits: int) -> str:
    """
    Compress the *whole* path with SHA-256, then RFC 4226 dynamic truncation:
    - offset = last_byte & 0x0F
    - extract 4 bytes at offset, mask MSB → int
    - mod 10^digits, zero-pad
    """
    digest = hashlib.sha256(ALGORITHM_VERSION.encode() + b"|" + encoded).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset: offset + 4])[0] & 0x7FFFFFFF
    return str(code_int % (10 ** digits)).zfill(digits)


def generate_otp_with_path(
    secret_k: bytes,
    counter: Optional[int] = None,
    config: Optional[OTPConfig] = None,
    context: str = "",
) -> Tuple[str, int, List[int]]:
    """Like generate_otp, but also returns the walk path (for visualisation)."""
    if config is None:
        config = OTPConfig()
    if counter is None:
        counter = _current_time_step(config.time_step)

    seed_bytes = _derive_walk_seed(secret_k, counter, context)
    adjacency = config.graph.adjacency()
    path = _perform_walk(
        seed_bytes, adjacency, config.graph.num_nodes, config.walk_steps
    )
    otp = _truncate_to_otp(_encode_path(path), config.digits)
    return otp, counter, path


def generate_otp(
    secret_k: bytes,
    counter: Optional[int] = None,
    config: Optional[OTPConfig] = None,
    context: str = "",
) -> Tuple[str, int]:
    """
    Public API — generate an OTP.

    Parameters
    ----------
    secret_k : bytes
        The shared secret (min 16 bytes / 128-bit recommended).
    counter  : int, optional
        Time-step counter T.  Defaults to the current time-step.
    config   : OTPConfig, optional
        Algorithm configuration.  Defaults to OTPConfig().
    context  : str, optional
        What the code authorises (e.g. a transaction). Empty for login.

    Returns
    -------
    (otp_string, counter_used)
    """
    otp, counter, _ = generate_otp_with_path(secret_k, counter, config, context)
    return otp, counter


def verify_otp(
    secret_k: bytes,
    submitted_otp: str,
    config: Optional[OTPConfig] = None,
    window: int = 1,
    context: str = "",
    grace_seconds: Optional[float] = None,
    now: Optional[float] = None,
) -> Tuple[bool, int]:
    """
    Verify a submitted OTP against T-window … T+window.

    grace_seconds (optional) narrows the window to what a user actually
    experiences: a code from an earlier step is accepted only if it expired
    less than `grace_seconds` ago, and a code from a later step only if it
    becomes current within `grace_seconds` (phone clock slightly ahead).
    Without it, any code in the ±window steps is accepted (RFC 6238 style),
    which keeps an expired code usable for up to a full extra step.

    Returns (is_valid, matched_counter).
    matched_counter is -1 if invalid.
    """
    if config is None:
        config = OTPConfig()
    now = time.time() if now is None else now
    step = config.time_step
    t_now = int(now) // step
    into_step = now - t_now * step                   # seconds since the current code became valid
    for delta in range(-window, window + 1):
        if grace_seconds is not None:
            if delta < 0 and into_step + (-delta - 1) * step >= grace_seconds:
                continue                             # expired longer ago than the grace period
            if delta > 0 and (step - into_step) + (delta - 1) * step >= grace_seconds:
                continue                             # not valid yet, beyond tolerated clock skew
        t_check = t_now + delta
        expected, _ = generate_otp(secret_k, counter=t_check, config=config, context=context)
        if hmac.compare_digest(expected, submitted_otp.strip()):
            return True, t_check
    return False, -1


def otp_age(
    secret_k: bytes,
    submitted_otp: str,
    config: Optional[OTPConfig] = None,
    context: str = "",
    lookback: int = 10,
    now: Optional[float] = None,
) -> Optional[int]:
    """How many steps old a submitted code is (0 = current), or None if it was never valid
    in the last `lookback` steps. Used to tell an expired code apart from a wrong one."""
    if config is None:
        config = OTPConfig()
    now = time.time() if now is None else now
    t_now = int(now) // config.time_step
    for age in range(lookback + 1):
        expected, _ = generate_otp(secret_k, counter=t_now - age, config=config, context=context)
        if hmac.compare_digest(expected, submitted_otp.strip()):
            return age
    return None


def transaction_context(tx_id: str, amount: float, payee: str) -> str:
    """Canonical context string for a transfer (shared with the JS client)."""
    cents = int(round(amount * 100))
    return f"TX|{tx_id}|{cents}|{payee.strip().lower()}"


# ---------------------------------------------------------------------------
# Secret generation (server-side only; separate from client path)
# ---------------------------------------------------------------------------

def generate_secret(num_bytes: int = 32) -> bytes:
    """
    Generate a cryptographically random secret K.
    Uses secrets.token_bytes — OS CSPRNG backed.

    num_bytes >= 16 (128-bit) required; default is 32 (256-bit).
    """
    import secrets as _secrets
    if num_bytes < 16:
        raise ValueError("Secret must be at least 16 bytes (128-bit entropy).")
    return _secrets.token_bytes(num_bytes)


def secret_to_b32(secret_k: bytes) -> str:
    """Encode secret as Base32 for QR/display."""
    import base64
    return base64.b32encode(secret_k).decode()


def b32_to_secret(b32_str: str) -> bytes:
    """Decode a Base32 string back to raw secret bytes."""
    import base64
    return base64.b32decode(b32_str.upper())
