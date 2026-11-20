"""
Architecture, design and UML diagrams for the report, drawn with matplotlib.

    python docs/report/diagrams.py        -> docs/report/figures/*.png
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Ellipse  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "savefig.dpi": 220, "savefig.bbox": "tight",
                     "savefig.pad_inches": 0.06})

C = {"ui": "#E8F0FB", "uiE": "#3B6FB6", "core": "#E9F6EF", "coreE": "#3A9E6F", "ml": "#FFF2E2", "mlE": "#E08A2E",
     "sec": "#F3ECF8", "secE": "#7B5EA7", "db": "#EEF0F3", "dbE": "#5B6573", "bad": "#FBE9E6", "badE": "#C8553D",
     "dark": "#1F2D3D"}


def canvas(w, h, xlim=100, ylim=None):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, xlim)
    ax.set_ylim(0, ylim or xlim * h / w)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fc=C["core"], ec=C["coreE"], fs=8.5, bold=False, round_=1.2, ha="center", lw=1.2,
        color="#1F2D3D", style="round", z=2):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"{style},pad=0,rounding_size={round_}" if style == "round" else style,
                       fc=fc, ec=ec, lw=lw, zorder=z)
    ax.add_patch(p)
    tx = x + w / 2 if ha == "center" else x + 1.2
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs, fontweight="bold" if bold else "normal",
            zorder=3, color=color, linespacing=1.25)
    return (x, y, w, h)


def arrow(ax, p1, p2, text=None, color="#4A5563", ls="-", lw=1.1, fs=7.5, rad=0.0, both=False, toff=(0, 1.2),
          head=8):
    a = FancyArrowPatch(p1, p2, arrowstyle="<|-|>" if both else "-|>", mutation_scale=head, color=color, lw=lw,
                        linestyle=ls, connectionstyle=f"arc3,rad={rad}", zorder=2.5, shrinkA=0, shrinkB=0)
    ax.add_patch(a)
    if text:
        ax.text((p1[0] + p2[0]) / 2 + toff[0], (p1[1] + p2[1]) / 2 + toff[1], text, ha="center", va="bottom",
                fontsize=fs, color="#374151", zorder=4,
                bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))


def save(fig, name):
    fig.savefig(os.path.join(OUT, name))
    plt.close(fig)
    print("  ", name)


# ------------------------------------------------------------------ 1. system architecture
def architecture():
    fig, ax = canvas(9.2, 6.4)
    W, H = 100, 100 * 6.4 / 9.2
    box(ax, 1, H - 9, 98, 7.5, "", fc="#F7F9FC", ec="#C9D3E0", round_=1, z=0)
    ax.text(3, H - 5.2, "Client side", fontsize=9, fontweight="bold", color="#3B4A5E", va="center")
    box(ax, 18, H - 8, 33, 5.5, "Laptop browser — Streamlit UI\nWebRTC camera 640×480 @ 15 fps", C["ui"], C["uiE"], fs=8)
    box(ax, 58, H - 8, 39, 5.5, "Phone browser — authenticator page\npure-JS SHA-256 / HMAC, key in localStorage",
        C["ui"], C["uiE"], fs=8)
    # server
    top = H - 13
    box(ax, 1, 3.2, 98, top - 3.8, "", fc="#FBFCFD", ec="#C9D3E0", round_=1, z=0)
    ax.text(3, top - 2.6, "Server (laptop, CPU only) — Python 3.14", fontsize=9, fontweight="bold", color="#3B4A5E")
    box(ax, 4, top - 13, 44, 8.5, "app.py — pages, routing, decisions\nsign-up · sign-in · accounts · transfers\n"
        "step-up policy (≥ $1,000) · model lab", C["core"], C["coreE"], fs=8)
    box(ax, 52, top - 13, 44, 8.5, "authenticator_server.py (port 8600)\nserves the phone page; no secrets\n"
        "on the server side of this page", C["core"], C["coreE"], fs=8)
    box(ax, 4, top - 26.5, 44, 10.5, "ui_components.py\nliveness_camera · presence_step\nverify_presence (AND fusion)\n"
        "_check_continuity · evidence card · explanation", C["core"], C["coreE"], fs=8)
    y = top - 41
    box(ax, 4, y, 21, 11.5, "liveness_engine.py\nMediaPipe Face\nLandmarker (478 pts,\n52 blendshapes)\nchallenges + continuity",
        C["ml"], C["mlE"], fs=7.5)
    box(ax, 27, y, 21, 11.5, "fas_engine.py\ndual ResNet-18\nRGB + FFT branches\nGrad-CAM, FD, spectrum\nv5, thr 0.185",
        C["ml"], C["mlE"], fs=7.5)
    box(ax, 52, y, 21, 11.5, "face_engine.py\nRetinaFace det_10g\n+ ArcFace R50\n(WebFace600K)\n512-D embedding",
        C["ml"], C["mlE"], fs=7.5)
    box(ax, 75, y, 21, 11.5, "biometric_template.py\nlogistic-map key →\npermutation + QR\nprojection 512→256\n(cancelable)",
        C["sec"], C["secE"], fs=7.5)
    box(ax, 52, top - 26.5, 44, 10.5, "walk_otp.py (OTP v2)\nHMAC-SHA256(K, T ‖ H(tx)) → SHA-256 stream\n"
        "16-step walk on a 64-node small-world graph\nSHA-256(path) → RFC 4226 truncation → 6 digits",
        C["sec"], C["secE"], fs=7.5)
    box(ax, 4, 5, 44, 9, "database.py — SQLite (vaulttrust.db)\nusers · transactions · audit · used_otps\n"
        "Fernet (AES-128-CBC + HMAC) for keys and K", C["db"], C["dbE"], fs=7.5)
    box(ax, 52, 5, 44, 9, "Model files and policy\nmodels/fas_v2.pth (v5) · calibration JSON\n"
        "policy.json (enforce / advisory) · buffalo_l ONNX", C["db"], C["dbE"], fs=7.5)
    arrow(ax, (34.5, H - 8), (26, top - 4.5))
    arrow(ax, (77.5, H - 8), (74, top - 4.5))
    ax.text(29, H - 11.8, "camera frames, clicks", fontsize=7, color="#374151", ha="right")
    ax.text(77, H - 11.8, "page load only", fontsize=7, color="#374151", ha="left")
    arrow(ax, (26, top - 13), (26, top - 16))
    for x in (14.5, 37.5, 62.5):
        arrow(ax, (26, top - 26.5), (x, y + 11.5))
    arrow(ax, (48, top - 21), (52, top - 21), both=True)
    arrow(ax, (85.5, top - 26.5), (85.5, y + 11.5))
    arrow(ax, (26, y), (26, 14))
    arrow(ax, (62.5, y), (74, 14))
    ax.text(50, 0.6, "QR codes shown on the laptop carry K (once, at pairing) and the transfer details to the phone; "
            "the phone never sends data to the server", ha="center", fontsize=7.2, style="italic", color="#4B5563")
    save(fig, "architecture.png")


# ------------------------------------------------------------------ 2. step-up flow
def stepup_flow():
    fig, ax = canvas(8.6, 7.6)
    H = 100 * 7.6 / 8.6
    def node(y, t, kind="core", w=46, x=27):
        fc, ec = {"core": (C["core"], C["coreE"]), "ml": (C["ml"], C["mlE"]), "sec": (C["sec"], C["secE"]),
                  "bad": (C["bad"], C["badE"]), "ui": (C["ui"], C["uiE"])}[kind]
        return box(ax, x, y, w, 6.2, t, fc, ec, fs=8)
    ys = [H - 8 - i * 9.6 for i in range(9)]
    node(ys[0], "Signed-in user starts a transfer\n(amount, payee)", "ui")
    box(ax, 33, ys[1], 34, 6.2, "amount ≥ $1,000 ?", "#FFFFFF", "#4A5563", fs=8.5, style="round4,pad=0")
    node(ys[2], "Presence check: calibration (20 frontal frames)\n+ 2 random challenges (9 s each)", "ml")
    node(ys[3], "Continuity tracked from calibration to last challenge\n(gap ≤ 0.7 s, jump ≤ 0.5 face-widths)", "ml")
    node(ys[4], "Verify: anti-spoofing (median of 10 frames ≥ thr),\nArcFace ≥ 0.40, identity on challenges ≥ 0.35", "ml")
    node(ys[5], "QR with reference, amount, payee\nshown on the laptop", "sec")
    node(ys[6], "Phone authenticator shows the transfer;\nuser approves → 6-digit walk-OTP bound to it", "sec")
    node(ys[7], "Server verifies code (current step, 10 s grace),\nreplay table, ≤ 3 tries", "sec")
    node(ys[8], "Transfer settled atomically; audit + evidence saved", "core")
    for a, b in zip(ys, ys[1:]):
        arrow(ax, (50, a), (50, b + 6.2))
    node(ys[1], "Settle immediately\n(no step-up)", "core", w=21, x=78)
    arrow(ax, (67, ys[1] + 3.1), (78, ys[1] + 3.1), "no", toff=(0, 0.3))
    ax.text(51.5, ys[1] - 2.2, "yes", fontsize=7.5)
    node(ys[3] - 2, "Fail → retry\n(max 3) → block", "bad", w=21, x=78)
    arrow(ax, (73, ys[4] + 3.1), (78, ys[3] + 1.1))
    ax.text(79, ys[4] + 0.5, "any check fails", fontsize=7.5, color="#374151")
    arrow(ax, (73, ys[2] + 3.1), (78, ys[3] + 3.1))
    arrow(ax, (73, ys[3] + 3.1), (78, ys[3] + 2.1))
    node(ys[7] - 1, "Wrong / expired /\nreplayed → block", "bad", w=21, x=78)
    arrow(ax, (73, ys[7] + 3.1), (78, ys[7] + 2.1))
    box(ax, 1, ys[4], 22, 6.2 + (ys[2] - ys[4]), "INHERENCE\nlive, genuine,\nmatching face\n(A + L + F)", "#FFFFFF",
        C["mlE"], fs=8, bold=True)
    box(ax, 1, ys[7], 22, 6.2 + (ys[5] - ys[7]), "POSSESSION\npaired phone,\ncode bound to the\ntransfer (PSD2\ndynamic linking)",
        "#FFFFFF", C["secE"], fs=8, bold=True)
    save(fig, "stepup_flow.png")


# ------------------------------------------------------------------ 3. sequence diagram
def sequence():
    fig, ax = canvas(9.6, 7.4)
    H = 100 * 7.4 / 9.6
    actors = ["User", "Browser\n(Streamlit UI)", "Liveness\nprocessor", "Verifier\n(FAS · ArcFace)", "Database", "Phone\nauthenticator"]
    xs = [8, 25, 43, 61, 77, 92]
    for x, a in zip(xs, actors):
        box(ax, x - 7, H - 7, 14, 5.5, a, C["ui"] if x in (8, 92) else C["core"], C["uiE"] if x in (8, 92) else C["coreE"], fs=7.5)
        ax.plot([x, x], [2, H - 7], color="#9AA3AF", lw=0.8, ls="--", zorder=0)
    msgs = [(0, 1, "transfer $5,000 to payee"), (1, 4, "create PENDING_STEP_UP"), (1, 2, "start camera (WebRTC frames)"),
            (2, 2, "calibrate: 20 frontal frames"), (2, 0, "challenge 1, challenge 2 (random)"), (0, 2, "blink / turn / smile / look up"),
            (2, 2, "continuity: gap, jump, faces"), (2, 1, "PASSED + snapshot (10 clean, ≤24 challenge frames)"),
            (1, 3, "verify_presence(snapshot, user)"), (3, 4, "load template, key"), (3, 1, "decision + reasons + Grad-CAM"),
            (1, 0, "QR: ref · amount · payee"), (0, 5, "scan QR, approve"), (5, 0, "6-digit code (bound to tx)"),
            (0, 1, "enter code"), (1, 4, "verify: step, grace, replay"), (4, 1, "COMPLETED; audit")]
    y = H - 11
    for a, b, t in msgs:
        if a == b:
            ax.annotate("", xy=(xs[a] + 0.3, y - 2.2), xytext=(xs[a] + 0.3, y),
                        arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=-1.2", color="#4A5563", lw=1))
            ax.text(xs[a] + 2.5, y - 1.1, t, fontsize=7, va="center")
            y -= 4.2
            continue
        arrow(ax, (xs[a], y), (xs[b], y), color="#3B6FB6" if b > a else "#E08A2E", ls="-" if b > a else "--")
        ax.text((xs[a] + xs[b]) / 2, y + 0.5, t, ha="center", va="bottom", fontsize=7)
        y -= 3.85
    save(fig, "sequence_stepup.png")


# ------------------------------------------------------------------ 4. use case diagram
def usecase():
    fig, ax = canvas(9, 6.2)
    H = 100 * 6.2 / 9

    def actor(x, y, name):
        ax.add_patch(plt.Circle((x, y + 6.4), 1.5, fc="white", ec="#1F2D3D", lw=1.2))
        ax.plot([x, x], [y + 4.9, y + 1.8], color="#1F2D3D", lw=1.2)
        ax.plot([x - 2.4, x + 2.4], [y + 3.9, y + 3.9], color="#1F2D3D", lw=1.2)
        ax.plot([x, x - 2], [y + 1.8, y - 1], color="#1F2D3D", lw=1.2)
        ax.plot([x, x + 2], [y + 1.8, y - 1], color="#1F2D3D", lw=1.2)
        ax.text(x, y - 3, name, ha="center", fontsize=8, fontweight="bold")
    box(ax, 20, 2, 60, H - 4, "", fc="#FBFCFD", ec="#9AA3AF", round_=1)
    ax.text(50, H - 4.8, "VaultTrust", ha="center", fontsize=10, fontweight="bold")
    uc = [("Open account (enrol face,\npair phone)", 50, H - 11), ("Sign in with face", 50, H - 19),
          ("View accounts and\nsecurity log", 50, H - 27), ("Transfer < $1,000", 50, H - 35),
          ("Transfer ≥ $1,000\n(step-up)", 50, H - 43), ("Approve transfer\non phone (OTP)", 50, H - 51),
          ("Re-pair phone", 32, H - 59), ("Inspect models,\nthresholds, policy", 68, H - 59)]
    pos = {}
    for t, x, y in uc:
        ax.add_patch(Ellipse((x, y), 24, 6.4, fc=C["ui"], ec=C["uiE"], lw=1.1, zorder=2))
        ax.text(x, y, t, ha="center", va="center", fontsize=7.5, zorder=3)
        pos[t.split("\n")[0]] = (x, y)
    actor(8, H / 2 + 6, "Customer")
    actor(92, H / 2 + 14, "Phone\nauthenticator")
    actor(92, H / 2 - 16, "Evaluator /\nexaminer")
    for k in ("Open account (enrol face,", "Sign in with face", "View accounts and", "Transfer < $1,000",
              "Transfer ≥ $1,000", "Re-pair phone"):
        x, y = pos[k]
        ax.plot([10.5, x - 12], [H / 2 + 9.5, y], color="#6B7280", lw=0.8)
    for k in ("Approve transfer", "Open account (enrol face,"):
        x, y = pos[k]
        ax.plot([89.5, x + 12], [H / 2 + 17.5, y], color="#6B7280", lw=0.8)
    x, y = pos["Inspect models,"]
    ax.plot([89.5, x + 12], [H / 2 - 12.5, y], color="#6B7280", lw=0.8)
    arrow(ax, (50, H - 46.2), (50, H - 47.8), color="#7B5EA7", ls="--")
    ax.text(51.5, H - 47.3, "«include»", fontsize=6.5, color="#7B5EA7")
    save(fig, "usecase.png")


# ------------------------------------------------------------------ 5. liveness state machine
def liveness_states():
    fig, ax = canvas(9, 5.0)
    H = 100 * 5.0 / 9
    box(ax, 3, 20, 18, 10, "CALIBRATE\n20 frontal frames\n|yaw|<15°, |pitch|<20°\nkeep 10 clean frames", C["ml"], C["mlE"], fs=7.5)
    box(ax, 33, 20, 22, 10, "CHALLENGE i (i = 1, 2)\nrandom, distinct;\njudged vs. own baseline;\n9 s limit", C["ml"], C["mlE"], fs=7.5)
    box(ax, 72, 36, 24, 8, "PASSED\nsnapshot → verifier", C["core"], C["coreE"], fs=8, bold=True)
    box(ax, 72, 20, 24, 8, "FAILED\nreason logged", C["bad"], C["badE"], fs=8, bold=True)
    arrow(ax, (21, 25), (33, 25), "baseline =\nmedian signals", toff=(0, 0.6))
    arrow(ax, (55, 27), (72, 40), "both done")
    arrow(ax, (55, 24), (72, 24))
    ax.text(63.5, 17.6, "timeout · 2 faces ·\ncontinuity broken", ha="center", fontsize=7.3, color="#374151")
    ax.annotate("", xy=(48, 30.2), xytext=(40, 30.2), arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=-1.4",
                                                                       color="#4A5563", lw=1))
    ax.text(44, 36.5, "next challenge", ha="center", fontsize=7.5)
    ax.annotate("", xy=(8, 30.2), xytext=(15, 30.2), arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=1.4",
                                                                     color="#C8553D", lw=1))
    ax.text(12, 37, "gap > 0.7 s, jump, 2nd face:\nrestart & discard frames", ha="center", fontsize=7, color="#C8553D")
    rows = ["BLINK x2: eye closure > max(0.45, rest+0.3), then < max(0.25, rest+0.1)",
            "TURN L/R: |Δyaw| > 18° (mirrored view)   ·   LOOK UP: Δpitch > 12°",
            "SMILE: mouthSmile > max(0.45, rest+0.25)"]
    for i, r in enumerate(rows):
        ax.text(3, 11 - i * 4.0, r, fontsize=7.3, family="DejaVu Sans Mono", color="#374151")
    save(fig, "liveness_state_machine.png")


# ------------------------------------------------------------------ 6. class diagram
def class_diagram():
    fig, ax = canvas(9.4, 6.6)
    H = 100 * 6.6 / 9.4

    def cls(x, y, w, name, attrs, ops, color=("#FFFFFF", "#1F2D3D")):
        lh = 2.55
        h = lh * (1 + len(attrs) + len(ops)) + 2.2
        ax.add_patch(FancyBboxPatch((x, y - h), w, h, boxstyle="square,pad=0", fc=color[0], ec=color[1], lw=1.1))
        ax.add_patch(FancyBboxPatch((x, y - lh - 0.6), w, lh + 0.6, boxstyle="square,pad=0", fc="#E8EDF4", ec=color[1], lw=1.1))
        ax.text(x + w / 2, y - lh / 2 - 0.3, name, ha="center", va="center", fontsize=8, fontweight="bold")
        yy = y - lh - 1.9
        for a in attrs:
            ax.text(x + 0.8, yy, a, fontsize=6.6, va="center", family="DejaVu Sans Mono")
            yy -= lh
        ax.plot([x, x + w], [yy + lh / 2 + 0.2, yy + lh / 2 + 0.2], color=color[1], lw=0.8)
        yy -= 0.4
        for o in ops:
            ax.text(x + 0.8, yy, o, fontsize=6.6, va="center", family="DejaVu Sans Mono")
            yy -= lh
        return (x, y - h, w, h)
    a = cls(1, H - 2, 31, "LivenessProcessor", ["state, challenges, idx", "baseline, clean_frames", "challenge_frames, continuity"],
            ["recv(frame) → frame", "_check_challenge(m)", "_continuity(m, now)", "snapshot() → dict"])
    b = cls(35, H - 2, 30, "Verifier (ui_components)", ["CONTINUITY_THRESHOLD = 0.35"],
            ["verify_presence(snap, user)", "_check_continuity(v, snap)", "_reasons(v) → list", "evidence_card(v)"])
    c = cls(68, H - 2, 31, "SpatialFrequencyFAS", ["spatial_encoder: ResNet-18", "freq_encoder: ResNet-18",
                                                   "classifier: 1024→256→2"], ["forward(x_rgb, x_fft)"])
    d = cls(68, H - 26, 31, "fas_engine", ["threshold, policy"], ["assess_frames(frames)", "explain(face) → maps",
                                                                  "fas_enforced()"])
    e = cls(35, H - 30, 30, "face_engine", ["MATCH_THRESHOLD = 0.40"], ["embed(img) → (e, box)", "embed_best(frames)",
                                                                        "cosine(a, b)"])
    f = cls(1, H - 30, 31, "biometric_template", ["EMBED_DIM 512, TEMPLATE_DIM 256"],
            ["new_key() → 32 bytes", "protect(e, key) → t", "match(e, t, key) → cos"])
    g = cls(1, H - 50, 31, "walk_otp", ["OTPConfig, GraphConfig"], ["generate_otp(K, T, ctx)", "verify_otp(K, code, …)",
                                                                     "otp_age(K, code)", "transaction_context(…)"])
    h = cls(35, H - 50, 30, "database", ["users, transactions", "audit, used_otps"],
            ["create_user(…)", "settle_transaction(…)", "log_event(…)", "replace_otp_secret(…)"])
    i = cls(68, H - 50, 31, "app (Streamlit pages)", ["PAGES, STEP_UP_LIMIT", "OTP_GRACE_SECONDS = 10"],
            ["page_signup / page_signin", "page_transfer / page_verify", "page_pair / page_model_lab"])
    for (p, q) in (((32, H - 9), (35, H - 9)), ((65, H - 8), (68, H - 8)), ((83, H - 18.5), (83, H - 26)),
                   ((50, H - 18.5), (50, H - 30)), ((35, H - 15), (32, H - 33)), ((65, H - 15), (68, H - 30)),
                   ((68, H - 55), (65, H - 55)), ((68, H - 60), (32, H - 55)), ((83, H - 50), (83, H - 38.5))):
        arrow(ax, p, q, color="#6B7280", lw=0.9, head=7)
    save(fig, "class_diagram.png")


# ------------------------------------------------------------------ 7. ER diagram
def er_diagram():
    fig, ax = canvas(9, 5.6)
    H = 100 * 5.6 / 9

    def ent(x, y, w, name, fields):
        lh = 2.9
        h = lh * (len(fields) + 1) + 1.2
        ax.add_patch(FancyBboxPatch((x, y - h), w, h, boxstyle="square,pad=0", fc="white", ec="#1F2D3D", lw=1.1))
        ax.add_patch(FancyBboxPatch((x, y - lh - 0.5), w, lh + 0.5, boxstyle="square,pad=0", fc="#E8EDF4", ec="#1F2D3D", lw=1.1))
        ax.text(x + w / 2, y - lh / 2 - 0.2, name, ha="center", va="center", fontweight="bold", fontsize=8.5)
        for k, f in enumerate(fields):
            ax.text(x + 0.8, y - lh * (k + 1.5) - 0.6, f, fontsize=6.8, va="center", family="DejaVu Sans Mono")
    ent(4, H - 12, 30, "users", ["PK email TEXT", "template BLOB (256×f32)", "template_key BLOB (Fernet)",
                                "otp_secret BLOB (Fernet)", "device_paired INT", "balance REAL", "paired_host TEXT",
                                "paired_at, created_at"])
    ent(62, H - 1, 32, "transactions", ["PK id INT", "ref TEXT UNIQUE", "FK sender → users", "receiver TEXT",
                                        "amount REAL", "status TEXT", "evidence JSON", "created_at"])
    ent(62, H - 30.5, 32, "audit", ["PK id INT", "FK email → users", "event TEXT", "detail JSON", "created_at"])
    ent(62, H - 51.5, 32, "used_otps", ["PK (email, scope, counter)", "FK email → users"])
    arrow(ax, (34, H - 20), (62, H - 12), "1 : N  (sender)", head=7, toff=(0, 0.4))
    arrow(ax, (34, H - 26), (62, H - 39), "1 : N", head=7, toff=(0, 0.4))
    arrow(ax, (34, H - 32), (62, H - 57), "1 : N", head=7, toff=(0, 0.4))
    ax.text(4, H - 48, "transactions.status ∈ {PENDING, PENDING_STEP_UP,\nCOMPLETED, CANCELLED, BLOCKED_PRESENCE,\n"
            "BLOCKED_OTP, FAILED_FUNDS}", fontsize=7, color="#374151")
    save(fig, "er_diagram.png")


# ------------------------------------------------------------------ 8. dual-branch network
def fas_network():
    fig, ax = canvas(9.4, 3.9)
    H = 100 * 3.9 / 9.4
    box(ax, 1, 14, 12, 14, "face crop\n(MediaPipe box\n+ 20 % margin)", C["ui"], C["uiE"], fs=7.5)
    box(ax, 17, 26, 15, 9, "RGB 224×224\nImageNet norm.", C["core"], C["coreE"], fs=7.5)
    box(ax, 17, 6, 15, 10, "2-D FFT per channel\nlog-magnitude,\nshift, min-max", C["sec"], C["secE"], fs=7.5)
    box(ax, 36, 26, 20, 9, "ResNet-18 encoder\n(layer3–4 fine-tuned)\n→ 512-D", C["ml"], C["mlE"], fs=7.5)
    box(ax, 36, 6.5, 20, 9, "ResNet-18 encoder\n(layer3–4 fine-tuned)\n→ 512-D", C["ml"], C["mlE"], fs=7.5)
    box(ax, 60, 14, 11, 14, "concat\n1024-D", "#FFFFFF", "#4A5563", fs=7.5)
    box(ax, 74, 14, 13, 14, "FC 256\nBatchNorm\nReLU\nDropout 0.4\nFC 2", C["core"], C["coreE"], fs=7.2)
    box(ax, 90, 16, 9, 10, "softmax\nP(real)", "#FFFFFF", "#1F2D3D", fs=7.5, bold=True)
    arrow(ax, (13, 23), (17, 30))
    arrow(ax, (13, 19), (17, 11))
    arrow(ax, (32, 30.5), (36, 30.5))
    arrow(ax, (32, 11), (36, 11))
    arrow(ax, (56, 30.5), (60, 24))
    arrow(ax, (56, 11), (60, 18))
    arrow(ax, (71, 21), (74, 21))
    arrow(ax, (87, 21), (90, 21))
    ax.text(46, 37, "spatial branch: texture, reflections, edges, moiré in RGB", ha="center", fontsize=7, style="italic")
    ax.text(46, 2.5, "frequency branch: screen pixel grid, print raster, missing high frequencies", ha="center", fontsize=7,
            style="italic")
    ax.text(79, 31, "Grad-CAM on layer4 (7×7) of both encoders;\ngradient × activation splits the evidence by branch",
            ha="center", fontsize=6.8, color="#7B5EA7")
    save(fig, "fas_network.png")


# ------------------------------------------------------------------ 9. template pipeline
def template_pipeline():
    fig, ax = canvas(9.4, 3.4)
    box(ax, 1, 13, 15, 9, "ArcFace\nembedding e\n512-D, ‖e‖ = 1", C["ml"], C["mlE"], fs=7.5)
    box(ax, 1, 1, 15, 8, "per-user key\n256-bit (random)", C["sec"], C["secE"], fs=7.5)
    box(ax, 21, 1, 20, 8, "HMAC-SHA256(key, label)\n→ x₀ ∈ (0.01, 0.99),\nr ∈ [3.99, 3.9999]", C["sec"], C["secE"], fs=7)
    box(ax, 46, 1, 22, 8, "logistic map xₙ₊₁ = r·xₙ(1−xₙ)\n500 burn-in; seq. 1 → perm π\nseq. 2 → 512×256 → QR → W", C["sec"],
        C["secE"], fs=7)
    box(ax, 46, 13, 22, 9, "t = W · e[π]\nW: 256×512,\northonormal rows", C["core"], C["coreE"], fs=7.5)
    box(ax, 73, 13, 13, 9, "normalise\n‖t‖ = 1\n1,024 bytes", C["core"], C["coreE"], fs=7.5)
    box(ax, 89, 11, 10, 13, "stored\ntemplate\n(no raw e)", C["db"], C["dbE"], fs=7.5, bold=True)
    arrow(ax, (16, 17.5), (46, 17.5))
    arrow(ax, (16, 5), (21, 5))
    arrow(ax, (41, 5), (46, 5))
    arrow(ax, (57, 9), (57, 13))
    arrow(ax, (68, 17.5), (73, 17.5))
    arrow(ax, (86, 17.5), (89, 17.5))
    ax.text(50, 30.5, "match(e′, t, key) = cos(protect(e′, key), t) ≥ 0.40   ·   new key ⇒ new, unlinkable template (revocation)",
            ha="center", fontsize=7.6, color="#374151")
    save(fig, "template_pipeline.png")


# ------------------------------------------------------------------ 10. OTP pipeline
def otp_pipeline():
    fig, ax = canvas(9.4, 3.6)
    box(ax, 1, 21, 15, 8, "secret K (32 B)\nshared at pairing", C["sec"], C["secE"], fs=7.5)
    box(ax, 1, 11, 15, 8, "T = ⌊time / 30 s⌋", C["ui"], C["uiE"], fs=7.5)
    box(ax, 1, 1, 15, 8, "context\nTX|ref|cents|payee", C["ui"], C["uiE"], fs=7.5)
    box(ax, 21, 9, 18, 12, "seed = HMAC-SHA256\n(K, T₈ ‖ SHA-256(ctx))", C["sec"], C["secE"], fs=7.5)
    box(ax, 43, 9, 17, 12, "byte stream\nSHA-256(seed ‖ i)\nrejection sampling\n→ uniform choices", C["core"], C["coreE"], fs=7.2)
    box(ax, 64, 9, 15, 12, "walk on public\n64-node graph\nstart + 16 steps\n(17 nodes)", C["ml"], C["mlE"], fs=7.2)
    box(ax, 83, 9, 16, 12, "SHA-256 of tag\n‖ path, RFC 4226\ntruncation\n→ 6 digits", C["core"], C["coreE"], fs=7)
    arrow(ax, (16, 25), (21, 17))
    arrow(ax, (16, 15), (21, 15))
    arrow(ax, (16, 5), (21, 13))
    for a, b in ((39, 43), (60, 64), (79, 83)):
        arrow(ax, (a, 15), (b, 15))
    ax.text(50, 30.5, "Phone and server compute the same code independently; changing amount, payee or reference changes the code",
            ha="center", fontsize=7.6, color="#374151")
    save(fig, "otp_pipeline.png")


# ------------------------------------------------------------------ 11. decision fusion
def fusion():
    fig, ax = canvas(9.2, 3.95)
    box(ax, 1, 25, 20, 9, "L  active liveness\n2 random challenges\n+ continuity (processor)", C["ml"], C["mlE"], fs=7.3)
    box(ax, 1, 13.5, 20, 9, "F  anti-spoofing\nmedian of 10 calibration\nframes ≥ threshold", C["ml"], C["mlE"], fs=7.3)
    box(ax, 1, 2, 20, 9, "A  ArcFace match\nprotected template\ncos ≥ 0.40", C["ml"], C["mlE"], fs=7.3)
    box(ax, 27, 7, 25, 22, "server continuity\n\nidentity: challenge frames vs\ncalibration (cos ≥ 0.35)\n\n"
        "anti-spoofing on ≥ 3 neutral\nchallenge frames ≥ threshold", C["core"], C["coreE"], fs=7.3)
    box(ax, 58, 12.5, 12, 11, "AND", "#FFFFFF", "#1F2D3D", fs=11, bold=True)
    box(ax, 76, 20, 22, 8, "PASS → OTP step", C["core"], C["coreE"], fs=8, bold=True)
    box(ax, 76, 7, 22, 9, "REJECT + reasons,\nGrad-CAM, evidence card", C["bad"], C["badE"], fs=7.5, bold=True)
    for y in (29.5, 18, 6.5):
        arrow(ax, (21, y), (27, 18 if y == 18 else (24 if y > 18 else 12)))
    arrow(ax, (52, 18), (58, 18))
    arrow(ax, (70, 20), (76, 24))
    arrow(ax, (70, 16), (76, 11.5))
    ax.text(60, 36.5, "policy: enforce (default) — or advisory, where the F score is logged but does not block",
            ha="center", fontsize=7, style="italic", color="#4B5563")
    save(fig, "decision_fusion.png")


# ------------------------------------------------------------------ 12. Gantt chart
def gantt():
    import datetime as dt
    tasks = [
        ("Problem study, idea selection, team roles", "2026-07-06", "2026-07-24", "Team"),
        ("Literature survey (FAS, liveness, OTP, templates)", "2026-07-13", "2026-08-14", "Team"),
        ("Requirements, architecture and UML (Review 1)", "2026-07-27", "2026-08-18", "Team"),
        ("Random-walk OTP engine v1 + FastAPI server", "2026-08-01", "2026-08-19", "Nilay"),
        ("Spatial-frequency anti-spoofing model (C1–C2)", "2026-08-20", "2026-09-26", "Magizharasan, Rwitankar"),
        ("Active liveness and explainability (C3–C4)", "2026-08-25", "2026-09-19", "Nilay"),
        ("Integration, UI, face recognition, template", "2026-09-20", "2026-10-06", "Team"),
        ("Overhaul: OTP v2, phone authenticator, retraining", "2026-10-06", "2026-10-10", "Team"),
        ("Webcam data collection (videos, captures)", "2026-10-08", "2026-10-10", "Rwitankar, Nilay"),
        ("Continuity fix, v5 model, 105 tests", "2026-10-10", "2026-10-12", "Nilay"),
        ("Evaluation suite, ablation, comparative study", "2026-10-13", "2026-10-24", "Team"),
        ("Report, slides, final review", "2026-10-13", "2026-11-03", "Team"),
    ]
    miles = [("Review 1", "2026-08-19"), ("System complete", "2026-10-12"), ("Submission", "2026-11-03")]
    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    d0 = dt.date(2026, 7, 6)
    for i, (t, s, e, who) in enumerate(tasks):
        s, e = dt.date.fromisoformat(s), dt.date.fromisoformat(e)
        y = len(tasks) - 1 - i
        col = {"Team": "#3B6FB6", "Nilay": "#E08A2E"}.get(who, "#3A9E6F")
        ax.barh(y, (e - s).days + 1, left=(s - d0).days, color=col, height=0.62, edgecolor="white")
        ax.text(-1, y, t, ha="right", va="center", fontsize=7.6)
    for name, d in miles:
        x = (dt.date.fromisoformat(d) - d0).days
        ax.axvline(x, color="#C8553D", ls="--", lw=0.9)
        ax.text(x, len(tasks) - 0.3, name, rotation=0, fontsize=7.3, color="#C8553D", ha="center")
    months = [dt.date(2026, m, 1) for m in range(7, 12)]
    ax.set_xticks([(m - d0).days for m in months])
    ax.set_xticklabels([m.strftime("%b %Y") for m in months], fontsize=8)
    ax.set_yticks([])
    ax.set_xlim(0, (dt.date(2026, 11, 5) - d0).days)
    ax.set_ylim(-0.8, len(tasks) + 0.4)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", alpha=0.25)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#3B6FB6", label="whole team"), Patch(color="#E08A2E", label="Nilay"),
                       Patch(color="#3A9E6F", label="Magizharasan / Rwitankar")], fontsize=7.5, loc="lower left",
              frameon=False, ncol=3, bbox_to_anchor=(0, -0.2))
    save(fig, "gantt.png")


# ------------------------------------------------------------------ 13. taxonomy of anti-spoofing
def taxonomy():
    fig, ax = canvas(9.4, 5.0)
    H = 100 * 5.0 / 9.4
    box(ax, 33, H - 8, 34, 6, "Face presentation attack detection", "#FFFFFF", "#1F2D3D", fs=8.5, bold=True)
    cols = [("Hardware-based", ["depth / 3-D sensors", "infrared, thermal", "multispectral", "light-field"]),
            ("Handcrafted software", ["texture: LBP, colour LBP", "frequency: Fourier HF ratio", "image quality (IDA)",
                                      "motion / optical flow"]),
            ("Deep learning", ["binary CNN classifiers", "auxiliary: depth, rPPG", "central difference conv.",
                               "domain generalisation"]),
            ("Challenge–response", ["blink, mouth, head pose", "random prompts", "screen-light reflection",
                                    "continuity of the face"])]
    for k, (title, items) in enumerate(cols):
        x = 2 + k * 24.5
        box(ax, x, H - 20, 22, 6, title, C["ml"] if k in (1, 2) else C["core"], C["mlE"] if k in (1, 2) else C["coreE"],
            fs=8, bold=True)
        arrow(ax, (50, H - 8), (x + 11, H - 14), head=6)
        for j, it in enumerate(items):
            box(ax, x + 1, H - 28.5 - j * 6.4, 20, 5, it, "#FFFFFF", "#9AA3AF", fs=7.2)
    ax.text(50, 2, "VaultTrust uses software only: deep spatial + frequency CNN (passive) and challenge–response "
            "with continuity (active)", ha="center", fontsize=7.5, style="italic", color="#374151")
    save(fig, "fas_taxonomy.png")


# ------------------------------------------------------------------ 14. threat / defence map
def threats():
    fig, ax = canvas(9.4, 4.8)
    H = 100 * 4.8 / 9.4
    th = ["Stolen password /\nhijacked session", "Printed or on-screen\nphoto", "Replayed video", "Different live person",
          "Swap: photo, then\nlive attacker", "Code for a modified\ntransfer", "Code replay /\nbrute force", "Template\ndatabase leak"]
    df = ["Step-up at transfer time\n(face + phone)", "L: cannot blink / smile\nF: print / screen texture",
          "L: random challenges\nF: screen artefacts", "A: ArcFace template\nmatch (cos < 0.40)",
          "Continuity: gap / jump,\nidentity + F on challenges", "Dynamic linking:\nH(tx) in the OTP seed",
          "used_otps table, 3 tries,\n10⁶ uniform codes", "Cancelable template,\nre-keying, Fernet"]
    for i, (a, b) in enumerate(zip(th, df)):
        y = H - 6.3 - i * 5.6
        box(ax, 3, y, 30, 4.6, a, C["bad"], C["badE"], fs=7.2)
        box(ax, 45, y, 36, 4.6, b, C["core"], C["coreE"], fs=7.2)
        arrow(ax, (45, y + 2.3), (33, y + 2.3), head=7)
        ax.text(90, y + 2.3, "tested", fontsize=7.2, ha="center", va="center", color="#3A9E6F", fontweight="bold")
    ax.text(18, H - 1.3, "Threat", ha="center", fontweight="bold")
    ax.text(63, H - 1.3, "Defence", ha="center", fontweight="bold")
    save(fig, "threat_map.png")


if __name__ == "__main__":
    for f in (architecture, stepup_flow, sequence, usecase, liveness_states, class_diagram, er_diagram, fas_network,
              template_pipeline, otp_pipeline, fusion, gantt, taxonomy, threats):
        f()
