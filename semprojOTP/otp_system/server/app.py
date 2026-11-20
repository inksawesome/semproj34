"""
server/app.py — FastAPI server exposing /enroll and /verify
============================================================
Endpoints
---------
POST /enroll          — generate K, return it as Base32 + QR payload
POST /verify          — validate a submitted OTP, prevent replay
GET  /health          — liveness check
DELETE /devices/{id}  — de-enroll a device (admin use)

Security notes
--------------
- Rate limiting via a simple in-process leaky-bucket (replace with
  Redis/nginx rate-limit in production).
- Verification failures are logged (stubbed hook `_log_failure`).
- K is NEVER returned after enroll, and NEVER appears in logs.
- All endpoints should be behind TLS in production (use a reverse proxy).
"""

from __future__ import annotations

import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, Optional

# Allow importing from the parent otp_system package
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from walk_otp import (
    GraphConfig,
    OTPConfig,
    b32_to_secret,
    generate_otp,
    generate_secret,
    secret_to_b32,
    verify_otp,
)
from server.storage import DeviceStore

# ---------------------------------------------------------------------------
# App & global state
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Random-Walk OTP Server",
    description=(
        "TOTP-style OTP system using a random walk on a graph "
        "instead of HMAC-SHA1.  Designed for the SemProj face-recognition "
        "2FA module."
    ),
    version="1.0.0",
)

_store = DeviceStore()

# Shared graph config (same on server and client — not secret)
_GRAPH_CFG = GraphConfig()
_OTP_CFG = OTPConfig(graph=_GRAPH_CFG)

# ---------------------------------------------------------------------------
# Rate limiting (in-memory leaky bucket; replace with Redis in production)
# ---------------------------------------------------------------------------

_RATE_WINDOW: int = 60   # seconds
_RATE_LIMIT: int = 10    # max attempts per window per device

_attempt_log: Dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(device_id: str) -> None:
    now = time.time()
    attempts = _attempt_log[device_id]
    # Prune old entries
    _attempt_log[device_id] = [t for t in attempts if now - t < _RATE_WINDOW]
    if len(_attempt_log[device_id]) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many OTP attempts. Retry after {_RATE_WINDOW}s window resets.",
        )
    _attempt_log[device_id].append(now)


# ---------------------------------------------------------------------------
# Anomaly-detection hook (stubbed — replace with logging/SIEM in prod)
# ---------------------------------------------------------------------------

def _log_failure(device_id: str, reason: str, request: Request) -> None:
    """
    STUB: hook for failed verification events.
    In production: emit structured log to ELK / Splunk / Cloud Logging.
    """
    print(
        f"[SECURITY] Verification failure | device={device_id} "
        f"| reason={reason} | ip={request.client.host if request.client else 'unknown'}"
    )


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class EnrollRequest(BaseModel):
    device_id: Optional[str] = Field(
        default=None,
        description="Optional device ID.  Server assigns one if omitted.",
    )
    user_label: Optional[str] = Field(
        default=None,
        description="Human-readable label (username / device name).",
    )


class EnrollResponse(BaseModel):
    device_id: str
    secret_b32: str = Field(
        description=(
            "Base32-encoded shared secret K.  "
            "Store this securely on the client.  "
            "It will NOT be retrievable from the server again."
        )
    )
    qr_payload: str = Field(
        description=(
            "otpauth:// URI — scan with any TOTP-compatible app "
            "or the walk-otp client CLI."
        )
    )
    graph_config: dict
    otp_config: dict
    message: str


class VerifyRequest(BaseModel):
    device_id: str
    otp: str = Field(min_length=6, max_length=8)


class VerifyResponse(BaseModel):
    valid: bool
    device_id: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["meta"], include_in_schema=False)
async def root():
    """Landing page — human-readable server status shown in a browser."""
    from fastapi.responses import HTMLResponse

    enrolled = len(_store.all_devices())
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Walk-OTP Server</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', sans-serif;
    background: #0d1117;
    color: #e6edf3;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
  }}
  .card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 2.5rem 3rem;
    max-width: 640px;
    width: 100%;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  }}
  .badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #1a7f37;
    color: #3fb950;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: .06em;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    margin-bottom: 1.25rem;
    border: 1px solid #238636;
  }}
  .badge::before {{ content: '●'; font-size: 0.6rem; }}
  h1 {{ font-size: 1.6rem; font-weight: 700; margin-bottom: 0.4rem; }}
  .subtitle {{ color: #8b949e; font-size: 0.9rem; margin-bottom: 2rem; line-height: 1.5; }}
  .stat-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 2rem;
  }}
  .stat {{
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 1rem 1.25rem;
  }}
  .stat-label {{ font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: .08em; }}
  .stat-value {{ font-size: 1.5rem; font-weight: 700; color: #58a6ff; margin-top: 0.25rem; }}
  h2 {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: .1em; color: #8b949e; margin-bottom: 0.75rem; }}
  .endpoint-list {{ list-style: none; display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 2rem; }}
  .endpoint-list li {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
  }}
  .method {{
    font-weight: 700;
    font-size: 0.7rem;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    min-width: 48px;
    text-align: center;
  }}
  .get  {{ background: #1f6feb22; color: #58a6ff; border: 1px solid #1f6feb; }}
  .post {{ background: #2ea04326; color: #3fb950; border: 1px solid #2ea043; }}
  .del  {{ background: #da363326; color: #f85149; border: 1px solid #da3633; }}
  .path {{ color: #e6edf3; }}
  .desc {{ margin-left: auto; color: #8b949e; font-family: 'Inter', sans-serif; font-size: 0.75rem; }}
  .links {{ display: flex; gap: 1rem; }}
  .link-btn {{
    flex: 1;
    display: block;
    text-align: center;
    padding: 0.65rem;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    text-decoration: none;
    transition: opacity .15s;
  }}
  .link-btn:hover {{ opacity: 0.8; }}
  .btn-primary {{ background: #238636; color: #fff; border: 1px solid #2ea043; }}
  .btn-secondary {{ background: #21262d; color: #e6edf3; border: 1px solid #30363d; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">ONLINE</div>
  <h1>Random-Walk OTP Server</h1>
  <p class="subtitle">
    TOTP-style 2FA using a random walk on a graph instead of HMAC-SHA1.<br>
    SemProj face-recognition authentication module · v1.0.0
  </p>

  <div class="stat-row">
    <div class="stat">
      <div class="stat-label">Enrolled Devices</div>
      <div class="stat-value">{enrolled}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Time Step</div>
      <div class="stat-value">30s</div>
    </div>
  </div>

  <h2>Endpoints</h2>
  <ul class="endpoint-list">
    <li><span class="method post">POST</span><span class="path">/enroll</span><span class="desc">Pair a new device</span></li>
    <li><span class="method post">POST</span><span class="path">/verify</span><span class="desc">Validate an OTP</span></li>
    <li><span class="method get">GET</span><span class="path">/devices</span><span class="desc">List enrolled devices</span></li>
    <li><span class="method del">DEL</span><span class="path">/devices/{{id}}</span><span class="desc">De-enroll a device</span></li>
    <li><span class="method get">GET</span><span class="path">/health</span><span class="desc">Liveness check</span></li>
  </ul>

  <div class="links">
    <a class="link-btn btn-primary" href="/docs">Interactive Docs (Swagger)</a>
    <a class="link-btn btn-secondary" href="/redoc">ReDoc</a>
  </div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.post("/enroll", response_model=EnrollResponse, tags=["enrollment"])
async def enroll(req: EnrollRequest, request: Request):
    """
    Enrollment endpoint (call ONCE per device, over authenticated TLS session).

    Generates a fresh 256-bit secret K, stores it encrypted at rest,
    and returns it to the caller exactly once.  K is never logged.
    """
    device_id = req.device_id or str(uuid.uuid4())

    if _store.device_exists(device_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device '{device_id}' already enrolled.  De-enroll first.",
        )

    secret_k = generate_secret(32)           # 256-bit CSPRNG secret
    secret_b32 = secret_to_b32(secret_k)    # Base32 for transport + QR

    graph_cfg_dict = _GRAPH_CFG.to_dict()
    _store.add_device(device_id, secret_b32, graph_cfg_dict)

    label = req.user_label or device_id
    qr_payload = (
        f"otpauth://walk-totp/{label}"
        f"?secret={secret_b32}"
        f"&period={_OTP_CFG.time_step}"
        f"&digits={_OTP_CFG.digits}"
        f"&algorithm=WALK-SHA256"
    )

    return EnrollResponse(
        device_id=device_id,
        secret_b32=secret_b32,
        qr_payload=qr_payload,
        graph_config=graph_cfg_dict,
        otp_config={
            "time_step": _OTP_CFG.time_step,
            "walk_steps": _OTP_CFG.walk_steps,
            "digits": _OTP_CFG.digits,
        },
        message=(
            "Enrollment successful.  Store secret_b32 securely on the client. "
            "It will NOT be re-issued."
        ),
    )


@app.post("/verify", response_model=VerifyResponse, tags=["verification"])
async def verify(req: VerifyRequest, request: Request):
    """
    OTP Verification endpoint.

    Checks OTP against T-1, T, T+1 (±1 window for clock drift).
    Prevents replay within the same time window (last-used counter tracking).
    Rate-limits per device to prevent brute force.
    """
    _check_rate_limit(req.device_id)

    if not _store.device_exists(req.device_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{req.device_id}' not enrolled.",
        )

    secret_b32 = _store.get_secret_b32(req.device_id)
    secret_k = b32_to_secret(secret_b32)

    graph_dict = _store.get_graph_config(req.device_id)
    graph_cfg = GraphConfig.from_dict(graph_dict)
    otp_cfg = OTPConfig(graph=graph_cfg)

    is_valid, matched_counter = verify_otp(
        secret_k,
        req.otp,
        config=otp_cfg,
        window=1,
    )

    if not is_valid:
        _log_failure(req.device_id, "OTP mismatch", request)
        return VerifyResponse(
            valid=False,
            device_id=req.device_id,
            message="OTP is invalid or expired.",
        )

    # Replay prevention: reject if this counter was already used
    last_counter = _store.get_last_counter(req.device_id)
    if matched_counter <= last_counter:
        _log_failure(req.device_id, "OTP replay", request)
        return VerifyResponse(
            valid=False,
            device_id=req.device_id,
            message="OTP already used (replay rejected).",
        )

    _store.set_last_counter(req.device_id, matched_counter)

    return VerifyResponse(
        valid=True,
        device_id=req.device_id,
        message=f"OTP verified successfully (window T={matched_counter}).",
    )


@app.delete("/devices/{device_id}", tags=["enrollment"])
async def de_enroll(device_id: str):
    """De-enroll a device (admin operation)."""
    removed = _store.remove_device(device_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found.",
        )
    return {"message": f"Device '{device_id}' de-enrolled successfully."}


@app.get("/devices", tags=["enrollment"])
async def list_devices():
    """List enrolled device IDs (admin operation)."""
    return {"devices": _store.all_devices()}
