"""
Latency of every component and of the full presence verification, on this laptop's CPU.

    python evaluation/eval_latency.py      (run with nothing else using the CPU)

A recorded genuine webcam video (resized to the app's 640x480 camera size) is fed through the real
LivenessProcessor; the resulting snapshot goes through the real ui_components.verify_presence()
with timers around each stage. Repeated REPS times; min / mean / max reported.
"""

import os
import statistics
import time
import types

os.environ["VT_SAVE_CAPTURES"] = "0"

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from common import COLORS, plt_setup, save_json, savefig  # noqa: E402

import biometric_template as bt  # noqa: E402
import face_engine  # noqa: E402
import fas_engine  # noqa: E402
import liveness_engine as le  # noqa: E402
import ui_components  # noqa: E402
import walk_otp as W  # noqa: E402

REPS = 5
SIZE = (640, 480)


def frames(name="rwitankar_real_1"):
    cap = cv2.VideoCapture(f"data/raw_videos/{name}.mp4")
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            return out
        out.append(cv2.resize(f, SIZE))


def snapshot(bgr_frames):
    import av
    clock = [1000.0]
    real_time = le.time
    le.time = types.SimpleNamespace(time=lambda: clock[0])
    p = le.LivenessProcessor()
    p.challenges = ["BLINK", "BLINK"]
    per_frame = []
    for f in bgr_frames:
        clock[0] += 1 / 15
        t0 = time.perf_counter()
        p.recv(av.VideoFrame.from_ndarray(f, format="bgr24"))
        per_frame.append((time.perf_counter() - t0) * 1000)
        if p.state in ("PASSED", "FAILED"):
            break
    le.time = real_time
    return p.snapshot(), per_frame


def timed(store, key, fn):
    def wrap(*a, **k):
        t0 = time.perf_counter()
        try:
            return fn(*a, **k)
        finally:
            store.setdefault(key, []).append((time.perf_counter() - t0) * 1000)
    return wrap


def main():
    vid = frames()
    # warm-up (first calls load models: reported separately)
    first = {}
    t0 = time.perf_counter()
    le.measure(cv2.cvtColor(vid[0], cv2.COLOR_BGR2RGB))
    first["mediapipe_first_call_ms"] = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    fas_engine.score_crops([fas_engine.crop(cv2.cvtColor(vid[0], cv2.COLOR_BGR2RGB))])
    first["anti_spoofing_first_call_ms"] = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    face_engine.embed(cv2.cvtColor(vid[0], cv2.COLOR_BGR2RGB))
    first["arcface_first_call_ms"] = (time.perf_counter() - t0) * 1000

    snap, per_frame = snapshot(vid)
    assert snap["state"] == "PASSED", snap["fail_reason"]
    enrol = face_engine.embed_best(snap["clean_frames"][:5])
    key = bt.new_key()
    user = {"template": bt.protect(enrol, key), "template_key": key}

    # stage timers around the real functions verify_presence calls
    orig = {"assess": fas_engine.assess_frames, "explain": fas_engine.explain, "embed_best": face_engine.embed_best,
            "match": bt.match, "crop": fas_engine.crop, "score": fas_engine.score_crops}
    runs = []
    for r in range(REPS):
        st = {}
        fas_engine.crop = timed(st, "face crop (MediaPipe)", orig["crop"])
        fas_engine.score_crops = timed(st, "anti-spoofing CNN", orig["score"])
        fas_engine.explain = timed(st, "explanation (Grad-CAM etc.)", orig["explain"])
        face_engine.embed_best = timed(st, "ArcFace (detect+align+embed)", orig["embed_best"])
        bt.match = timed(st, "template match", orig["match"])
        t0 = time.perf_counter()
        v = ui_components.verify_presence(snap, user)
        total = (time.perf_counter() - t0) * 1000
        runs.append({"total": total, **{k: sum(x) for k, x in st.items()}})
    fas_engine.crop, fas_engine.score_crops, fas_engine.explain = orig["crop"], orig["score"], orig["explain"]
    face_engine.embed_best, bt.match = orig["embed_best"], orig["match"]

    stages = {k: {"min": min(r[k] for r in runs), "mean": statistics.mean(r[k] for r in runs),
                  "max": max(r[k] for r in runs)} for k in runs[0]}
    rgb = [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in vid[:40:4]]

    def bench(fn, reps=5):
        ts = []
        for _ in range(reps):
            t0 = time.perf_counter()
            fn()
            ts.append((time.perf_counter() - t0) * 1000)
        return statistics.mean(ts)
    crops = [fas_engine.crop(f) for f in rgb]
    unit = {
        "liveness_per_frame_ms (landmarks + overlay)": statistics.mean(per_frame),
        "mediapipe_landmarks_per_frame_ms": bench(lambda: le.measure(rgb[0]), 20),
        "face_crop_per_frame_ms": bench(lambda: fas_engine.crop(rgb[0]), 10),
        "anti_spoofing_1_crop_ms": bench(lambda: fas_engine.score_crops(crops[:1]), 10),
        "anti_spoofing_10_crops_ms": bench(lambda: fas_engine.score_crops(crops), 5),
        "anti_spoofing_10_frames_incl_crop_ms": bench(lambda: fas_engine.assess_frames(rgb), 3),
        "arcface_per_frame_640x480_ms": bench(lambda: face_engine.embed(rgb[0]), 10),
        "arcface_5_frames_ms": bench(lambda: face_engine.embed_best(rgb[:5]), 3),
        "explanation_ms": bench(lambda: fas_engine.explain(crops[0]), 3),
        "template_protect_cached_key_ms": bench(lambda: bt.protect(enrol, key), 200),
        "template_new_key_ms": bench(lambda: bt._transform.__wrapped__(os.urandom(32)), 5),
        "otp_generate_ms": bench(lambda: W.generate_otp(b"k" * 32, context="TX|A|1|b"), 500),
    }
    live = {"challenge_seconds": [r["seconds"] for r in snap["results"]],
            "calibration_frames": le.CALIBRATION_FRAMES, "calibration_seconds_at_15fps": le.CALIBRATION_FRAMES / 15}

    # server compute per component combination (sequential stages of verify_presence)
    a = unit["arcface_5_frames_ms"] + unit["template_protect_cached_key_ms"]
    f = unit["anti_spoofing_10_frames_incl_crop_ms"]
    lv = unit["liveness_per_frame_ms (landmarks + overlay)"]
    cont = stages.get("ArcFace (detect+align+embed)", {}).get("mean", 0) - a + 1e-9
    combos = {"A": a, "L": 0.0, "F": f, "A+L": a, "A+F": a + f, "L+F": f, "A+L+F": stages["total"]["mean"]}
    res = {"reps": REPS, "camera": f"{SIZE[0]}x{SIZE[1]} @ 15 fps", "first_call": first, "unit": unit,
           "verify_presence_stages": stages, "liveness": live, "server_compute_by_combination_ms": combos,
           "note": "L runs on every camera frame while the user responds (per-frame cost above); its "
                   "wall-clock time is the user's response time, not compute. A+L+F = full verify_presence "
                   "(includes explanation and the continuity checks).",
           "continuity_extra_ms_estimate": max(cont, 0.0), "cpu": os.cpu_count()}
    save_json("latency_metrics.json", res)

    plt = plt_setup()
    parts = {k: v["mean"] for k, v in stages.items() if k != "total"}
    other = stages["total"]["mean"] - sum(parts.values())
    if other > 1:
        parts["fusion, reasons, logging"] = other
    order = sorted(parts, key=parts.get, reverse=True)
    cols = [COLORS["A"], COLORS["F"], COLORS["L"], COLORS["AF"], COLORS["grey"], COLORS["AL"], COLORS["LF"]]
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    w, _, _ = ax.pie([parts[k] for k in order], colors=cols[:len(order)], startangle=90, counterclock=False,
                     autopct=lambda p: f"{p:.0f}%" if p >= 4 else "", pctdistance=0.75,
                     wedgeprops={"linewidth": 1, "edgecolor": "white"}, textprops={"fontsize": 8, "color": "white"})
    ax.legend(w, [f"{k} — {parts[k]:.0f} ms" for k in order], loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8)
    ax.set_title(f"Presence verification compute: {stages['total']['mean'] / 1000:.2f} s mean (CPU)")
    ax.grid(False)
    savefig(fig, "latency_pie.png")

    print("stages", {k: round(v["mean"]) for k, v in stages.items()})
    print("unit", {k: round(v, 2) for k, v in unit.items()})
    print("first", first)
    print("liveness", live)


if __name__ == "__main__":
    main()
