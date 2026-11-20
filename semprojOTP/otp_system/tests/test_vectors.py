"""
Cross-implementation test: the Python core and the JavaScript phone client
must produce identical graphs, walk paths and OTPs for the pinned vectors.
The JS half runs only when Node.js is on PATH.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from walk_otp import GraphConfig, b32_to_secret, generate_otp_with_path

VECTORS = json.loads((Path(__file__).parent / "walk_otp_vectors.json").read_text())
JS_CLIENT = Path(__file__).resolve().parents[3] / "authenticator" / "walk_otp.js"


def test_python_matches_vectors():
    assert GraphConfig().adjacency() == VECTORS["graph"]
    for case in VECTORS["cases"]:
        otp, _, path = generate_otp_with_path(
            b32_to_secret(case["secret_b32"]), counter=case["counter"], context=case["context"]
        )
        assert (otp, path) == (case["otp"], case["path"])


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_javascript_matches_vectors():
    script = f"""
    const W = require({json.dumps(str(JS_CLIENT))});
    const v = {json.dumps(VECTORS)};
    if (JSON.stringify(W.graph()) !== JSON.stringify(v.graph)) {{ console.log("GRAPH MISMATCH"); process.exit(1); }}
    for (const c of v.cases) {{
      const r = W.generateOtp(W.b32ToBytes(c.secret_b32), c.counter, c.context);
      if (r.otp !== c.otp || JSON.stringify(r.path) !== JSON.stringify(c.path)) {{
        console.log("MISMATCH", JSON.stringify(c), JSON.stringify(r)); process.exit(1);
      }}
    }}
    console.log("OK");
    """
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert result.returncode == 0 and "OK" in result.stdout, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Grace window: an expired code is accepted only briefly
# ---------------------------------------------------------------------------

from walk_otp import generate_otp, generate_secret, otp_age, verify_otp  # noqa: E402

STEP_START = 1_800_000_000 - (1_800_000_000 % 30)   # a time exactly at the start of a step


@pytest.mark.parametrize("seconds_after_expiry,accepted", [(0.5, True), (9.5, True), (10.5, False), (29, False)])
def test_previous_code_only_within_grace(seconds_after_expiry, accepted):
    k = generate_secret()
    old = generate_otp(k, counter=STEP_START // 30 - 1)[0]
    ok, _ = verify_otp(k, old, grace_seconds=10, now=STEP_START + seconds_after_expiry)
    assert ok is accepted


def test_without_grace_expired_code_lasts_a_full_step():
    """The behaviour the user reported: RFC-style ±1 window accepts a code 29 s after it expired."""
    k = generate_secret()
    old = generate_otp(k, counter=STEP_START // 30 - 1)[0]
    assert verify_otp(k, old, now=STEP_START + 29)[0]


@pytest.mark.parametrize("seconds_before_valid,accepted", [(5, True), (15, False)])
def test_next_code_only_for_small_clock_skew(seconds_before_valid, accepted):
    k = generate_secret()
    nxt = generate_otp(k, counter=STEP_START // 30 + 1)[0]
    ok, _ = verify_otp(k, nxt, grace_seconds=10, now=STEP_START + 30 - seconds_before_valid)
    assert ok is accepted


def test_current_code_always_valid_and_age():
    k = generate_secret()
    cur = generate_otp(k, counter=STEP_START // 30)[0]
    for t in (0, 15, 29.9):
        assert verify_otp(k, cur, grace_seconds=10, now=STEP_START + t)[0]
    assert otp_age(k, cur, now=STEP_START + 95) == 3
    assert otp_age(k, "000000" if cur != "000000" else "111111", now=STEP_START) is None
