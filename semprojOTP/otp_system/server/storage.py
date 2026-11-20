"""
server/storage.py — Encrypted-at-rest device store
====================================================
Stores device secrets and OTP state using Fernet symmetric encryption
so that K never sits in plaintext on disk.

A real deployment would use a proper secrets manager / HSM.
For MVP: AES-128-CBC via Fernet, master key loaded from env var
WALK_OTP_MASTER_KEY (32-byte base64url string).
If the env var is absent a randomly generated key is used per-process
(acceptable for development; NOT for production).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, Optional

from cryptography.fernet import Fernet, InvalidToken


# ---------------------------------------------------------------------------
# Master key bootstrap
# ---------------------------------------------------------------------------

def _load_or_create_master_key() -> bytes:
    """
    Load Fernet master key from env (WALK_OTP_MASTER_KEY).
    If absent, generate a new one and print a warning.
    """
    raw = os.environ.get("WALK_OTP_MASTER_KEY")
    if raw:
        return raw.encode()
    key = Fernet.generate_key()
    print(
        "[WARN] WALK_OTP_MASTER_KEY not set. "
        "Using ephemeral key — storage will not survive process restart.\n"
        f"       For persistent use, set: WALK_OTP_MASTER_KEY={key.decode()}"
    )
    return key


_MASTER_KEY: bytes = _load_or_create_master_key()
_FERNET: Fernet = Fernet(_MASTER_KEY)

# ---------------------------------------------------------------------------
# Storage file path (JSON on disk, Fernet-encrypted values)
# ---------------------------------------------------------------------------

_DEFAULT_STORE_PATH = Path(os.environ.get("WALK_OTP_STORE_PATH") or Path(__file__).parent / "device_store.json.enc")


class DeviceStore:
    """
    Thread-safe (single-process) encrypted device store.

    Schema per device_id:
    {
        "secret_b32": "<Fernet-encrypted Base32 secret>",
        "graph_config": { ... },
        "last_used_counter": <int>,
        "enrolled_at": <float unix>
    }
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path or _DEFAULT_STORE_PATH
        self._data: Dict[str, dict] = {}
        self._load()

    # ---- persistence -------------------------------------------------------

    def _load(self):
        if self._path.exists():
            raw = self._path.read_bytes()
            try:
                plaintext = _FERNET.decrypt(raw)
            except InvalidToken:
                raise RuntimeError(
                    f"{self._path} was encrypted with a different WALK_OTP_MASTER_KEY. Set the key it was "
                    "created with, or point WALK_OTP_STORE_PATH at a new file to start an empty store."
                ) from None
            self._data = json.loads(plaintext)

    def _save(self):
        plaintext = json.dumps(self._data).encode()
        encrypted = _FERNET.encrypt(plaintext)
        self._path.write_bytes(encrypted)

    # ---- public API --------------------------------------------------------

    def add_device(
        self,
        device_id: str,
        secret_b32: str,
        graph_config: dict,
    ) -> None:
        """Enroll a new device."""
        self._data[device_id] = {
            "secret_enc": _FERNET.encrypt(secret_b32.encode()).decode(),
            "graph_config": graph_config,
            "last_used_counter": -1,
            "enrolled_at": time.time(),
        }
        self._save()

    def get_secret_b32(self, device_id: str) -> Optional[str]:
        """Retrieve and decrypt the secret for a device."""
        record = self._data.get(device_id)
        if not record:
            return None
        return _FERNET.decrypt(record["secret_enc"].encode()).decode()

    def get_graph_config(self, device_id: str) -> Optional[dict]:
        return self._data.get(device_id, {}).get("graph_config")

    def get_last_counter(self, device_id: str) -> int:
        return self._data.get(device_id, {}).get("last_used_counter", -1)

    def set_last_counter(self, device_id: str, counter: int) -> None:
        if device_id in self._data:
            self._data[device_id]["last_used_counter"] = counter
            self._save()

    def device_exists(self, device_id: str) -> bool:
        return device_id in self._data

    def remove_device(self, device_id: str) -> bool:
        if device_id in self._data:
            del self._data[device_id]
            self._save()
            return True
        return False

    def all_devices(self) -> list[str]:
        return list(self._data.keys())
