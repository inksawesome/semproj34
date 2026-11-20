"""
client/client_cli.py — Walk-OTP Client (CLI)
============================================
Usage
-----
  # Enroll (run once per device):
  python client_cli.py enroll --server http://localhost:8000 --device-id my_phone

  # Generate OTP loop (no network call for generation):
  python client_cli.py generate

  # One-shot OTP (print current OTP and exit):
  python client_cli.py generate --once

  # Verify against server:
  python client_cli.py verify --server http://localhost:8000

Client stores K encrypted locally in ~/.walk_otp/client_state.json.enc
using a password-derived key (prompted once at setup, or via
WALK_OTP_CLIENT_PASS env var).
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# Allow imports from the otp_system root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Lazy-import httpx only for enroll/verify (not needed for OTP generation)
try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from cryptography.fernet import Fernet

from walk_otp import (
    GraphConfig,
    OTPConfig,
    b32_to_secret,
    generate_otp,
    secret_to_b32,
    _current_time_step,
)

# ---------------------------------------------------------------------------
# Local encrypted state
# ---------------------------------------------------------------------------

_STATE_DIR = Path.home() / ".walk_otp"
_STATE_FILE = _STATE_DIR / "client_state.json.enc"


def _derive_fernet_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet key from a password using PBKDF2."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        iterations=260_000,
        dklen=32,
    )
    return base64.urlsafe_b64encode(dk)


def _get_password(prompt: str = "Client passphrase: ") -> str:
    pwd = os.environ.get("WALK_OTP_CLIENT_PASS")
    if pwd:
        return pwd
    return getpass.getpass(prompt)


def _load_state() -> dict:
    """Load and decrypt client state.  Returns {} if no state file."""
    if not _STATE_FILE.exists():
        return {}
    raw = _STATE_FILE.read_bytes()
    # First 16 bytes = salt
    salt = raw[:16]
    encrypted = raw[16:]
    password = _get_password("Passphrase to unlock client state: ")
    key = _derive_fernet_key(password, salt)
    fernet = Fernet(key)
    try:
        plaintext = fernet.decrypt(encrypted)
    except Exception:
        print("[ERROR] Wrong passphrase or corrupted state file.")
        sys.exit(1)
    return json.loads(plaintext)


def _save_state(state: dict, password: str | None = None) -> None:
    """Encrypt and save client state."""
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    if password is None:
        password = _get_password("Set a passphrase for client state: ")
        confirm = _get_password("Confirm passphrase: ")
        if password != confirm:
            print("[ERROR] Passphrases do not match.")
            sys.exit(1)
    salt = os.urandom(16)
    key = _derive_fernet_key(password, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(json.dumps(state).encode())
    _STATE_FILE.write_bytes(salt + encrypted)
    print(f"[OK] Client state saved to {_STATE_FILE}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_enroll(args):
    """Contact server /enroll, receive K, store it locally."""
    if httpx is None:
        print("[ERROR] httpx not installed. Run: pip install httpx")
        sys.exit(1)

    server = args.server.rstrip("/")
    device_id = args.device_id or input("Device ID (leave blank for server-assigned): ").strip() or None
    label = args.label or input("Label (optional): ").strip() or None

    payload = {}
    if device_id:
        payload["device_id"] = device_id
    if label:
        payload["user_label"] = label

    print(f"[*] Enrolling with server at {server} …")
    try:
        resp = httpx.post(f"{server}/enroll", json=payload, timeout=10)
    except Exception as e:
        print(f"[ERROR] Could not reach server: {e}")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"[ERROR] Server returned {resp.status_code}: {resp.text}")
        sys.exit(1)

    data = resp.json()
    print("\n[ENROLLED SUCCESSFULLY]")
    print(f"  Device ID   : {data['device_id']}")
    print(f"  Secret (B32): {data['secret_b32']}")
    print(f"  QR payload  : {data['qr_payload']}")
    print()
    print("[!] The secret will NOT be re-issued by the server.")
    print("    Store it now.  The client will save it encrypted locally.")

    state = {
        "device_id": data["device_id"],
        "secret_b32": data["secret_b32"],
        "graph_config": data["graph_config"],
        "otp_config": data["otp_config"],
        "server": server,
    }
    pwd = _get_password("Set a passphrase to protect the local secret: ")
    confirm = _get_password("Confirm passphrase: ")
    if pwd != confirm:
        print("[ERROR] Passphrases do not match.")
        sys.exit(1)
    _save_state(state, password=pwd)


def cmd_generate(args):
    """Generate OTP locally — no network call."""
    state = _load_state()
    if not state:
        print("[ERROR] No client state found.  Run: python client_cli.py enroll")
        sys.exit(1)

    secret_k = b32_to_secret(state["secret_b32"])
    graph_cfg = GraphConfig.from_dict(state["graph_config"])
    otp_cfg_dict = state.get("otp_config", {})
    otp_cfg = OTPConfig(
        time_step=otp_cfg_dict.get("time_step", 30),
        walk_steps=otp_cfg_dict.get("walk_steps", 16),
        digits=otp_cfg_dict.get("digits", 6),
        graph=graph_cfg,
    )

    device_id = state["device_id"]

    if args.once:
        otp, counter = generate_otp(secret_k, config=otp_cfg)
        t_rem = otp_cfg.time_step - (int(time.time()) % otp_cfg.time_step)
        print(f"Device : {device_id}")
        print(f"OTP    : {otp}")
        print(f"Valid for ~{t_rem}s")
        return

    # Continuous loop
    print(f"[Walk-OTP Client]  Device: {device_id}")
    print("Press Ctrl+C to exit.\n")
    last_t = -1
    try:
        while True:
            t_now = _current_time_step(otp_cfg.time_step)
            if t_now != last_t:
                otp, _ = generate_otp(secret_k, counter=t_now, config=otp_cfg)
                last_t = t_now
                t_rem = otp_cfg.time_step - (int(time.time()) % otp_cfg.time_step)
                # Draw countdown bar
                bar_len = 20
                filled = int(bar_len * t_rem / otp_cfg.time_step)
                bar = "█" * filled + "░" * (bar_len - filled)

            t_rem = otp_cfg.time_step - (int(time.time()) % otp_cfg.time_step)
            filled = int(bar_len * t_rem / otp_cfg.time_step)
            bar = "█" * filled + "░" * (bar_len - filled)

            print(
                f"\r  OTP: \033[1;32m{otp}\033[0m  [{bar}] {t_rem:2d}s  ",
                end="",
                flush=True,
            )
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[Exited]")


def cmd_verify(args):
    """Read current OTP from local generation, POST it to server /verify."""
    if httpx is None:
        print("[ERROR] httpx not installed. Run: pip install httpx")
        sys.exit(1)

    state = _load_state()
    if not state:
        print("[ERROR] No client state found.  Run: python client_cli.py enroll")
        sys.exit(1)

    secret_k = b32_to_secret(state["secret_b32"])
    graph_cfg = GraphConfig.from_dict(state["graph_config"])
    otp_cfg_dict = state.get("otp_config", {})
    otp_cfg = OTPConfig(
        time_step=otp_cfg_dict.get("time_step", 30),
        walk_steps=otp_cfg_dict.get("walk_steps", 16),
        digits=otp_cfg_dict.get("digits", 6),
        graph=graph_cfg,
    )

    otp, _ = generate_otp(secret_k, config=otp_cfg)
    server = args.server or state.get("server", "http://localhost:8000")
    server = server.rstrip("/")

    print(f"[*] Generated OTP: {otp}")
    print(f"[*] Sending to {server}/verify …")

    try:
        resp = httpx.post(
            f"{server}/verify",
            json={"device_id": state["device_id"], "otp": otp},
            timeout=10,
        )
    except Exception as e:
        print(f"[ERROR] Could not reach server: {e}")
        sys.exit(1)

    data = resp.json()
    if data.get("valid"):
        print(f"\033[1;32m[✓] OTP ACCEPTED\033[0m — {data['message']}")
    else:
        print(f"\033[1;31m[✗] OTP REJECTED\033[0m — {data['message']}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="walk-otp-client",
        description="Random-Walk OTP Client (local OTP generation — no network for generation)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # enroll
    p_enroll = sub.add_parser("enroll", help="Enroll this device with the server")
    p_enroll.add_argument("--server", default="http://localhost:8000", help="Server URL")
    p_enroll.add_argument("--device-id", help="Explicit device ID (optional)")
    p_enroll.add_argument("--label", help="Human-readable label")

    # generate
    p_gen = sub.add_parser("generate", help="Generate OTP locally (no network)")
    p_gen.add_argument("--once", action="store_true", help="Print once and exit")

    # verify
    p_verify = sub.add_parser("verify", help="Generate OTP and verify against server")
    p_verify.add_argument("--server", default=None, help="Override server URL")

    args = parser.parse_args()

    dispatch = {
        "enroll": cmd_enroll,
        "generate": cmd_generate,
        "verify": cmd_verify,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
