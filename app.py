"""
VaultTrust - step-up authentication for high-value transfers.

    streamlit run app.py

Factors
  * inherence  - face: active liveness + passive spatial/frequency
                 anti-spoofing + ArcFace match on a cancelable template
  * possession - phone authenticator computing random-walk OTPs offline,
                 bound to the exact transaction (dynamic linking)

Pages live at their own addresses (st.navigation), so the browser's back
and forward buttons move between them.
"""

import base64
import faulthandler
import io
import json
import os
import secrets
import socket
import sys
import time

import qrcode
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "semprojOTP", "otp_system"))

import authenticator_server  # noqa: E402
import biometric_template  # noqa: E402
import database as db  # noqa: E402
import model_lab  # noqa: E402
from email_service import send_code_email  # noqa: E402
from ui_components import evidence_card, presence_step  # noqa: E402
from walk_otp import generate_secret, otp_age, secret_to_b32, transaction_context, verify_otp  # noqa: E402

os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), exist_ok=True)
if not faulthandler.is_enabled():
    # native crashes (MediaPipe / ONNX / PyAV) leave no Python traceback; keep their stacks here
    faulthandler.enable(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "crash.log"), "a"),
                        all_threads=True)

STEP_UP_LIMIT = 1_000.0
MAX_OTP_ATTEMPTS = 3
# An expired code stays usable only this long (typing time); RFC 6238's full ±1 step allowed 30 s more.
OTP_GRACE_SECONDS = 10
# A passed face check this recent also authorises re-pairing a phone (no second camera round).
PRESENCE_REUSE_SECONDS = 180

st.set_page_config(page_title="VaultTrust", page_icon=":material/shield_lock:", layout="wide")
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_resource
def _start_authenticator():
    return authenticator_server.start_server()


_start_authenticator()


@st.cache_resource
def _warm_models():
    """
    Load MediaPipe, the anti-spoofing CNN and ArcFace in the background at startup, and run each once on
    a blank image: the first inference sets up XNNPACK / PyTorch / ONNX Runtime and is several times
    slower than later ones. MediaPipe goes first because the camera needs it.
    """
    import logging
    import threading

    import numpy as np

    def load():
        t0 = time.time()
        import face_engine
        import fas_engine
        import liveness_engine
        blank = np.full((480, 640, 3), 128, np.uint8)
        liveness_engine.measure(blank)
        fas_engine.score_crops([blank[:224, :224]])
        face_engine.embed(blank)
        logging.getLogger("vaulttrust.liveness").info("models warmed up in %.1fs", time.time() - t0)

    threading.Thread(target=load, daemon=True).start()
    return True


_warm_models()

ss = st.session_state
ss.setdefault("user", None)


def go(page, **reset):
    """Move to another page (a real navigation: the browser can go back to this one)."""
    for k in reset:
        ss.pop(k, None)
    st.switch_page(PAGES[page])


def money(x):
    return f"${x:,.2f}"


def _note_presence(email, v):
    if v and v["passed"]:
        ss.last_presence = {"email": email, "at": time.time()}


def _recent_presence(email):
    lp = ss.get("last_presence")
    return bool(lp and lp["email"] == email and time.time() - lp["at"] < PRESENCE_REUSE_SECONDS)


# ------------------------------------------------------------------ authenticator links

def _candidate_hosts():
    """Route-detected Wi-Fi/hotspot address first; other adapters (WSL, VPN, Docker) after it."""
    primary = authenticator_server.lan_ip()
    others = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            others.add(info[4][0])
    except OSError:
        pass
    hosts = [primary] + sorted(others - {primary})
    return [h for h in hosts if not h.startswith("127.")]


def current_host():
    return ss.get("auth_host") or authenticator_server.lan_ip()


def auth_url(fragment: str, host: str | None = None) -> str:
    return authenticator_server.base_url(host or current_host()) + "#" + fragment


def qr_data_uri(url: str) -> str:
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def show_qr(url: str, local_url: str, caption: str, pairing: bool = False):
    a, b = st.columns([1, 1.4], vertical_alignment="center")
    # Embedded in the page itself: a media-file image can vanish if a rerun lands while it loads.
    a.html(f'<img src="{qr_data_uri(url)}" width="240" height="240" alt="QR code for the phone authenticator" '
           f'style="border-radius:12px;background:#fff">')
    with b:
        st.markdown(caption)
        st.caption("Scan with the phone camera (phone and laptop on the same Wi-Fi / hotspot).")
        st.code(url.split("#")[0], language=None)
        st.link_button("No phone? Open the authenticator on this laptop", local_url,
                       icon=":material/open_in_new:")
        if pairing:
            st.caption("Opening that link here pairs this laptop's browser too, with the same key.")
        else:
            st.caption("The laptop link works only if this laptop's browser was paired from a pairing screen.")


def phone_pairing_help(user, back_to: str, offer_button: bool = True):
    """Explain why a phone may say 'not paired' and offer re-pairing."""
    now_host = current_host()
    if user.get("paired_host") and user["paired_host"] != now_host:
        st.warning(f"Your phone was paired while the laptop's address was **{user['paired_host']}**. It is now "
                   f"**{now_host}**. A phone keeps its key per address, so it will say *not paired*. "
                   "Re-pair it (about 20 seconds), or put the laptop back on that network.",
                   icon=":material/wifi_find:")
        if offer_button and st.button("Re-pair my phone", type="primary", icon=":material/smartphone:",
                                      key=f"repair-{back_to}"):
            ss.return_to = back_to
            go("pair", repair=None)
        return
    with st.expander("Phone says *not paired*, or codes are wrong?", icon=":material/help:"):
        st.markdown("A phone keeps its key per laptop address (the IP in the QR code). If the laptop changed "
                    "network since you paired, the phone cannot see the key. Pairing again issues a new key; "
                    "old phones stop working.")
        if offer_button and st.button("Re-pair my phone", icon=":material/smartphone:", key=f"repair-{back_to}"):
            ss.return_to = back_to
            go("pair", repair=None)


# ================================================================== pages

def _switch_links(where: str):
    """Ways out of a sign-in / sign-up flow: the other flow, or back home."""
    a, b, _ = st.columns([1.3, 1, 2])
    if where == "signup":
        if a.button("Sign in instead", icon=":material/login:", width="stretch"):
            go("login", signup=None, login=None)
    else:
        if a.button("Open an account instead", icon=":material/person_add:", width="stretch"):
            go("signup", signup=None, login=None)
    if b.button("Back", icon=":material/arrow_back:", width="stretch"):
        go("home", signup=None, login=None)


def _start_over(where: str, label: str):
    if st.button(label, icon=":material/swap_horiz:", key=f"start-over-{where}"):
        go(where, **{where: None})


def page_home():
    st.markdown("<div class='hero'><h1>VaultTrust</h1><p>Banking where large transfers need <b>you</b>, "
                "live, and <b>your phone</b> - not just a password.</p></div>", unsafe_allow_html=True)
    if ss.user:
        st.info(f"Signed in as **{ss.user}**.", icon=":material/account_circle:")
        c, d = st.columns(2)
        if c.button("Go to my accounts", type="primary", icon=":material/account_balance:", width="stretch"):
            go("dashboard")
        if d.button("Switch account", icon=":material/swap_horiz:", width="stretch"):
            ss.user = None
            go("login", login=None)
    a, b = st.columns(2)
    if a.button("Open an account", type="primary" if not ss.user else "secondary",
                icon=":material/person_add:", width="stretch"):
        go("signup", signup=None)
    if b.button("Sign in with your face", icon=":material/face:", width="stretch"):
        go("login", login=None)

    st.markdown("#### How a high-value transfer is protected")
    c = st.columns(4)
    steps = [
        (":material/directions_run:", "Active liveness", "Two random challenges (blink, turn, smile, look up), "
                                                          "judged against your own neutral pose."),
        (":material/blur_on:", "Passive anti-spoofing", "Dual-branch CNN on RGB + FFT spectrum over 10 frames; "
                                                        "explained with Grad-CAM and frequency evidence."),
        (":material/fingerprint:", "Cancelable face template", "ArcFace embedding protected by a chaotic-map "
                                                               "projection; matched without storing your face."),
        (":material/hub:", "Random-walk OTP", "Your phone walks a 64-node graph seeded by HMAC(K, time, "
                                              "transaction) - the code only works for that transfer."),
    ]
    for col, (icon, title, text) in zip(c, steps):
        with col.container(border=True):
            st.markdown(f"**{icon} {title}**")
            st.caption(text)


# ------------------------------------------------------------------ sign up

def page_signup():
    s = ss.get("signup") or {"stage": "email", "attempt": 0}
    ss.signup = s
    st.title("Open an account")
    if ss.user and s["stage"] == "email":
        st.info(f"You are signed in as **{ss.user}**. Opening another account signs you in to the new one.",
                icon=":material/account_circle:")
    stages = ["email", "face", "pair"]
    st.progress((stages.index(s["stage"]) + 1) / 3,
                text=["1 · Verify email", "2 · Enrol your face", "3 · Pair your phone"][stages.index(s["stage"])])

    if s["stage"] == "email":
        email = st.text_input("Email address", value=s.get("email", ""),
                              disabled=bool(s.get("code"))).strip().lower()
        if s.get("code"):
            if st.button("Use a different email", icon=":material/swap_horiz:"):
                ss.signup = None
                st.rerun()
        elif st.button("Send verification code", type="primary"):
            if "@" not in email or "." not in email.split("@")[-1]:
                st.error("Enter a valid email address.")
            elif db.user_exists(email):
                st.error("An account with this email already exists. Sign in instead.")
            else:
                s.update(email=email, code=f"{secrets.randbelow(10 ** 6):06d}", code_at=time.time(), tries=0)
                with st.spinner("Sending..."):
                    sent, err = send_code_email(email, s["code"])
                s["sent"], s["send_error"] = sent, err
        if s.get("code"):
            if s["sent"]:
                st.success(f"Code sent to {s['email']}.")
            else:
                st.warning(f"Email could not be sent ({s['send_error']}). Demo fallback - your code is "
                           f"**{s['code']}**.")
            entered = st.text_input("6-digit code", max_chars=6)
            if st.button("Verify email"):
                s["tries"] += 1
                if time.time() - s["code_at"] > 600 or s["tries"] > 5:
                    st.error("Code expired or too many attempts. Send a new code.")
                    s.pop("code")
                elif entered.strip() == s["code"]:
                    s["stage"] = "face"
                    st.rerun()
                else:
                    st.error("Wrong code.")
        _switch_links("signup")

    elif s["stage"] == "face":
        st.caption(f"Enrolling **{s['email']}**")
        _start_over("signup", "Start over with a different email")
        st.markdown("Look at the camera. We calibrate to your face, then ask for **two random actions**. "
                    "Your raw face data is never stored - only a cancelable template.")
        v = presence_step(s, f"enrol-{s['attempt']}", None,
                          "Checking for spoofing and building your protected template...")
        if v is not None:
            evidence_card(v, "Enrolment check")
            if v["passed"]:
                if st.button("Continue to phone pairing", type="primary", icon=":material/arrow_forward:"):
                    s["template_key"] = biometric_template.new_key()
                    s["template"] = biometric_template.protect(v["embedding"], s["template_key"])
                    s["secret"] = generate_secret()
                    s["stage"] = "pair"
                    s["pair_tries"] = 0
                    s.pop("verification")
                    st.rerun()
            else:
                db.audit(s["email"], "ENROLMENT_REJECTED", {"reasons": v["reasons"]})
                if st.button("Try again", icon=":material/refresh:"):
                    s["attempt"] += 1
                    s.pop("verification")
                    st.rerun()

    elif s["stage"] == "pair":
        st.caption(f"Pairing a phone for **{s['email']}**")
        _start_over("signup", "Start over with a different email")
        b32 = secret_to_b32(s["secret"])
        frag = f"pair={b32}&u={s['email']}"
        show_qr(auth_url(frag), auth_url(frag, "localhost"),
                "**Pair your phone.** The QR code carries your secret key **once**. After this, "
                "the phone computes codes on its own - nothing is sent over the network.", pairing=True)
        code = st.text_input("Enter the code shown on your phone to confirm pairing", max_chars=7)
        if st.button("Confirm pairing", type="primary"):
            s["pair_tries"] += 1
            ok, counter = verify_otp(s["secret"], code.replace(" ", ""), grace_seconds=OTP_GRACE_SECONDS)
            if s["pair_tries"] > 5:
                st.error("Too many attempts. Start again.")
                ss.signup = None
            elif ok:
                db.create_user(s["email"], s["template"], s["template_key"], s["secret"])
                db.set_device_paired(s["email"], host=current_host())
                db.consume_otp_counter(s["email"], "login", counter)
                db.audit(s["email"], "ACCOUNT_CREATED", {"device_paired": True, "paired_host": current_host()})
                ss.user = s["email"]
                ss.signup = None
                st.toast("Account created", icon=":material/celebration:")
                go("dashboard")
            elif otp_age(s["secret"], code.replace(" ", "")):
                st.error("That code has expired. Type the code the phone shows now.")
            else:
                st.error("That code does not match. Check the phone shows your email and try the current code.")


# ------------------------------------------------------------------ sign in

def page_login():
    s = ss.get("login") or {"attempt": 0}
    ss.login = s
    st.title("Sign in")
    if not s.get("email"):
        if ss.user:
            st.info(f"You are signed in as **{ss.user}**. Enter another email to switch.",
                    icon=":material/account_circle:")
            if st.button("Go to my accounts", icon=":material/account_balance:"):
                go("dashboard")
        email = st.text_input("Email").strip().lower()
        if st.button("Continue", type="primary"):
            if db.user_exists(email):
                s["email"] = email
                st.rerun()
            else:
                st.error("No account with that email.")
        _switch_links("login")
        return

    user = db.get_user(s["email"])
    if user is None:  # account deleted meanwhile
        ss.login = None
        st.rerun()
    a, b = st.columns([3, 1.2], vertical_alignment="center")
    a.caption(f"Account: **{s['email']}**")
    if b.button("Use a different account", icon=":material/swap_horiz:", width="stretch"):
        ss.login = None
        st.rerun()
    v = presence_step(s, f"login-{s['attempt']}", user)
    if v is not None:
        if not s.get("audited"):
            s["audited"] = True
            _note_presence(s["email"], v)
            db.audit(s["email"], "LOGIN_OK" if v["passed"] else "LOGIN_REJECTED",
                     {"fas": round(v["fas"]["real_prob"], 3), "match": v["match_score"], "reasons": v["reasons"]})
        evidence_card(v, "Sign-in")
        if v["passed"]:
            if st.button("Go to my account", type="primary", icon=":material/arrow_forward:"):
                ss.user = s["email"]
                ss.login = None
                go("dashboard")
        elif st.button("Try again", icon=":material/refresh:"):
            s["attempt"] += 1
            s.pop("verification")
            s.pop("audited", None)
            st.rerun()


# ------------------------------------------------------------------ dashboard

STATUS_LABEL = {
    "COMPLETED": ":green[completed]", "PENDING_STEP_UP": ":orange[awaiting verification]",
    "BLOCKED_PRESENCE": ":red[blocked - presence check]", "BLOCKED_OTP": ":red[blocked - wrong codes]",
    "CANCELLED": ":gray[cancelled]", "FAILED_FUNDS": ":red[insufficient funds]",
}


def page_dashboard():
    user = db.get_user(ss.user) if ss.user else None
    if user is None:  # signed out, or the account no longer exists
        ss.user = None
        go("home")
    t, sw = st.columns([4, 1], vertical_alignment="bottom")
    t.title("Accounts")
    if sw.button("Switch account", icon=":material/swap_horiz:", width="stretch"):
        ss.user = None
        ss.stepup = None
        go("login", login=None)

    pending = ss.get("stepup")
    if pending and not pending.get("done") and not pending.get("blocked"):
        a, b, c = st.columns([3, 1, 1], vertical_alignment="center")
        a.warning(f"**{money(pending['amount'])} to {pending['payee']}** ({pending['ref']}) is waiting for "
                  "verification.", icon=":material/pending:")
        if b.button("Continue", type="primary", width="stretch"):
            go("stepup")
        if c.button("Cancel it", width="stretch"):
            db.set_transaction_status(pending["ref"], "CANCELLED")
            ss.stepup = None
            st.rerun()

    a, b, c = st.columns(3)
    a.metric("Available balance", money(user["balance"]))
    b.metric("Step-up limit", money(STEP_UP_LIMIT), "face + phone above this", delta_color="off")
    c.metric("Authenticator", "paired" if user["device_paired"] else "not paired",
             f"at {user['paired_host']}" if user.get("paired_host") else None, delta_color="off")

    left, right = st.columns([1, 1.25], gap="large")
    with left:
        with st.container(border=True):
            st.subheader("Send money")
            others = [u for u in _known_payees() if u != ss.user]
            payee = st.selectbox("Payee", others + ["Someone else..."])
            if payee == "Someone else...":
                payee = st.text_input("Payee email").strip().lower()
            amount = st.number_input("Amount ($)", min_value=1.0, value=250.0, step=50.0)
            if amount >= STEP_UP_LIMIT:
                st.info("High-value transfer: you will verify your face and approve on your phone.",
                        icon=":material/shield:")
            if st.button("Send", type="primary", icon=":material/send:", width="stretch"):
                if not payee or "@" not in payee:
                    st.error("Choose a payee.")
                elif amount > user["balance"]:
                    st.error("Insufficient funds.")
                else:
                    ref = "TX-" + secrets.token_hex(3).upper()
                    db.create_transaction(ref, ss.user, payee, float(amount),
                                          "PENDING_STEP_UP" if amount >= STEP_UP_LIMIT else "PENDING")
                    if amount >= STEP_UP_LIMIT:
                        db.audit(ss.user, "STEP_UP_REQUIRED", {"ref": ref, "amount": amount, "payee": payee})
                        ss.stepup = {"ref": ref, "amount": float(amount), "payee": payee, "attempt": 0,
                                     "otp_tries": 0}
                        go("stepup")
                    elif db.settle_transaction(ref):
                        db.audit(ss.user, "TRANSFER_COMPLETED", {"ref": ref, "amount": amount, "step_up": False})
                        st.toast(f"Sent {money(amount)} to {payee}", icon=":material/check:")
                        time.sleep(0.6)
                        st.rerun()
                    else:
                        st.error("Transfer failed.")
        with st.container(border=True):
            st.subheader("Your authenticator")
            if user.get("paired_at"):
                st.caption(f"Paired {time.strftime('%d %b %H:%M', time.localtime(user['paired_at']))} at "
                           f"`{user['paired_host']}`")
            phone_pairing_help(user, "dashboard", offer_button=False)
            if st.button("Pair a new phone", icon=":material/smartphone:"):
                ss.return_to = "dashboard"
                go("pair", repair=None)

    with right:
        t1, t2 = st.tabs(["Transactions", "Security log"])
        with t1:
            txs = db.get_transactions(ss.user)
            if not txs:
                st.caption("No transactions yet.")
            for tx in txs:
                out = tx["sender"] == ss.user
                who = tx["receiver"] if out else tx["sender"]
                sign = "−" if out else "+"
                st.markdown(f"**{sign}{money(tx['amount'])}** {'to' if out else 'from'} {who}  \n"
                            f"<span class='small'>{tx['ref']} · {time.strftime('%d %b %H:%M', time.localtime(tx['created_at']))}"
                            f"</span> · {STATUS_LABEL.get(tx['status'], tx['status'])}", unsafe_allow_html=True)
        with t2:
            for ev in db.get_audit(ss.user):
                detail = json.loads(ev["detail"]) if ev["detail"] else {}
                st.markdown(f"`{time.strftime('%H:%M:%S', time.localtime(ev['created_at']))}` **{ev['event']}**  \n"
                            f"<span class='small'>{_short(detail)}</span>", unsafe_allow_html=True)


def _short(d):
    keep = {k: v for k, v in d.items() if k != "reasons"}
    text = ", ".join(f"{k}={v}" for k, v in keep.items())
    if d.get("reasons"):
        text += (" · " if text else "") + d["reasons"][0]
    return text


def _known_payees():
    import sqlite3
    with sqlite3.connect(db.DB_PATH) as c:
        users = [r[0] for r in c.execute("SELECT email FROM users ORDER BY created_at")]
    return users + ["alice@vaulttrust.com", "bob@vaulttrust.com"]


# ------------------------------------------------------------------ re-pair a phone

def page_pair():
    user = db.get_user(ss.user) if ss.user else None
    if user is None:
        go("home")
    back_to = ss.get("return_to", "dashboard")
    s = ss.get("repair") or {"attempt": 0, "tries": 0}
    ss.repair = s
    st.title("Pair a phone")
    st.caption(f"Account: **{ss.user}** · pairing issues a new key, so any phone or browser paired before stops "
               "working.")
    if st.button("Back", icon=":material/arrow_back:"):
        ss.repair = None
        go(back_to)

    # 1. a fresh face check (reused if one passed in the last few minutes)
    if not _recent_presence(ss.user):
        st.markdown("**Step 1 of 2 - confirm it's you.** Changing the phone that approves your transfers needs "
                    "the same face check as a transfer.")
        v = presence_step(s, f"repair-{s['attempt']}", user, "Verifying...")
        if v is None:
            return
        _note_presence(ss.user, v)
        if not v["passed"]:
            evidence_card(v, "Re-pairing check")
            db.audit(ss.user, "REPAIR_REJECTED", {"reasons": v["reasons"]})
            if st.button("Try again", icon=":material/refresh:"):
                s["attempt"] += 1
                s.pop("verification")
                st.rerun()
            return
        st.rerun()

    # 2. show the new key once; confirm with the first code
    st.markdown("**Step 2 of 2 - scan with the phone.**")
    s.setdefault("secret", generate_secret())
    frag = f"pair={secret_to_b32(s['secret'])}&u={ss.user}"
    show_qr(auth_url(frag), auth_url(frag, "localhost"),
            f"**Pair a phone for {ss.user}.** The QR code carries the new key **once**.", pairing=True)
    code = st.text_input("Enter the code shown on your phone to confirm pairing", max_chars=7)
    if st.button("Confirm pairing", type="primary"):
        s["tries"] += 1
        ok, counter = verify_otp(s["secret"], code.replace(" ", ""), grace_seconds=OTP_GRACE_SECONDS)
        if s["tries"] > 5:
            st.error("Too many attempts. Start again.")
            ss.repair = None
        elif ok:
            db.replace_otp_secret(ss.user, s["secret"], current_host())
            db.consume_otp_counter(ss.user, "login", counter)
            db.audit(ss.user, "AUTHENTICATOR_REPAIRED", {"paired_host": current_host()})
            ss.repair = None
            st.toast("Phone paired", icon=":material/smartphone:")
            go(back_to)
        elif otp_age(s["secret"], code.replace(" ", "")):
            st.error("That code has expired. Type the code the phone shows now.")
        else:
            st.error("That code does not match. Check the phone shows your email and try the current code.")


# ------------------------------------------------------------------ step-up

def page_stepup():
    s = ss.get("stepup")
    user = db.get_user(ss.user) if ss.user else None
    if not s or user is None:
        go("dashboard")
    t, back = st.columns([4, 1], vertical_alignment="bottom")
    t.title("Verify this transfer")
    if not s.get("done") and not s.get("blocked") and back.button("Back to accounts", icon=":material/arrow_back:",
                                                                  width="stretch"):
        go("dashboard")      # the transfer stays pending; the Accounts page offers to continue or cancel it
    with st.container(border=True):
        a, b, c = st.columns(3)
        a.metric("Amount", money(s["amount"]))
        b.metric("To", s["payee"])
        c.metric("Reference", s["ref"])

    if s.get("done"):
        st.success(f"**{money(s['amount'])} sent to {s['payee']}.** Signed with your face and your phone.",
                   icon=":material/task_alt:")
        if st.button("Back to accounts", type="primary"):
            ss.stepup = None
            go("dashboard")
        return

    if s.get("blocked"):
        st.error(f"Transfer blocked: {s['blocked']}", icon=":material/block:")
        if s.get("verification"):
            evidence_card(s["verification"], "Step-up presence check")
        if st.button("Back to accounts"):
            ss.stepup = None
            go("dashboard")
        return

    # 1. presence
    if s.get("verification") is None:
        st.markdown("**Step 1 of 2 - prove it's really you, right now.** A stolen password or hijacked session "
                    "is not enough to move this much money.")
        presence_step(s, f"stepup-{s['ref']}-{s['attempt']}", user, "Running anti-spoofing and face match...")
        if st.button("Cancel transfer"):
            db.set_transaction_status(s["ref"], "CANCELLED")
            ss.stepup = None
            go("dashboard")
        return

    v = s["verification"]
    if not s.get("audited"):
        s["audited"] = True
        _note_presence(ss.user, v)
        db.audit(ss.user, "STEP_UP_PRESENCE_OK" if v["passed"] else "STEP_UP_PRESENCE_REJECTED",
                 {"ref": s["ref"], "fas": round(v["fas"]["real_prob"], 3), "match": v["match_score"],
                  "reasons": v["reasons"]})
    evidence_card(v, "Step-up presence check")
    if not v["passed"]:
        a, b = st.columns(2)
        if s["attempt"] < 2 and a.button("Try again", icon=":material/refresh:"):
            s["attempt"] += 1
            s.pop("verification")
            s.pop("audited", None)
            st.rerun()
        if b.button("Block this transfer", type="primary"):
            db.set_transaction_status(s["ref"], "BLOCKED_PRESENCE", _evidence_json(v))
            s["blocked"] = "presence verification failed. The attempt is in your security log."
            st.rerun()
        return

    # 2. possession + dynamic linking
    st.markdown("**Step 2 of 2 - approve on your phone.** The phone shows the amount and payee and computes a "
                "code from them. A code for any other amount or payee will not work.")
    phone_pairing_help(user, "stepup")
    tx = {"id": s["ref"], "a": s["amount"], "p": s["payee"], "u": ss.user}
    frag = "tx=" + base64.urlsafe_b64encode(json.dumps(tx).encode()).decode().rstrip("=")
    show_qr(auth_url(frag), auth_url(frag, "localhost"), f"**Approve {money(s['amount'])} to {s['payee']}**")
    code = st.text_input("Signing code from your phone", max_chars=7)
    if st.button("Sign & send", type="primary", icon=":material/draw:"):
        ctx = transaction_context(s["ref"], s["amount"], s["payee"])
        ok, counter = verify_otp(user["otp_secret"], code.replace(" ", ""), context=ctx,
                                 grace_seconds=OTP_GRACE_SECONDS)
        if ok and db.consume_otp_counter(ss.user, s["ref"], counter):
            if db.settle_transaction(s["ref"]):
                db.set_transaction_status(s["ref"], "COMPLETED", _evidence_json(v))
                db.audit(ss.user, "TRANSFER_COMPLETED", {"ref": s["ref"], "amount": s["amount"], "step_up": True})
                s["done"] = True
            else:
                s["blocked"] = "insufficient funds."
            st.rerun()
        else:
            s["otp_tries"] += 1
            db.audit(ss.user, "OTP_REJECTED", {"ref": s["ref"], "try": s["otp_tries"]})
            if s["otp_tries"] >= MAX_OTP_ATTEMPTS:
                db.set_transaction_status(s["ref"], "BLOCKED_OTP", _evidence_json(v))
                s["blocked"] = f"{MAX_OTP_ATTEMPTS} wrong signing codes."
                st.rerun()
            left = MAX_OTP_ATTEMPTS - s["otp_tries"]
            if otp_age(user["otp_secret"], code.replace(" ", ""), context=ctx):
                st.error(f"That code has expired ({left} tries left). Type the code the phone shows now.")
            else:
                st.error(f"Code rejected ({left} tries left). It must come from the "
                         "phone approval screen for this exact transfer.")


def _evidence_json(v):
    return {"liveness": [r["name"] + (":ok" if r["passed"] else ":fail") for r in v["liveness"]["results"]],
            "fas_real_prob": round(v["fas"]["real_prob"], 4), "fas_threshold": v["fas"]["threshold"],
            "match": v["match_score"], "reasons": v["reasons"]}


# ================================================================== navigation

def _as_page(name, fn):
    def run():
        ss.page = name          # the page currently shown (read by tests and helpers)
        fn()
    run.__name__ = f"page_{name}"
    return run


signed_in = bool(ss.user)
_SPEC = [  # name, function, title, icon, url path, shown in the top bar
    ("home", page_home, "Home", ":material/home:", "home", True),
    ("login", page_login, "Sign in", ":material/login:", "sign-in", not signed_in),
    ("signup", page_signup, "Open an account", ":material/person_add:", "open-account", not signed_in),
    ("dashboard", page_dashboard, "Accounts", ":material/account_balance:", "accounts", signed_in),
    ("lab", model_lab.render, "Model Lab", ":material/science:", "model-lab", True),
    ("stepup", page_stepup, "Verify transfer", ":material/verified_user:", "verify-transfer", False),
    ("pair", page_pair, "Pair a phone", ":material/smartphone:", "pair-phone", False),
]
PAGES = {name: st.Page(_as_page(name, fn), title=title, icon=icon, url_path=path, default=(name == "home"),
                       visibility="visible" if shown else "hidden")
         for name, fn, title, icon, path, shown in _SPEC}
current = st.navigation(list(PAGES.values()), position="top")

with st.sidebar:
    st.markdown("### :material/shield_lock: VaultTrust")
    if ss.user:
        st.caption(f"Signed in as **{ss.user}**")
    with st.expander("Phone network", icon=":material/wifi:"):
        hosts = _candidate_hosts() or ["127.0.0.1"]
        ss.auth_host = st.selectbox("Laptop address the phone should use", hosts,
                                    index=hosts.index(ss.get("auth_host")) if ss.get("auth_host") in hosts else 0)
        st.caption(f"Authenticator served at `{authenticator_server.base_url(ss.auth_host)}`. "
                   "If the phone cannot open it, allow Python through Windows Firewall.")
    if ss.user and st.button("Sign out", icon=":material/logout:", width="stretch"):
        ss.clear()
        go("home")

# Programmatic navigation for tests: st.session_state["_goto"] = "<page name>" before a run.
_goto = ss.pop("_goto", None)
if _goto and PAGES[_goto].url_path != current.url_path:
    st.switch_page(PAGES[_goto])
current.run()
