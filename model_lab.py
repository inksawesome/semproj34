"""
Model Lab - shows how each component works, with numbers.
"""

import glob
import json
import os
import random
import re
import time

import cv2
import numpy as np
import plotly.graph_objects as go
import streamlit as st

import biometric_template
import face_engine
import fas_engine
from ui_components import ACCENT, MUTED, explain_panel
from walk_otp import GraphConfig, generate_otp, generate_otp_with_path, generate_secret, transaction_context

BASE = os.path.dirname(os.path.abspath(__file__))


def render():
    st.title("Model Lab")
    st.caption("What each component does, how it was evaluated, and live demos.")
    sections = {":material/blur_on: Anti-spoofing": fas_tab, ":material/hub: Random-walk OTP": otp_tab,
                ":material/fingerprint: Cancelable template": template_tab}
    choice = st.segmented_control("Section", list(sections), default=list(sections)[0],
                                  label_visibility="collapsed", key="lab_section")
    sections[choice or list(sections)[0]]()


# ------------------------------------------------------------------ anti-spoofing

def fas_tab():
    info = fas_engine.model_info()
    st.markdown(
        "**Architecture.** Face crop → two ResNet-18 encoders: the *spatial* branch sees the RGB face, "
        "the *frequency* branch sees its 2-D FFT log-magnitude spectrum. The two 512-D feature vectors are "
        "concatenated → FC(256) → REAL / SPOOF. At login it scores 10 frames and takes the median.")
    st.caption(f"Loaded weights: `{info['model_path']}` · decision threshold {info['threshold']:.2f}"
               + (f" (calibrated on validation split, trained {info['trained_at']})" if info.get("trained_at") else
                  " (default - run training/train_fas_v2.py to calibrate)"))

    summary_path = os.path.join(BASE, "reports", "summary.json")
    if os.path.exists(summary_path):
        with open(summary_path) as f:
            evaluation_report(json.load(f))
    sets = {"Webcam - unseen person (deployment camera)": "heldout_webcam_scores.npy",
            "LCC-FASD - unseen subjects (public dataset)": "heldout_lcc_scores.npy"}
    sets = {k: os.path.join(BASE, "reports", v) for k, v in sets.items()
            if os.path.exists(os.path.join(BASE, "reports", v))}
    if sets:
        operating_point(sets, info)

    st.markdown("#### Try it")
    st.caption("Take a photo of yourself, then of a photo of yourself on a phone, and compare the evidence.")
    src = st.camera_input("Camera", label_visibility="collapsed") if st.toggle("Use camera") else None
    up = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    data = (src or up)
    if data is not None:
        img = cv2.cvtColor(cv2.imdecode(np.frombuffer(data.getvalue(), np.uint8), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        face = fas_engine.crop(img)
        if face is None:
            st.warning("No face found.")
            return
        with st.spinner("Explaining..."):
            e = fas_engine.explain(face)
        verdict = e["prob_real"] >= info["threshold"]
        (st.success if verdict else st.error)(f"**{e['predicted']}** - REAL probability {e['prob_real']:.3f}")
        explain_panel(e)


def evaluation_report(m):
    st.markdown("#### 1 · Which model works on our webcam? (median REAL score per clip)")
    thr = m["thresholds"]
    rows = []
    for r in m["webcam_clips"]:
        row = {"Clip": r["clip"], "Truth": "live" if r["label"] == "real" else "spoof"}
        for k in ("v1", "v2", "v3", "v4", "v5"):
            if k in r:
                row[k] = f"{r[k]['score']:.2f} {'✅' if r[k]['pass'] == (r['label'] == 'real') else '❌'}"
        row["Trained on it"] = ", ".join(r["trained_on_by"]) or "none"
        rows.append(row)
    st.dataframe(rows, hide_index=True)
    st.caption(f"✅ = correct decision at each model's threshold (v1 {thr['v1']:.2f}, v2 {thr['v2']:.2f}, "
               f"v3 {thr['v3']:.3f}, v4 {thr['v4']:.3f}, v5 {thr.get('v5', 0):.3f}). v1 = original model, v2 = retrained "
               "on LCC-FASD, v3 = + teammate's webcam videos, v4 = + all webcam captures, v5 (deployed) = + the "
               "10 Oct phone attack that fooled v4 and a real sign-in. v1 accepts phone replays; v2 rejects real "
               "webcam faces (it learned 'blurry = spoof' from LCC); v4 missed one phone held close to the camera.")

    h = m["held_out_person"]
    st.markdown("#### 2 · Generalisation to an unseen person")
    a, b, c, d = st.columns(4)
    a.metric("AUC", f"{h['AUC']:.3f}")
    b.metric("APCER (attacks accepted)", f"{h['APCER']:.0%}")
    c.metric("BPCER (genuine rejected)", f"{h['BPCER']:.0%}")
    d.metric("ACER", f"{h['ACER']:.1%}")
    st.caption(f"Model {h['model']} trained with no data from '{h['person']}', tested on {h['frames']} of their frames "
               f"(threshold {h['threshold']} from the teammate's validation clips). Frame-level; the app decides on the "
               "median of 10 frames, which is more stable.")

    st.markdown("#### 3 · LCC-FASD ablation (12 unseen subjects, AUC)")
    st.dataframe([{"Model": r["model"], "AUC ↑": r["AUC"], "Note": r["note"]} for r in m["lcc_ablation"]],
                 hide_index=True, column_config={"AUC ↑": st.column_config.NumberColumn(format="%.3f")})
    st.caption("Spatial features carry most of the signal on LCC-FASD; the frequency branch alone is weak, and the "
               "handcrafted fractal / high-frequency features are weaker still. They are kept as interpretable "
               "evidence in the explanation, not in the decision.")


def webcam_check():
    path = os.path.join(BASE, "reports", "webcam_check.json")
    if not os.path.exists(path):
        return
    with open(path) as f:
        rows = json.load(f)
    st.markdown("#### On our own webcam")
    st.dataframe([{"Attempt": r["attempt"].replace("_", " "), "Frames": r["frames"],
                   **{f"{k} (median REAL)": v["median"] for k, v in r.items() if isinstance(v, dict)}}
                  for r in rows], hide_index=True,
                 column_config={c: st.column_config.NumberColumn(format="%.3f")
                                for c in ("v1 original (median REAL)", "v2 retrained (median REAL)")})
    st.caption("Frames captured by the app during real login attempts on the demo laptop. A handful of attempts "
               "by one person - a sanity check of the deployment domain, not a benchmark.")


def operating_point(sets, info):
    """Security/convenience trade-off: choose the decision threshold, see held-out error rates."""
    st.markdown("#### Operating point")
    name = st.radio("Evaluate on", list(sets), horizontal=True, key="op_set")
    p, y = np.load(sets[name])
    if name.startswith("LCC"):
        st.caption("The threshold is calibrated for the deployment webcam. On the public dataset's attack types "
                   "(screen re-captures from other devices) it is too permissive - a cross-domain gap that more "
                   "webcam people and attack devices should close (remaining work).")
    else:
        st.caption("Frame-level rates for a person the evaluation model (v3) never trained on. The app decides on "
                   "the median of 10 frames per attempt: at clip level every attempt was classified correctly.")
    thr = st.slider("Decision threshold (REAL probability needed to pass)", 0.05, 0.95,
                    float(info["threshold"]), 0.01)
    apcer = float((p[y == 0] >= thr).mean())
    bpcer = float((p[y == 1] < thr).mean())
    a, b, c = st.columns(3)
    a.metric("APCER - attacks accepted", f"{apcer:.1%}")
    b.metric("BPCER - genuine rejected", f"{bpcer:.1%}")
    c.metric("ACER", f"{(apcer + bpcer) / 2:.1%}")
    x, y2 = st.columns(2)
    if x.button("Use this threshold", icon=":material/tune:", disabled=abs(thr - info["threshold"]) < 1e-3):
        fas_engine.set_operating_point(thr)
        st.rerun()
    if y2.button(f"Reset to calibrated ({info['calibrated_threshold']:.2f})",
                 disabled=abs(info["threshold"] - info["calibrated_threshold"]) < 1e-3):
        fas_engine.set_operating_point(None)
        st.rerun()
    st.caption("A bank would favour low APCER (block attacks) at the cost of occasional retries (BPCER). "
               "The calibrated value is the equal-error point on validation data from the deployment webcam.")
    enforce = st.toggle("Block on low anti-spoofing score (enforce)", value=fas_engine.fas_enforced(),
                        help="Off = advisory: the score and its evidence are still computed, shown and logged as a "
                             "risk signal, but only liveness + face match decide.")
    if enforce != fas_engine.fas_enforced():
        fas_engine.set_fas_enforced(enforce)
        st.rerun()


# ------------------------------------------------------------------ OTP

@st.cache_data
def _code_space(n=5000):
    return len({generate_otp(generate_secret(), counter=i)[0] for i in range(n)})


def otp_tab():
    st.markdown(
        "**Algorithm (v2).** `seed = HMAC-SHA256(K, T ‖ SHA256(context))`, T = ⌊time/30s⌋. The seed is expanded "
        "with SHA-256 in counter mode and drives a 16-step walk on a fixed 64-node small-world graph. "
        "The code is SHA-256 of the full path, dynamically truncated to 6 digits (RFC 4226). "
        "`context` = `TX|ref|amount|payee` binds a code to one transfer (PSD2-style *dynamic linking*).")
    ss = st.session_state
    ss.setdefault("lab_secret", generate_secret())
    c1, c2 = st.columns([1, 1.2])
    with c1:
        amount = st.number_input("Amount", value=5000.00, step=0.01, format="%.2f")
        payee = st.text_input("Payee", "bob@vaulttrust.com")
        ref = st.text_input("Reference", "TX-DEMO01")
        counter = int(time.time()) // 30
        ctx = transaction_context(ref, amount, payee)
        otp, _, path = generate_otp_with_path(ss.lab_secret, counter=counter, context=ctx)
        st.metric("Code for this transfer", f"{otp[:3]} {otp[3:]}")
        tampered = generate_otp(ss.lab_secret, counter=counter, context=transaction_context(ref, amount + 0.01, payee))[0]
        st.caption(f"Same key, same time, amount + $0.01 → `{tampered}` - the attacker can't reuse your code for a "
                   "modified transfer.")
        st.code(f"context = {ctx!r}\npath    = {' → '.join(map(str, path))}", language=None)
    with c2:
        st.plotly_chart(_walk_figure(path), config={"displayModeBar": False})

    st.markdown("#### Verified properties")
    a, b, c = st.columns(3)
    a.metric("Distinct codes / 5,000 secrets", f"{_code_space():,}", "v1 produced only 768 / 20,000",
             delta_color="off")
    b.metric("Python ↔ JavaScript", "12 / 12 vectors identical", "graph, walk path and code", delta_color="off")
    c.metric("Replay", "rejected", "each time-step accepted once per scope", delta_color="off")
    st.caption("v1 truncated the raw path bytes, so the 4-byte window only ever covered two node IDs "
               "(64 × 64 values): ~800 guesses would brute-force it. v2 hashes the full path. "
               "Security rests on HMAC-SHA256; the walk is the code-generation structure and is visualised on the phone.")


def _walk_figure(path):
    adj = GraphConfig().adjacency()
    n = len(adj)
    pos = [(np.cos(2 * np.pi * i / n - np.pi / 2), np.sin(2 * np.pi * i / n - np.pi / 2)) for i in range(n)]
    ex, ey = [], []
    for i, nb in enumerate(adj):
        for j in nb:
            if j > i:
                ex += [pos[i][0], pos[j][0], None]
                ey += [pos[i][1], pos[j][1], None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="#cbd5e1", width=0.7), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[pos[p][0] for p in path], y=[pos[p][1] for p in path], mode="lines+markers",
                             line=dict(color=ACCENT, width=3), marker=dict(size=9, color=ACCENT), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[p[0] for p in pos], y=[p[1] for p in pos], mode="markers",
                             marker=dict(size=6, color=MUTED), text=[str(i) for i in range(n)], hoverinfo="text"))
    fig.add_trace(go.Scatter(x=[pos[path[0]][0]], y=[pos[path[0]][1]], mode="markers",
                             marker=dict(size=14, color="#f59e0b"), name="start", hoverinfo="skip"))
    fig.update_layout(showlegend=False, height=420, margin=dict(l=0, r=0, t=0, b=0),
                      xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"))
    return fig


# ------------------------------------------------------------------ cancelable template

@st.cache_data(show_spinner="Embedding sample faces with ArcFace...")
def _sample_embeddings(per_subject=3, subjects=14):
    by_subj = {}
    for p in sorted(glob.glob(os.path.join(BASE, "LCC_FASD_development", "real", "*"))):
        m = re.search(r"_id(\d+)_", os.path.basename(p))
        if m:
            by_subj.setdefault(m.group(1), []).append(p)
    rng = random.Random(0)
    chosen = [s for s in sorted(by_subj) if len(by_subj[s]) >= per_subject]
    rng.shuffle(chosen)
    out = []
    for s in chosen[:subjects]:
        for p in rng.sample(by_subj[s], per_subject):
            img = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
            e, _ = face_engine.embed(cv2.copyMakeBorder(img, 40, 40, 40, 40, cv2.BORDER_REPLICATE))
            if e is not None:
                out.append((s, e))
    return out


def template_tab():
    st.markdown(
        "**Scheme.** A per-user 256-bit key seeds a logistic map `x ← r·x·(1−x)` (r ≈ 3.99, chaotic regime). "
        "The chaotic sequence permutes the 512-D ArcFace embedding and fills a 256×512 orthonormal projection. "
        "Only `normalise(W·e[perm])` is stored; matching happens in this protected space.")
    data = _sample_embeddings()
    if len(data) < 6:
        st.info("Not enough sample faces available for the demo.")
        return
    keys = {s: biometric_template.new_key() for s, _ in data}
    gen_o, imp_o, gen_p, imp_p = [], [], [], []
    for i in range(len(data)):
        for j in range(i + 1, len(data)):
            (si, ei), (sj, ej) = data[i], data[j]
            orig = face_engine.cosine(ei, ej)
            # verification: probe j against template of i under i's key
            prot = biometric_template.match(ej, biometric_template.protect(ei, keys[si]), keys[si])
            (gen_o if si == sj else imp_o).append(orig)
            (gen_p if si == sj else imp_p).append(prot)
    fig = go.Figure()
    for xs, name, colour, dash in ((gen_o, "same person · raw", ACCENT, "dot"), (imp_o, "different · raw", "#dc2626", "dot"),
                                   (gen_p, "same person · protected", ACCENT, "solid"),
                                   (imp_p, "different · protected", "#dc2626", "solid")):
        fig.add_trace(go.Histogram(x=xs, name=name, marker_color=colour, opacity=0.45 if dash == "dot" else 0.75,
                                   nbinsx=40, histnorm="probability"))
    fig.add_vline(x=face_engine.MATCH_THRESHOLD, line_dash="dash", annotation_text="match threshold")
    fig.update_layout(barmode="overlay", height=300, margin=dict(l=10, r=10, t=30, b=10),
                      title=dict(text=f"Similarity of {len(data)} sample faces ({len({s for s, _ in data})} people)",
                                 font=dict(size=13)),
                      xaxis_title="cosine similarity", legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, config={"displayModeBar": False})

    s0, e0 = data[0]
    k1, k2 = biometric_template.new_key(), biometric_template.new_key()
    unlink = float(np.dot(biometric_template.protect(e0, k1), biometric_template.protect(e0, k2)))
    a, b, c = st.columns(3)
    a.metric("Genuine pairs ≥ threshold", f"{np.mean(np.array(gen_p) >= face_engine.MATCH_THRESHOLD):.0%}")
    b.metric("Impostor pairs ≥ threshold", f"{np.mean(np.array(imp_p) >= face_engine.MATCH_THRESHOLD):.1%}")
    c.metric("Same face, two keys", f"{unlink:+.3f}", "unlinkable after revocation", delta_color="off")
    st.caption("Raw vs protected distributions overlap almost exactly: the transform keeps recognition accuracy. "
               "Re-keying gives an unrelated template (cosine ≈ 0), so a leaked template can be revoked. "
               "With 256 equations for 512 unknowns, the stored template cannot be inverted to a unique face embedding.")
