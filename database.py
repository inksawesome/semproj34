"""
VaultTrust persistence (SQLite).

Stored per user: the *protected* face template (never the raw embedding),
the template key and OTP secret (both Fernet-encrypted at rest), balance,
and whether a phone authenticator has been paired.
"""

import json
import os
import sqlite3
import time
from contextlib import contextmanager

import numpy as np
from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("VT_DB_PATH") or os.path.join(BASE_DIR, "vaulttrust.db")  # tests point this at a temp file
KEY_PATH = os.path.join(BASE_DIR, "db_key.key")
STARTING_BALANCE = 25_000.0


def _master_key() -> bytes:
    if not os.path.exists(KEY_PATH):
        with open(KEY_PATH, "wb") as f:
            f.write(Fernet.generate_key())
    with open(KEY_PATH, "rb") as f:
        return f.read()


_fernet = Fernet(_master_key())


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            email           TEXT PRIMARY KEY,
            template        BLOB NOT NULL,
            template_key    BLOB NOT NULL,
            otp_secret      BLOB NOT NULL,
            device_paired   INTEGER NOT NULL DEFAULT 0,
            balance         REAL NOT NULL,
            created_at      REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ref         TEXT UNIQUE NOT NULL,
            sender      TEXT NOT NULL,
            receiver    TEXT NOT NULL,
            amount      REAL NOT NULL,
            status      TEXT NOT NULL,
            created_at  REAL NOT NULL,
            evidence    TEXT
        );
        CREATE TABLE IF NOT EXISTS audit (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT,
            event       TEXT NOT NULL,
            detail      TEXT,
            created_at  REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS used_otps (
            email   TEXT NOT NULL,
            scope   TEXT NOT NULL,
            counter INTEGER NOT NULL,
            PRIMARY KEY (email, scope, counter)
        );
        """)
        # migrations for databases created before these columns existed
        cols = {r["name"] for r in c.execute("PRAGMA table_info(users)")}
        if "paired_host" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN paired_host TEXT")      # laptop address the phone paired on
        if "paired_at" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN paired_at REAL")


# ---------------------------------------------------------------- users

def create_user(email: str, template: np.ndarray, template_key: bytes, otp_secret: bytes) -> bool:
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO users (email, template, template_key, otp_secret, device_paired, balance, created_at) "
                "VALUES (?, ?, ?, ?, 0, ?, ?)",
                (email.lower(), template.astype(np.float32).tobytes(),
                 _fernet.encrypt(template_key), _fernet.encrypt(otp_secret),
                 STARTING_BALANCE, time.time()),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_user(email: str):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    if row is None:
        return None
    return {
        "email": row["email"],
        "template": np.frombuffer(row["template"], dtype=np.float32),
        "template_key": _fernet.decrypt(row["template_key"]),
        "otp_secret": _fernet.decrypt(row["otp_secret"]),
        "device_paired": bool(row["device_paired"]),
        "paired_host": row["paired_host"],
        "paired_at": row["paired_at"],
        "balance": row["balance"],
    }


def user_exists(email: str) -> bool:
    with _conn() as c:
        return c.execute("SELECT 1 FROM users WHERE email = ?", (email.lower(),)).fetchone() is not None


def set_device_paired(email: str, paired: bool = True, host: str | None = None):
    with _conn() as c:
        c.execute("UPDATE users SET device_paired = ?, paired_host = COALESCE(?, paired_host), paired_at = ? "
                  "WHERE email = ?", (int(paired), host, time.time() if paired else None, email.lower()))


def replace_otp_secret(email: str, otp_secret: bytes, host: str | None):
    """Re-pair: a new secret K for a new phone. Every previously paired phone or browser stops working."""
    with _conn() as c:
        c.execute("UPDATE users SET otp_secret = ?, device_paired = 1, paired_host = ?, paired_at = ? WHERE email = ?",
                  (_fernet.encrypt(otp_secret), host, time.time(), email.lower()))
        c.execute("DELETE FROM used_otps WHERE email = ?", (email.lower(),))   # counters belonged to the old key


def replace_template(email: str, template: np.ndarray, template_key: bytes):
    """Revoke the old template by re-keying (cancelable biometrics)."""
    with _conn() as c:
        c.execute("UPDATE users SET template = ?, template_key = ? WHERE email = ?",
                  (template.astype(np.float32).tobytes(), _fernet.encrypt(template_key), email.lower()))


def delete_user(email: str):
    with _conn() as c:
        c.execute("DELETE FROM users WHERE email = ?", (email.lower(),))


def get_balance(email: str) -> float:
    with _conn() as c:
        row = c.execute("SELECT balance FROM users WHERE email = ?", (email.lower(),)).fetchone()
    return row["balance"] if row else 0.0


# ---------------------------------------------------------------- OTP replay protection

def consume_otp_counter(email: str, scope: str, counter: int) -> bool:
    """
    Record that an OTP time-step was used. Returns False on replay
    (this or a later step was already accepted for the same scope).
    """
    with _conn() as c:
        row = c.execute("SELECT MAX(counter) AS m FROM used_otps WHERE email = ? AND scope = ?",
                        (email.lower(), scope)).fetchone()
        if row["m"] is not None and counter <= row["m"]:
            return False
        c.execute("INSERT INTO used_otps VALUES (?, ?, ?)", (email.lower(), scope, counter))
    return True


# ---------------------------------------------------------------- transactions

def create_transaction(ref: str, sender: str, receiver: str, amount: float, status: str, evidence=None):
    with _conn() as c:
        c.execute(
            "INSERT INTO transactions (ref, sender, receiver, amount, status, created_at, evidence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ref, sender.lower(), receiver.lower(), amount, status, time.time(),
             json.dumps(evidence) if evidence is not None else None),
        )


def set_transaction_status(ref: str, status: str, evidence=None):
    with _conn() as c:
        if evidence is None:
            c.execute("UPDATE transactions SET status = ? WHERE ref = ?", (status, ref))
        else:
            c.execute("UPDATE transactions SET status = ?, evidence = ? WHERE ref = ?",
                      (status, json.dumps(evidence), ref))


def settle_transaction(ref: str) -> bool:
    """Move the money for a pending transaction atomically. False if funds are insufficient."""
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        tx = conn.execute("SELECT sender, receiver, amount, status FROM transactions WHERE ref = ?", (ref,)).fetchone()
        if tx is None or tx[3] not in ("PENDING", "PENDING_STEP_UP"):
            conn.execute("ROLLBACK")
            return False
        sender, receiver, amount, _ = tx
        bal = conn.execute("SELECT balance FROM users WHERE email = ?", (sender,)).fetchone()
        if bal is None or bal[0] < amount:
            conn.execute("UPDATE transactions SET status = 'FAILED_FUNDS' WHERE ref = ?", (ref,))
            conn.execute("COMMIT")
            return False
        conn.execute("UPDATE users SET balance = balance - ? WHERE email = ?", (amount, sender))
        conn.execute("UPDATE users SET balance = balance + ? WHERE email = ?", (amount, receiver))
        conn.execute("UPDATE transactions SET status = 'COMPLETED' WHERE ref = ?", (ref,))
        conn.execute("COMMIT")
        return True
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def get_transactions(email: str, limit: int = 20):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM transactions WHERE sender = ? OR receiver = ? ORDER BY created_at DESC LIMIT ?",
            (email.lower(), email.lower(), limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- audit log

def audit(email, event: str, detail=None):
    with _conn() as c:
        c.execute("INSERT INTO audit (email, event, detail, created_at) VALUES (?, ?, ?, ?)",
                  (email.lower() if email else None, event,
                   json.dumps(detail) if detail is not None else None, time.time()))


def get_audit(email: str, limit: int = 30):
    with _conn() as c:
        rows = c.execute("SELECT * FROM audit WHERE email = ? ORDER BY created_at DESC LIMIT ?",
                         (email.lower(), limit)).fetchall()
    return [dict(r) for r in rows]


init_db()
