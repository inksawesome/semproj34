"""
Regenerate walk_otp_vectors.json — fixed inputs/outputs that pin the Python
core and the JavaScript client (authenticator/walk_otp.js) to identical OTPs.

    python tests/make_vectors.py
"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from walk_otp import GraphConfig, generate_otp_with_path, secret_to_b32, transaction_context

OUT = Path(__file__).parent / "walk_otp_vectors.json"

cases = []
for i in range(12):
    secret = hashlib.sha256(f"vector-secret-{i}".encode()).digest()
    counter = 57_234_810 + i * 977
    context = "" if i % 3 == 0 else transaction_context(f"tx{i:04d}", 1000 + i * 250.5, f"payee{i}@vaulttrust.com")
    otp, _, path = generate_otp_with_path(secret, counter=counter, context=context)
    cases.append({
        "secret_b32": secret_to_b32(secret),
        "counter": counter,
        "context": context,
        "otp": otp,
        "path": path,
    })

OUT.write_text(json.dumps({
    "graph": GraphConfig().adjacency(),
    "cases": cases,
}, indent=1))
print(f"wrote {len(cases)} vectors to {OUT}")
