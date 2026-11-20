"""
End-to-end tests: every component, then the full app workflows driven through
Streamlit's AppTest with camera input replaced by REAL recorded video.

    python -m pytest tests/test_e2e.py -v -s          (~4-6 min on CPU)

The only part not exercised is the browser <-> server WebRTC transport: frames
from data/raw_videos are fed to the same LivenessProcessor.recv() the webcam
stream calls. A temporary database is used (see conftest.py).

Note: the deployed anti-spoofing model (v4) trained on most of these webcam
clips, so its scores here test the *pipeline*, not generalisation. The
held-out evaluation lives in reports/summary.json.
"""

import glob
import json
import os
import socket
import sqlite3
import subprocess
import shutil
import time
import urllib.request

import av
import cv2
import numpy as np
import pytest

import biometric_template as bt
import database as db
import face_engine
import fas_engine
import liveness_engine as le
from walk_otp import generate_otp, generate_secret, transaction_context, verify_otp

VIDEOS = "data/raw_videos"
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
needs_videos = pytest.mark.skipif(not os.path.exists(f"{VIDEOS}/rwitankar_real_1.mp4"), reason="no webcam videos")


# ================================================================== helpers

def video_frames(name, size=(640, 360)):
    cap = cv2.VideoCapture(f"{VIDEOS}/{name}.mp4")
    while True:
        ok, f = cap.read()
        if not ok:
            return
        yield cv2.resize(f, size)


def run_liveness(name, challenges):
    """Feed a recorded video through the live LivenessProcessor, as the WebRTC stream would."""
    p = le.LivenessProcessor()
    p.challenges = list(challenges)
    for bgr in video_frames(name):
        p.recv(av.VideoFrame.from_ndarray(bgr, format="bgr24"))
        if p.state in ("PASSED", "FAILED"):
            break
    return p.snapshot()


def padded(paths):
    return [cv2.copyMakeBorder(cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB), 60, 60, 60, 60, cv2.BORDER_REPLICATE)
            for p in paths]


def lcc_subject(subject, n):
    return padded(sorted(glob.glob(f"LCC_FASD_development/real/*_id{subject}_*"))[:n])


# ================================================================== 1. random-walk OTP

class TestOTP:
    def test_code_space_is_full(self):
        codes = {generate_otp(generate_secret(), counter=i)[0] for i in range(5000)}
        assert len(codes) > 4950           # v1 produced only 768 distinct codes from 20,000 secrets

    def test_context_binds_code_to_transaction(self):
        k, t = generate_secret(), 60_000_000
        base = generate_otp(k, counter=t, context=transaction_context("TX-1", 5000, "bob@x.com"))[0]
        for ctx in (transaction_context("TX-1", 5000.01, "bob@x.com"), transaction_context("TX-1", 5000, "eve@x.com"),
                    transaction_context("TX-2", 5000, "bob@x.com"), ""):
            assert generate_otp(k, counter=t, context=ctx)[0] != base

    def test_window_and_expiry(self):
        k = generate_secret()
        now = int(time.time()) // 30
        for d, ok in ((-1, True), (0, True), (1, True), (-3, False), (3, False)):
            assert verify_otp(k, generate_otp(k, counter=now + d)[0])[0] is ok

    @pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
    def test_phone_javascript_matches_server_right_now(self):
        """The phone computes the code for the current time; the server must accept it."""
        k = generate_secret()
        from walk_otp import secret_to_b32
        ctx = transaction_context("TX-LIVE", 4321.5, "Alice@VaultTrust.com ")
        js = (f"const W=require({json.dumps(os.path.abspath('authenticator/walk_otp.js'))});"
              f"const c=W.transactionContext('TX-LIVE',4321.5,'Alice@VaultTrust.com ');"
              f"process.stdout.write(c+'\\n'+W.generateOtp(W.b32ToBytes('{secret_to_b32(k)}'),undefined,c).otp)")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout.split("\n")
        assert out[0] == ctx
        assert verify_otp(k, out[1], context=ctx)[0]


class TestAuthenticatorServer:
    def test_serves_phone_page_on_the_network(self):
        import authenticator_server as srv
        with socket.socket() as s:
            s.bind(("", 0))
            port = s.getsockname()[1]
        assert srv.start_server(port)
        for host in ("127.0.0.1", srv.lan_ip()):
            html = urllib.request.urlopen(f"http://{host}:{port}/", timeout=5).read().decode()
            assert "VaultTrust Key" in html and "walk_otp.js" in html
        js = urllib.request.urlopen(f"http://127.0.0.1:{port}/walk_otp.js", timeout=5).read().decode()
        assert "hmacSha256" in js


# ================================================================== 2. face recognition + cancelable template

@pytest.fixture(scope="module")
def lcc_embeddings():
    a = [face_engine.embed(f)[0] for f in lcc_subject("48", 6)]
    b = [face_engine.embed(f)[0] for f in lcc_subject("43", 6)]
    assert all(e is not None for e in a + b)
    return a, b


class TestFaceAndTemplate:
    def test_embedding_shape_and_norm(self, lcc_embeddings):
        e = lcc_embeddings[0][0]
        assert e.shape == (512,) and abs(np.linalg.norm(e) - 1) < 1e-3

    def test_no_face_returns_none(self):
        assert face_engine.embed(np.full((480, 640, 3), 127, np.uint8)) == (None, None)

    def test_genuine_accepted_impostor_rejected_in_protected_domain(self, lcc_embeddings):
        a, b = lcc_embeddings
        key = bt.new_key()
        tmpl = bt.protect(np.mean(a[:3], axis=0) / np.linalg.norm(np.mean(a[:3], axis=0)), key)
        assert tmpl.shape == (256,)
        assert all(bt.match(e, tmpl, key) >= face_engine.MATCH_THRESHOLD for e in a[3:])
        assert all(bt.match(e, tmpl, key) < face_engine.MATCH_THRESHOLD for e in b)

    def test_revocation_and_unlinkability(self, lcc_embeddings):
        e = lcc_embeddings[0][0]
        k_old, k_new = bt.new_key(), bt.new_key()
        old = bt.protect(e, k_old)
        assert abs(float(np.dot(old, bt.protect(e, k_new)))) < 0.25      # same face, two keys: unrelated
        assert bt.match(e, old, k_new) < face_engine.MATCH_THRESHOLD      # leaked template useless after re-key


# ================================================================== 3. anti-spoofing + explanation

class TestAntiSpoofing:
    def test_deployed_model_and_threshold(self):
        info = fas_engine.model_info()
        assert info["model_path"] == "fas_v2.pth" and 0.05 < info["threshold"] < 0.95

    @needs_videos
    def test_webcam_real_passes_and_replay_blocked(self):
        for name, live in (("rwitankar_real_1", True), ("rwitankar_phone_1", False), ("rwitankar_phone_2", False)):
            frames = [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for i, f in enumerate(video_frames(name)) if i % 15 == 0][:10]
            r = fas_engine.assess_frames(frames)
            print(f"\n  {name}: median REAL {r['real_prob']:.2f} (thr {r['threshold']:.3f})")
            assert r["is_real"] is live

    def test_unseen_attempt_from_this_laptop(self):
        """A real login attempt captured after v4 was trained - never in any training set."""
        paths = sorted(glob.glob("data/captures/20261008-210638/crop_*.jpg"))
        if not paths:
            pytest.skip("capture not present")
        probs = fas_engine.score_crops([cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB) for p in paths])
        assert np.median(probs) >= fas_engine.model_info()["threshold"]

    def test_explanation_outputs(self):
        face = fas_engine.crop(lcc_subject("48", 1)[0])
        e = fas_engine.explain(face)
        assert e["gradcam_spatial"].shape == (224, 224, 3) and e["gradcam_freq"].shape == (224, 224, 3)
        assert e["gradcam_spatial"].std() > 5                              # a real map, not one flat value (v1 bug)
        assert e["predicted"] in ("REAL", "SPOOF") and 1.5 < e["fractal_dim"] < 3.0
        assert len(e["profile"]) == len(e["profile_freqs"]) and e["profile_ref"] is not None


# ================================================================== 4. active liveness on real recorded video

@pytest.fixture(scope="module")
def snaps():
    if not os.path.exists(f"{VIDEOS}/rwitankar_real_1.mp4"):
        pytest.skip("no webcam videos")
    s = {
        "enrol": run_liveness("rwitankar_real_3", ["BLINK", "BLINK"]),
        "login": run_liveness("rwitankar_real_1", ["BLINK", "BLINK"]),
        "replay_blink": run_liveness("rwitankar_phone_1", ["BLINK", "BLINK"]),
        "replay_turn": run_liveness("rwitankar_phone_2", ["BLINK", "TURN_LEFT"]),
    }
    for k, v in s.items():
        print(f"\n  liveness[{k}]: {v['state']} {[(r['name'], r['passed'], r['seconds']) for r in v['results']]}"
              f" {v['fail_reason'] or ''}")
    return s


class TestLivenessOnVideo:
    def test_live_video_passes_blink_challenges(self, snaps):
        for k in ("enrol", "login"):
            assert snaps[k]["state"] == "PASSED"
            assert len(snaps[k]["clean_frames"]) == le.CLEAN_FRAMES_KEPT
            assert snaps[k]["baseline"] is not None and snaps[k]["timeline"]

    def test_replayed_video_can_fool_blink_only(self, snaps):
        """Why passive anti-spoofing is needed: a replay of natural blinking satisfies a blink challenge."""
        assert snaps["replay_blink"]["state"] == "PASSED"

    def test_replayed_video_fails_random_second_challenge(self, snaps):
        r = snaps["replay_turn"]
        assert r["state"] == "FAILED" and "Turn your head LEFT" in r["fail_reason"]


class TestRecordedSwapAttack:
    """10 Oct: phone shown during calibration, then the real person performed the challenges - and it
    passed. The screen recording of that attempt is replayed through the processor at 15 fps with the
    video's own clock. Skipped where the (gitignored) recording is not present."""

    REC = "recordings/2026-10-10 22-08-25.mp4"

    @pytest.mark.skipif(not os.path.exists(REC), reason="screen recording not present")
    def test_phone_then_person_swap_is_blocked(self, monkeypatch):
        import types
        clock = {"t": 0.0}
        monkeypatch.setattr(le, "time", types.SimpleNamespace(time=lambda: clock["t"]))
        cap = cv2.VideoCapture(self.REC)
        cap.set(cv2.CAP_PROP_POS_MSEC, 64000)
        p = le.LivenessProcessor()
        p._t0 = 64.0
        p.challenges = ["LOOK_UP", "SMILE"]            # what the attempt was given
        i = 0
        while p.state not in ("PASSED", "FAILED"):
            ok, f = cap.read()
            if not ok or clock["t"] > 82:
                break
            i += 1
            if i % 4:
                continue
            clock["t"] = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            p.recv(av.VideoFrame.from_ndarray(f[520:1080, 504:1778].copy(), format="bgr24"))
        assert p.state == "FAILED" and "left the view" in p.fail_reason
        assert 69 < clock["t"] < 71                     # the moment the phone was taken away


# ================================================================== 5. database

class TestDatabase:
    def test_settlement_is_atomic_and_single_use(self):
        a, b = "db_a@test.local", "db_b@test.local"
        for u in (a, b):
            db.create_user(u, np.zeros(256, np.float32), bt.new_key(), generate_secret())
        db.create_transaction("TX-DB1", a, b, 1000.0, "PENDING")
        assert db.settle_transaction("TX-DB1")
        assert not db.settle_transaction("TX-DB1")                         # cannot settle twice
        assert db.get_balance(a) == db.STARTING_BALANCE - 1000 and db.get_balance(b) == db.STARTING_BALANCE + 1000
        db.create_transaction("TX-DB2", a, b, 10 ** 9, "PENDING")
        assert not db.settle_transaction("TX-DB2")
        assert db.get_balance(a) == db.STARTING_BALANCE - 1000             # nothing moved

    def test_otp_replay_protection(self):
        assert db.consume_otp_counter("r@test.local", "TX-9", 100)
        assert not db.consume_otp_counter("r@test.local", "TX-9", 100)     # same step again
        assert not db.consume_otp_counter("r@test.local", "TX-9", 99)      # older step
        assert db.consume_otp_counter("r@test.local", "TX-10", 100)        # other scope is independent

    def test_only_protected_template_is_stored(self):
        db.create_user("t@test.local", np.ones(256, np.float32), bt.new_key(), generate_secret())
        with sqlite3.connect(db.DB_PATH) as c:
            tmpl, key, secret = c.execute("SELECT template, template_key, otp_secret FROM users WHERE email=?",
                                          ("t@test.local",)).fetchone()
        assert len(tmpl) == 256 * 4                                         # 256-D float32, not the 512-D embedding
        assert key[:4] == b"gAAA" and secret[:4] == b"gAAA"                 # Fernet tokens: encrypted at rest


# ================================================================== 6. full app workflows (AppTest)

@pytest.fixture
def app(monkeypatch):
    import email_service
    monkeypatch.setattr(email_service, "send_code_email", lambda email, code: (False, "test: email disabled"))
    # the WebRTC widget needs a live browser session; tests hand recorded-video snapshots to the page instead
    import ui_components
    monkeypatch.setattr(ui_components, "liveness_camera", lambda key, state=None: None)
    # tests assume the default policy, whatever an operator saved in models/policy.json
    monkeypatch.setattr(fas_engine, "fas_enforced", lambda: True)
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=180)
    return at


URL_PATHS = {"home": "home", "login": "sign-in", "signup": "open-account", "dashboard": "accounts",
             "lab": "model-lab", "stepup": "verify-transfer", "pair": "pair-phone"}


def run(at):
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    # A browser stays on the page an st.switch_page moved it to; AppTest would replay the next
    # interaction on its starting page, so point it at the page that actually ran.
    from streamlit.navigation.page import calc_hash
    page = at.session_state["page"] if "page" in at.session_state else None
    if page in URL_PATHS:
        at._page_hash = calc_hash(URL_PATHS[page])
    return at


def texts(at):
    return " ".join(str(e.value) for kind in ("markdown", "success", "error", "warning", "info", "caption", "title", "header", "subheader")
                    for e in getattr(at, kind))


def button(at, label):
    for b in at.button:
        if b.label == label:
            return b
    raise AssertionError(f"no button {label!r}; have {[b.label for b in at.button]}")


def text_input(at, label):
    return next(t for t in at.text_input if t.label == label)


def inject_and_wait(at, state_key, snap, until, polls=60):
    """Hand a liveness snapshot to the page (as the camera would) and poll the background verification."""
    s = at.session_state[state_key]
    s["snap"] = snap
    at.session_state[state_key] = s
    for _ in range(polls):
        run(at)
        if until in texts(at) or any(b.label == until for b in at.button):
            return at
        time.sleep(0.5)
    raise AssertionError(f"timed out waiting for {until!r}: {texts(at)[:300]}")


def signup(at, email, snap):
    at.session_state["_goto"] = "signup"
    run(at)
    text_input(at, "Email address").set_value(email)
    button(at, "Send verification code").click()
    run(at)
    assert "Demo fallback" in texts(at)                         # SMTP mocked out -> code shown on screen
    code = at.session_state["signup"]["code"]
    text_input(at, "6-digit code").set_value("000000" if code != "000000" else "111111")
    button(at, "Verify email").click()
    run(at)
    assert "Wrong code" in texts(at)
    text_input(at, "6-digit code").set_value(code)
    button(at, "Verify email").click()
    run(at)
    assert at.session_state["signup"]["stage"] == "face"
    return inject_and_wait(at, "signup", snap, "Enrolment check")


def stepup(at, amount, payee="bob@vaulttrust.com"):
    at.session_state["_goto"] = "dashboard"
    run(at)
    next(sb for sb in at.selectbox if sb.label == "Payee").set_value(payee)
    at.number_input[0].set_value(float(amount))
    button(at, "Send").click()
    run(at)
    return at


USER = "rwitankar@test.local"


@needs_videos
class TestWorkflows:
    def test_1_signup_enrol_and_pair(self, app, snaps):
        at = signup(app, USER, snaps["enrol"])
        assert "Enrolment check: verified" in texts(at)
        button(at, "Continue to phone pairing").click()
        run(at)
        s = at.session_state["signup"]
        assert s["stage"] == "pair" and s["template"].shape == (256,)
        text_input(at, "Enter the code shown on your phone to confirm pairing").set_value("123456")
        button(at, "Confirm pairing").click()
        run(at)
        assert "does not match" in texts(at)
        code = generate_otp(s["secret"])[0]                     # what the paired phone displays
        text_input(at, "Enter the code shown on your phone to confirm pairing").set_value(code[:3] + " " + code[3:])
        button(at, "Confirm pairing").click()
        run(at)
        assert at.session_state["page"] == "dashboard" and at.session_state["user"] == USER
        u = db.get_user(USER)
        assert u["device_paired"] and u["balance"] == db.STARTING_BALANCE

    def test_2_login_with_face(self, app, snaps):
        app.session_state["_goto"] = "login"
        at = run(app)
        text_input(at, "Email").set_value(USER)
        button(at, "Continue").click()
        run(at)
        at = inject_and_wait(at, "login", snaps["login"], "Go to my account")
        assert "Sign-in: verified" in texts(at)
        button(at, "Go to my account").click()
        run(at)
        assert at.session_state["page"] == "dashboard"

    def test_3_low_value_transfer_is_instant(self, app):
        app.session_state["user"] = USER
        before = db.get_balance(USER)
        at = stepup(app, 250)
        assert at.session_state["page"] == "dashboard" and db.get_balance(USER) == before - 250

    def test_4_high_value_transfer_with_face_and_phone(self, app, snaps):
        app.session_state["user"] = USER
        before = db.get_balance(USER)
        at = stepup(app, 5000)
        assert at.session_state["page"] == "stepup"
        at = inject_and_wait(at, "stepup", snaps["login"], "Step 2 of 2")
        assert "Step-up presence check: verified" in texts(at)
        s = at.session_state["stepup"]
        k = db.get_user(USER)["otp_secret"]
        wrong = generate_otp(k, context=transaction_context(s["ref"], 5000.01, s["payee"]))[0]
        text_input(at, "Signing code from your phone").set_value(wrong)
        button(at, "Sign & send").click()
        run(at)
        assert "Code rejected (2 tries left)" in texts(at)
        right = generate_otp(k, context=transaction_context(s["ref"], 5000, s["payee"]))[0]
        text_input(at, "Signing code from your phone").set_value(right)
        button(at, "Sign & send").click()
        run(at)
        assert "sent to bob@vaulttrust.com" in texts(at)
        assert db.get_balance(USER) == before - 5000
        tx = next(t for t in db.get_transactions(USER) if t["ref"] == s["ref"])
        assert tx["status"] == "COMPLETED" and json.loads(tx["evidence"])["fas_real_prob"] > 0
        assert not db.consume_otp_counter(USER, s["ref"], int(time.time()) // 30)   # code cannot be replayed

    def test_5_attack_video_replay_blocked_by_anti_spoofing(self, app, snaps):
        """Replay passed the blink challenges; the CNN must still stop it."""
        app.session_state["user"] = USER
        before = db.get_balance(USER)
        at = stepup(app, 3000)
        at = inject_and_wait(at, "stepup", snaps["replay_blink"], "Step-up presence check: rejected")
        assert "Passive anti-spoofing scored" in texts(at)
        button(at, "Block this transfer").click()
        run(at)
        ref = at.session_state["stepup"]["ref"]
        assert next(t for t in db.get_transactions(USER) if t["ref"] == ref)["status"] == "BLOCKED_PRESENCE"
        assert db.get_balance(USER) == before

    def test_6_attack_replay_fails_random_challenge(self, app, snaps):
        app.session_state["user"] = USER
        at = stepup(app, 2000)
        at = inject_and_wait(at, "stepup", snaps["replay_turn"], "Step-up presence check: rejected")
        assert "Active liveness failed" in texts(at)

    def test_7_attack_different_person(self, app, snaps):
        """A live, genuine face - just not the account owner's."""
        app.session_state["user"] = USER
        impostor = dict(snaps["login"], clean_frames=lcc_subject("48", 6))
        at = stepup(app, 2000)
        at = inject_and_wait(at, "stepup", impostor, "Step-up presence check: rejected")
        assert "Face does not match this account" in texts(at)

    def test_8_attack_wrong_codes_lock_transfer(self, app, snaps):
        app.session_state["user"] = USER
        before = db.get_balance(USER)
        at = stepup(app, 1500)
        at = inject_and_wait(at, "stepup", snaps["login"], "Step 2 of 2")
        for code in ("111111", "222222", "333333"):
            text_input(at, "Signing code from your phone").set_value(code)
            button(at, "Sign & send").click()
            run(at)
        assert "3 wrong signing codes" in texts(at)
        ref = at.session_state["stepup"]["ref"]
        assert next(t for t in db.get_transactions(USER) if t["ref"] == ref)["status"] == "BLOCKED_OTP"
        assert db.get_balance(USER) == before

    def test_9_attack_enrol_with_replay(self, app, snaps):
        at = signup(app, "attacker@test.local", snaps["replay_blink"])
        assert "Enrolment check: rejected" in texts(at)
        assert not db.user_exists("attacker@test.local")

    def test_10_advisory_policy_passes_with_warning(self, app, snaps, monkeypatch):
        monkeypatch.setattr(fas_engine, "fas_enforced", lambda: False)
        at = signup(app, "advisory@test.local", snaps["replay_blink"])
        assert "Enrolment check: verified" in texts(at) and "Advisory policy" in texts(at)

    def test_11_security_log_records_everything(self):
        events = {e["event"] for e in db.get_audit(USER, limit=100)}
        assert {"ACCOUNT_CREATED", "LOGIN_OK", "TRANSFER_COMPLETED", "STEP_UP_REQUIRED", "STEP_UP_PRESENCE_OK",
                "STEP_UP_PRESENCE_REJECTED", "OTP_REJECTED"} <= events

    def test_12_dashboard_and_model_lab_render(self, app):
        if not db.user_exists(USER):
            db.create_user(USER, np.zeros(256, np.float32), bt.new_key(), generate_secret())
        app.session_state["user"] = USER
        app.session_state["_goto"] = "dashboard"
        at = run(app)
        assert "Accounts" in texts(at) and len(at.metric) >= 3
        for section in (":material/blur_on: Anti-spoofing", ":material/hub: Random-walk OTP",
                        ":material/fingerprint: Cancelable template"):
            at.session_state["_goto"] = "lab"
            at.session_state["lab_section"] = section
            run(at)
            assert "Model Lab" in texts(at)
        at.session_state["lab_section"] = ":material/blur_on: Anti-spoofing"
        for view in ("Webcam - unseen person (deployment camera)", "LCC-FASD - unseen subjects (public dataset)"):
            at.session_state["op_set"] = view
            run(at)
            assert len(at.metric) >= 3

    def test_13_deleted_account_session_recovers(self, app):
        app.session_state["user"] = "ghost@test.local"
        app.session_state["_goto"] = "dashboard"
        at = run(app)
        assert at.session_state["page"] == "home" and at.session_state["user"] is None

    def test_14_switch_account_everywhere(self, app):
        if not db.user_exists(USER):
            db.create_user(USER, np.zeros(256, np.float32), bt.new_key(), generate_secret())
        app.session_state["_goto"] = "login"
        at = run(app)
        text_input(at, "Email").set_value(USER)
        button(at, "Continue").click()
        run(at)
        assert "Account:" in texts(at)
        button(at, "Use a different account").click()
        run(at)
        assert any(t.label == "Email" for t in at.text_input)            # back to choosing the account
        button(at, "Open an account instead").click()
        run(at)
        assert at.session_state["page"] == "signup"
        button(at, "Sign in instead").click()
        run(at)
        assert at.session_state["page"] == "login"
        button(at, "Back").click()
        run(at)
        assert at.session_state["page"] == "home"
        at.session_state["user"] = USER
        run(at)
        button(at, "Switch account").click()                             # from home while signed in
        run(at)
        assert at.session_state["page"] == "login" and at.session_state["user"] is None
        at.session_state["user"] = USER
        at.session_state["_goto"] = "dashboard"
        run(at)
        button(at, "Switch account").click()                             # from the Accounts page
        run(at)
        assert at.session_state["page"] == "login" and at.session_state["user"] is None

    def test_15_signup_can_restart_with_another_email(self, app, snaps):
        at = signup(app, "first-try@test.local", snaps["enrol"])
        button(at, "Start over with a different email").click()
        run(at)
        assert at.session_state["page"] == "signup" and at.session_state["signup"]["stage"] == "email"

    def test_16_expired_codes_rejected(self, app, snaps):
        """A code older than the 10 s grace period is refused with an 'expired' message."""
        at = signup(app, "expiry@test.local", snaps["enrol"])
        button(at, "Continue to phone pairing").click()
        run(at)
        secret = at.session_state["signup"]["secret"]
        stale = generate_otp(secret, counter=int(time.time()) // 30 - 2)[0]     # 30-60 s past expiry
        text_input(at, "Enter the code shown on your phone to confirm pairing").set_value(stale)
        button(at, "Confirm pairing").click()
        run(at)
        assert "That code has expired" in texts(at) and not db.user_exists("expiry@test.local")

        at.session_state["user"] = USER
        db.set_device_paired(USER)
        at = stepup(at, 1200)
        at = inject_and_wait(at, "stepup", snaps["login"], "Step 2 of 2")
        s = at.session_state["stepup"]
        k = db.get_user(USER)["otp_secret"]
        stale = generate_otp(k, counter=int(time.time()) // 30 - 2,
                             context=transaction_context(s["ref"], 1200, s["payee"]))[0]
        text_input(at, "Signing code from your phone").set_value(stale)
        button(at, "Sign & send").click()
        run(at)
        assert "That code has expired (2 tries left)" in texts(at)

    def test_17_repair_after_network_change_mid_transfer(self, app, snaps):
        """Phone paired on another network: the transfer screen says so, re-pairing rotates the key, transfer completes."""
        app.session_state["user"] = USER
        old_secret = db.get_user(USER)["otp_secret"]
        db.set_device_paired(USER, host="10.38.232.183")                 # paired yesterday, other network
        before = db.get_balance(USER)
        at = stepup(app, 2500)
        at = inject_and_wait(at, "stepup", snaps["login"], "Step 2 of 2")
        assert "Your phone was paired while the laptop's address was **10.38.232.183**" in texts(at)
        button(at, "Re-pair my phone").click()
        run(at)
        assert at.session_state["page"] == "pair"
        assert "Step 1 of 2" not in texts(at)                            # face check just passed: reused
        new_secret = at.session_state["repair"]["secret"]
        assert new_secret != old_secret
        text_input(at, "Enter the code shown on your phone to confirm pairing").set_value(generate_otp(new_secret)[0])
        button(at, "Confirm pairing").click()
        run(at)
        assert at.session_state["page"] == "stepup"                      # back to the waiting transfer
        u = db.get_user(USER)
        assert u["otp_secret"] == new_secret and u["paired_host"] not in (None, "10.38.232.183")
        assert "Your phone was paired while" not in texts(at)
        s = at.session_state["stepup"]
        ctx = transaction_context(s["ref"], 2500, s["payee"])
        text_input(at, "Signing code from your phone").set_value(generate_otp(old_secret, context=ctx)[0])
        button(at, "Sign & send").click()
        run(at)
        assert "Code rejected" in texts(at)                              # the old phone's key no longer works
        text_input(at, "Signing code from your phone").set_value(generate_otp(new_secret, context=ctx)[0])
        button(at, "Sign & send").click()
        run(at)
        assert "sent to" in texts(at) and db.get_balance(USER) == before - 2500
        assert "AUTHENTICATOR_REPAIRED" in {e["event"] for e in db.get_audit(USER, limit=200)}

    def test_18_repair_from_accounts_needs_a_face_check(self, app, snaps):
        app.session_state["user"] = USER
        app.session_state.pop("last_presence") if "last_presence" in app.session_state else None
        app.session_state["_goto"] = "dashboard"
        at = run(app)
        assert "Your authenticator" in texts(at)
        button(at, "Pair a new phone").click()
        run(at)
        assert at.session_state["page"] == "pair" and "Step 1 of 2" in texts(at)
        impostor = dict(snaps["login"], clean_frames=lcc_subject("48", 6))
        at = inject_and_wait(at, "repair", impostor, "Re-pairing check: rejected")
        assert "Face does not match this account" in texts(at)            # nobody else can swap the phone
        assert "secret" not in at.session_state["repair"]
        button(at, "Back").click()
        run(at)
        assert at.session_state["page"] == "dashboard"

    def test_19_pending_transfer_survives_leaving_the_page(self, app):
        app.session_state["user"] = USER
        at = stepup(app, 1800)
        assert at.session_state["page"] == "stepup"
        button(at, "Back to accounts").click()
        run(at)
        assert at.session_state["page"] == "dashboard" and "is waiting for verification" in texts(at)
        button(at, "Continue").click()
        run(at)
        assert at.session_state["page"] == "stepup"
        button(at, "Back to accounts").click()
        run(at)
        ref = at.session_state["stepup"]["ref"]
        button(at, "Cancel it").click()
        run(at)
        assert next(t for t in db.get_transactions(USER) if t["ref"] == ref)["status"] == "CANCELLED"
