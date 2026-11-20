"""
Reusable Streamlit pieces: the liveness camera, the presence-verification
pipeline (liveness + anti-spoofing + face match) and the evidence card.
"""

import json
import os
import threading
import time

import cv2
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer

import biometric_template
import face_engine
import fas_engine
from liveness_engine import CHALLENGE_TIMEOUT, CHALLENGES, LivenessProcessor
from liveness_engine import log

ACCENT = "#0d9488"
BAD = "#dc2626"
MUTED = "#64748b"


# ------------------------------------------------------------------ camera

def liveness_camera(key: str, state: dict | None = None):
    """
    Renders the webcam with live challenge overlay. When the attempt is PASSED
    or FAILED, the processor snapshot is stored in state["snap"] and the page
    reruns once.

    Performance: 640x480 is kept (anti-spoofing needs the detail) but at
    15 fps, which nearly halves the software video encode/decode the WebRTC
    round trip costs. The browser and server are on the same machine, so no
    STUN server is needed. Completion is checked by a small fragment that
    reruns on its own, instead of re-running the whole page every second.
    """
    cam, side = st.columns([1.15, 1], gap="large")
    with cam:
        ctx = webrtc_streamer(
            key=key,
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=LivenessProcessor,
            rtc_configuration={"iceServers": []},
            media_stream_constraints={"video": {"width": {"ideal": 640}, "height": {"ideal": 480},
                                                "frameRate": {"ideal": 15, "max": 15}}, "audio": False},
            async_processing=True,
            desired_playing_state=True,
            video_html_attrs={"style": {"width": "100%", "maxWidth": "560px", "borderRadius": "14px",
                                        "display": "block"},
                              "controls": False, "autoPlay": True, "muted": True},
        )

    with side:
        @st.fragment(run_every=0.8)
        def _panel():
            proc = ctx.video_processor
            status = proc.status() if proc is not None else None
            instruction_panel(status)
            if status and status["state"] in ("PASSED", "FAILED"):
                if state is not None:
                    state["snap"] = proc.snapshot()
                st.rerun(scope="app")

        _panel()
    return None


STEP_HINTS = {
    "BLINK": "Close both eyes fully, twice.",
    "TURN_LEFT": "Turn your head to your left, about 20 degrees.",
    "TURN_RIGHT": "Turn your head to your right, about 20 degrees.",
    "SMILE": "Give a clear, wide smile.",
    "LOOK_UP": "Tilt your head up, as if looking at the ceiling.",
}


def instruction_panel(status):
    """What to do right now, next to the camera (replaces squinting at text burned into the video)."""
    with st.container(border=True):
        if status is None:
            st.markdown("#### :material/videocam: Starting camera...")
            st.caption("Allow camera access when the browser asks. The first start after launching the app "
                       "can take 10-20 seconds; later ones are faster. If nothing happens, press **START** "
                       "under the video.")
            _tips()
            return
        steps = [("CALIBRATE", "Look straight at the camera and hold still")] + \
                [(c, CHALLENGES[c]) for c in status["challenges"]]
        if status["state"] == "CALIBRATE":
            current = 0
        elif status["state"] == "CHALLENGE":
            current = status["idx"] + 1
        else:
            current = len(steps)
        if status["state"] == "FAILED":
            st.markdown("#### :material/cancel: Check failed")
            st.caption(status["fail_reason"] or "")
        elif status["state"] == "PASSED":
            st.markdown("#### :material/check_circle: Liveness confirmed")
            st.caption("Checking for spoofing and matching your face...")
        else:
            name, text = steps[current]
            st.markdown(f"#### {text}")
            st.caption(STEP_HINTS.get(name, "Keep your face centred, eyes open, neutral expression."))
            if status["state"] == "CALIBRATE":
                st.progress(status["calibration"], text="Calibrating to your face")
            else:
                left = status["seconds_left"] or 0.0
                st.progress(left / CHALLENGE_TIMEOUT, text=f"{left:.0f} s left")
        for i, (name, text) in enumerate(steps):
            if i < current:
                st.markdown(f":green[:material/check_circle:] {text}")
            elif i == current and status["state"] not in ("PASSED", "FAILED"):
                st.markdown(f":blue[:material/radio_button_checked:] **{text}**")
            else:
                st.markdown(f":gray[:material/radio_button_unchecked:] :gray[{text}]")
        if status.get("restarts"):
            st.caption(f"Calibration restarted {status['restarts']}x because the face left the view or changed.")
        _tips()


def _tips():
    st.caption(":material/light_mode: Light in front of you, not behind  \n"
               ":material/center_focus_strong: Keep your whole face in view from start to finish - if it "
               "leaves the frame or another face appears, the check restarts or fails")


def presence_step(state: dict, key: str, user: dict | None, spinner: str = "Verifying..."):
    """
    Camera -> verification. The verification runs once, in a background
    thread: page reruns (camera auto-refresh, clicks) interrupt the Streamlit
    script but cannot restart or cancel the job. The page polls until done.
    Returns the verification dict once available, else None.
    """
    if state.get("verification") is not None:
        return state["verification"]
    if state.get("snap") is None:
        liveness_camera(key, state)
        return None

    job = state.get("job")
    if job is None:
        job = state["job"] = {"done": False}
        snap = state["snap"]

        def work():
            try:
                job["result"] = verify_presence(snap, user)
            except Exception as exc:  # surfaced on the next poll
                job["error"] = exc
            job["done"] = True

        threading.Thread(target=work, daemon=True).start()

    if job["done"]:
        state.pop("job")
        state.pop("snap")
        if "error" in job:
            raise job["error"]
        state["verification"] = job["result"]
        st.rerun()
    st.info(spinner, icon=":material/hourglass_top:")

    @st.fragment(run_every=0.7)
    def _wait():
        if job["done"]:
            st.rerun(scope="app")

    _wait()
    return None


# ------------------------------------------------------------------ verification pipeline

def verify_presence(snap: dict, user: dict | None):
    """
    Decision fusion. `user` is the account being claimed (None during enrolment).
    Returns a dict with every signal the evidence card shows.
    """
    v = {"liveness": snap, "liveness_passed": snap["state"] == "PASSED"}
    frames = snap["clean_frames"]

    fas = fas_engine.assess_frames(frames) if frames else {"real_prob": 0.0, "per_frame": [], "is_real": False,
                                                           "threshold": fas_engine.model_info()["threshold"],
                                                           "best_crop": None, "error": "No frames captured"}
    v["fas"] = {k: fas[k] for k in ("real_prob", "per_frame", "is_real", "threshold")}
    v["explain"] = fas_engine.explain(fas["best_crop"]) if fas["best_crop"] is not None else None

    v["embedding"] = face_engine.embed_best(frames[:5]) if frames else None
    v["match_score"] = None
    if user is not None and v["embedding"] is not None:
        v["match_score"] = biometric_template.match(v["embedding"], user["template"], user["template_key"])
    v["match_threshold"] = face_engine.MATCH_THRESHOLD
    v["match_passed"] = user is None or (v["match_score"] is not None and v["match_score"] >= face_engine.MATCH_THRESHOLD)
    v["face_found"] = v["embedding"] is not None

    _check_continuity(v, snap)

    v["fas_enforced"] = fas_engine.fas_enforced()
    challenge_fas_ok = v["continuity"]["fas"] is None or v["continuity"]["fas"] >= v["fas"]["threshold"]
    fas_ok = (fas["is_real"] and challenge_fas_ok) or not v["fas_enforced"]
    v["passed"] = (v["liveness_passed"] and fas_ok and v["match_passed"] and v["face_found"]
                   and v["continuity_passed"])
    v["reasons"] = _reasons(v)
    _save_capture(frames, v)
    e = v["explain"] or {}
    log.info("VERIFY passed=%s liveness=%s fas=%.3f (thr %.2f) frames=%s match=%s spatialEv=%s freqEv=%s "
             "hf=%s fd=%s continuity=%s reasons=%s", v["passed"], snap["state"], fas["real_prob"], fas["threshold"],
             [round(p, 2) for p in fas["per_frame"]],
             None if v["match_score"] is None else round(v["match_score"], 3),
             round(e.get("spatial_evidence", 0), 2), round(e.get("freq_evidence", 0), 2),
             round(e.get("hf_ratio", 0), 4), round(e.get("fractal_dim", 0), 3),
             {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v["continuity"].items()}, v["reasons"])
    return v


# ArcFace similarity between the faces seen during the challenges and the calibration faces.
# The same person across poses/expressions scores about 0.5-0.8; different people stay below ~0.25.
CONTINUITY_THRESHOLD = 0.35


def _check_continuity(v, snap):
    """
    Server half of the continuity check (the processor already failed the attempt on gaps and jumps):
    the frames sampled during the challenges must show the same person as the calibration frames,
    and the neutral ones among them must pass anti-spoofing too. Blocks a photo/screen during
    calibration followed by a live person (or a different person) performing the challenges.
    """
    c = v["continuity"] = {"tracked": snap.get("continuity"), "identity": None, "fas": None, "frames": 0}
    v["continuity_passed"] = True
    if not v["liveness_passed"]:
        return                                       # already rejected; nothing more to prove
    samples = snap.get("challenge_frames") or []
    c["frames"] = len(samples)
    if not samples or v["embedding"] is None:
        v["continuity_passed"] = False
        return
    spread = [f for f, _ in samples][:: max(1, len(samples) // 3)][:3]
    emb = face_engine.embed_best(spread)
    c["identity"] = None if emb is None else face_engine.cosine(emb, v["embedding"])
    if c["identity"] is None or c["identity"] < CONTINUITY_THRESHOLD:
        v["continuity_passed"] = False
    base = snap.get("baseline") or {"yaw": 0.0, "pitch": 0.0}
    neutral = [f for f, s in samples if abs(s["yaw"] - base["yaw"]) < 10 and abs(s["pitch"] - base["pitch"]) < 10
               and s["blink"] < 0.5 and s["smile"] < 0.5][:6]
    if len(neutral) >= 3:
        c["fas"] = fas_engine.assess_frames(neutral)["real_prob"]


CAPTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "captures")


def _save_capture(frames, v):
    """Keep the face crops of each attempt locally (data/ is gitignored) to calibrate on this webcam."""
    if os.getenv("VT_SAVE_CAPTURES", "1") != "1" or not frames:
        return
    folder = os.path.join(CAPTURE_DIR, time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(folder, exist_ok=True)
    for i, f in enumerate(frames):
        crop = fas_engine.crop(f)
        if crop is not None:
            cv2.imwrite(os.path.join(folder, f"crop_{i:02d}.jpg"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    with open(os.path.join(folder, "meta.json"), "w") as fh:
        json.dump({"passed": v["passed"], "fas": v["fas"], "match": v["match_score"],
                   "liveness": v["liveness"]["state"], "model": fas_engine.model_info()["model_path"]}, fh)


def _reasons(v):
    out = []
    lv = v["liveness"]
    if not v["liveness_passed"]:
        out.append(f"Active liveness failed: {lv.get('fail_reason') or 'challenge not completed'}.")
    if not v["face_found"]:
        out.append("No usable face for recognition in the captured frames.")
    if not v["fas"]["is_real"]:
        if not v.get("fas_enforced", True):
            out.append("Advisory policy: low anti-spoofing score recorded as a risk signal, not used to block.")
        e = v["explain"] or {}
        s, f = e.get("spatial_evidence", 0), e.get("freq_evidence", 0)
        src = "frequency-domain artifacts (screen pixel grid / moiré / print pattern)" if f < s \
            else "spatial cues (flat texture, reflections, edges of a screen or paper)"
        out.append(f"Passive anti-spoofing scored {v['fas']['real_prob']:.2f} "
                   f"(< {v['fas']['threshold']:.2f}); strongest evidence came from {src}.")
        hf, ref = e.get("hf_ratio"), e.get("hf_ref")
        if hf is not None and ref:
            z = (hf - ref["mean"]) / (ref["std"] + 1e-9)
            if z < -1:
                out.append(f"High-frequency energy is {abs(z):.1f}σ below live faces - fine skin detail is "
                           "missing, typical of a re-captured or compressed image.")
            elif z > 2:
                out.append(f"High-frequency energy is {z:.1f}σ above live faces - typical of screen moiré or print dots.")
    if v["match_score"] is not None and not v["match_passed"]:
        out.append(f"Face does not match this account (similarity {v['match_score']:.2f} "
                   f"< {v['match_threshold']:.2f}).")
    c = v.get("continuity") or {}
    if v["liveness_passed"] and not v.get("continuity_passed", True):
        if not c.get("frames"):
            out.append("No frames were captured during the challenges, so the same live face could not be "
                       "confirmed.")
        elif c.get("identity") is None:
            out.append("No usable face in the frames captured during the challenges.")
        else:
            out.append(f"The face during the challenges is not the face seen at the start (similarity "
                       f"{c['identity']:.2f} < {CONTINUITY_THRESHOLD:.2f}) - a photo or screen may have been "
                       "swapped for a live person.")
    if c.get("fas") is not None and c["fas"] < v["fas"]["threshold"]:
        out.append(f"Frames captured during the challenges scored {c['fas']:.2f} on anti-spoofing "
                   f"(< {v['fas']['threshold']:.2f}).")
    return out


# ------------------------------------------------------------------ evidence card

def _check(ok, text):
    icon = ":material/check_circle:" if ok else ":material/cancel:"
    colour = "green" if ok else "red"
    st.markdown(f":{colour}[{icon}] {text}")


def evidence_card(v: dict, title: str = "Presence verification"):
    with st.container(border=True):
        if v["passed"]:
            st.success(f"**{title}: verified** - live person, genuine presentation, identity confirmed.",
                       icon=":material/verified_user:")
            for r in v["reasons"]:
                st.warning(r, icon=":material/warning:")
        else:
            st.error(f"**{title}: rejected**", icon=":material/gpp_bad:")
            for r in v["reasons"]:
                st.markdown(f"- {r}")

        c1, c2, c3 = st.columns(3)
        lv = v["liveness"]
        done = sum(r["passed"] for r in lv["results"])
        c1.metric("Active liveness", f"{done}/{len(lv['challenges'])} challenges")
        c2.metric("Anti-spoofing (real)", f"{v['fas']['real_prob']:.2f}",
                  f"threshold {v['fas']['threshold']:.2f}", delta_color="off")
        if v["match_score"] is not None:
            c3.metric("Face match", f"{v['match_score']:.2f}", f"threshold {v['match_threshold']:.2f}",
                      delta_color="off")
        else:
            c3.metric("Face match", "enrolment" if v["face_found"] else "no face")

        _check(v["liveness_passed"], "Active challenges: " + ", ".join(
            f"{CHALLENGES[r['name']]} ({'%.1fs' % r['seconds'] if r['passed'] else 'timed out'})"
            for r in lv["results"]) if lv["results"] else "Active challenges: none completed")
        n = len(v["fas"]["per_frame"])
        _check(v["fas"]["is_real"], f"Spatial + frequency CNN: median REAL probability "
                                    f"{v['fas']['real_prob']:.2f} over {n} frames"
                                    + ("" if v.get("fas_enforced", True) else " *(advisory - not blocking)*"))
        if v["match_score"] is not None:
            _check(v["match_passed"], f"ArcFace match in the protected (cancelable) template domain: "
                                      f"{v['match_score']:.2f}")
        c = v.get("continuity") or {}
        if v["liveness_passed"]:
            parts = ["tracked without gaps or jumps"]
            if c.get("identity") is not None:
                parts.append(f"challenge faces match the start ({c['identity']:.2f})")
            if c.get("fas") is not None:
                parts.append(f"challenge frames anti-spoofing {c['fas']:.2f}")
            _check(v.get("continuity_passed", True), "Same live face throughout: " + ", ".join(parts))

        with st.expander("Why? Explainable-AI evidence", expanded=not v["passed"]):
            explain_panel(v.get("explain"), lv, v["fas"]["per_frame"])


def explain_panel(e, liveness=None, per_frame=None):
    if e is None:
        st.info("No face crop available to explain.")
        return
    a, b, c = st.columns(3)
    a.image(e["gradcam_spatial"], caption=f"Grad-CAM, spatial branch (regions supporting {e['predicted']})",
            width="stretch")
    b.image(e["gradcam_freq"], caption="Grad-CAM, frequency branch over the FFT spectrum", width="stretch")
    with c:
        fig = go.Figure(go.Bar(
            x=[e["spatial_evidence"], e["freq_evidence"]], y=["Spatial (RGB)", "Frequency (FFT)"],
            orientation="h", marker_color=[ACCENT if x >= 0 else BAD for x in (e["spatial_evidence"], e["freq_evidence"])],
        ))
        fig.update_layout(title=dict(text="Branch evidence (+ REAL / − SPOOF)", font=dict(size=13)),
                          height=230, margin=dict(l=10, r=10, t=40, b=10), xaxis=dict(zeroline=True))
        st.plotly_chart(fig, config={"displayModeBar": False})
        st.caption("Gradient × activation on the fused 1024-D feature vector: how strongly each branch "
                   "pushed the decision.")

    d, f = st.columns(2)
    with d:
        fig = go.Figure()
        if e.get("profile_ref"):
            fig.add_trace(go.Scatter(x=e["profile_freqs"], y=e["profile_ref"], name="Live faces (training mean)",
                                     line=dict(color=MUTED, dash="dash")))
        fig.add_trace(go.Scatter(x=e["profile_freqs"], y=e["profile"], name="This face", line=dict(color=ACCENT)))
        fig.update_layout(title=dict(text="Radial frequency profile", font=dict(size=13)), height=260,
                          margin=dict(l=10, r=10, t=40, b=10), xaxis_title="frequency (fraction of Nyquist)",
                          yaxis_title="log power", legend=dict(orientation="h", y=-0.35))
        st.plotly_chart(fig, config={"displayModeBar": False})
    with f:
        fd, hf = e["fractal_dim"], e["hf_ratio"]
        fd_ref, hf_ref = e.get("fd_ref"), e.get("hf_ref")
        st.markdown("**Interpretable texture signals**")
        st.markdown(f"Fractal dimension (box counting): **{fd:.3f}**" +
                    (f"  \nlive faces: {fd_ref['mean']:.3f} ± {fd_ref['std']:.3f}" if fd_ref else ""))
        st.markdown(f"High-frequency energy: **{hf:.4f}**" +
                    (f"  \nlive faces: {hf_ref['mean']:.4f} ± {hf_ref['std']:.4f}" if hf_ref else ""))
        st.caption("Re-captured faces lose fine skin texture (blur, compression) or gain periodic patterns "
                   "(screen grid, print dots); both move these numbers away from the live range.")
        if per_frame:
            st.markdown("**Per-frame REAL probability**")
            st.bar_chart(np.array(per_frame), height=110, color=ACCENT)

    if liveness and liveness.get("timeline"):
        liveness_timeline(liveness)


def liveness_timeline(lv):
    tl = lv["timeline"]
    t = [p["t"] for p in tl]
    fig = go.Figure()
    for key, name, colour in (("blink", "eye closure", "#2563eb"), ("smile", "smile", "#d97706")):
        fig.add_trace(go.Scatter(x=t, y=[p[key] for p in tl], name=name, line=dict(color=colour)))
    base = lv.get("baseline") or {"yaw": 0, "pitch": 0}
    for key, name, colour in (("yaw", "yaw Δ (°)", ACCENT), ("pitch", "pitch Δ (°)", "#7c3aed")):
        fig.add_trace(go.Scatter(x=t, y=[p[key] - base[key] for p in tl], name=name, yaxis="y2",
                                 line=dict(color=colour, dash="dot")))
    # shade each phase
    start = 0
    for i in range(1, len(tl) + 1):
        if i == len(tl) or tl[i]["phase"] != tl[start]["phase"]:
            phase = tl[start]["phase"]
            fig.add_vrect(x0=tl[start]["t"], x1=tl[i - 1]["t"], fillcolor="#94a3b8" if phase == "CALIBRATE" else ACCENT,
                          opacity=0.08, line_width=0, annotation_text=CHALLENGES.get(phase, "calibration"),
                          annotation_position="top left", annotation_font_size=10)
            start = i
    fig.update_layout(title=dict(text="What the liveness verifier saw", font=dict(size=13)), height=300,
                      margin=dict(l=10, r=10, t=40, b=10), xaxis_title="seconds",
                      yaxis=dict(title="score (0-1)", range=[0, 1.05]),
                      yaxis2=dict(title="degrees from your neutral pose", overlaying="y", side="right"),
                      legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, config={"displayModeBar": False})
