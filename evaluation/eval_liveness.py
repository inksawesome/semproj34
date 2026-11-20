"""
Component L - active liveness (challenge-response + continuity) on recorded video.

    python evaluation/eval_liveness.py

The deployed LivenessProcessor is driven offline exactly as the WebRTC stream drives it (mirrored
frames, 15 fps, the processor's own state machine and thresholds); only the clock is replaced by the
video clock. MediaPipe signals of each video frame are computed once and cached.

Experiments
1. Per-challenge achievability within the 9 s limit, from many start points, on genuine webcam
   videos (natural behaviour) and on phone replays of the same person.
2. Random challenge pairs (all 20 ordered pairs of distinct challenges) on the replay videos
   -> probability that a replay passes L.
3. Photo attacks: a face photo held still, and a photo the attacker tilts (perspective warp) in the
   direction asked, to fake head turns / looking up.
4. Swap attacks: spoof (phone replay) frames until calibration completes, then a gap of g seconds,
   then the live person; with and without the continuity rules (pre-11-Oct behaviour), plus an
   "aligned" stress test where the live face appears exactly where the spoof face was.
5. Field trial: presence decisions logged by the app (audit table) 8-12 Oct 2026.
"""

import os
import pickle
import random
import sqlite3
import types
from collections import Counter, defaultdict

import cv2
import numpy as np

from common import CACHE, COLORS, plt_setup, save_json, savefig, wilson

import liveness_engine as le  # noqa: E402

FPS = 15.0
SIZE = (640, 360)
VIDEOS = {"rwitankar_real_1": "genuine", "rwitankar_real_2": "genuine", "rwitankar_real_3": "genuine",
          "rwitankar_phone_1": "replay", "rwitankar_phone_2": "replay"}
NAMES = list(le.CHALLENGES)
SIG_CACHE = os.path.join(CACHE, "liveness_signals.pkl")

# ------------------------------------------------------------------ offline driver

CLOCK = [1000.0]
le.time = types.SimpleNamespace(time=lambda: CLOCK[0])
_real_measure = le.measure
CUR = {"m": None}
le.measure = lambda rgb: CUR["m"]          # the driver supplies the (cached) signals of each frame
DUMMY = np.zeros((72, 128, 3), np.uint8)


class _Frame:
    def to_ndarray(self, format="bgr24"):
        return DUMMY


def drive(next_m, challenges, max_frames=600):
    """Run one attempt. next_m(processor) returns the signals of the next frame (None = no face),
    or raises StopIteration when the source ends."""
    p = le.LivenessProcessor()
    p.challenges = list(challenges)
    n = 0
    try:
        while p.state not in ("PASSED", "FAILED") and n < max_frames:
            m = next_m(p)
            CLOCK[0] += 1 / FPS
            CUR["m"] = m
            p.recv(_Frame())
            n += 1
    except StopIteration:
        pass
    calib_t = None
    for r in p.timeline:
        if r["phase"] != "CALIBRATE":
            calib_t = r["t"]
            break
    return {"state": p.state if p.state in ("PASSED", "FAILED") else "ENDED", "fail_reason": p.fail_reason,
            "results": p.results, "continuity": dict(p.continuity), "frames": n, "calibrated_at": calib_t}


def from_list(ms):
    it = iter(ms)
    return lambda p: next(it)


def continuity(on):
    if on:
        le.GAP_LIMIT, le.JUMP_SHIFT, le.JUMP_SCALE = 0.7, 0.5, 1.5
    else:
        le.GAP_LIMIT, le.JUMP_SHIFT, le.JUMP_SCALE = 1e9, 1e9, 1e9


# ------------------------------------------------------------------ signals of the recorded videos

def video_signals():
    if os.path.exists(SIG_CACHE):
        return pickle.load(open(SIG_CACHE, "rb"))
    out = {}
    for name in VIDEOS:
        cap = cv2.VideoCapture(f"data/raw_videos/{name}.mp4")
        fps = cap.get(cv2.CAP_PROP_FPS)
        step = max(1, round(fps / FPS))          # 30 fps phone clips -> every 2nd frame
        ms, i = [], 0
        while True:
            ok, f = cap.read()
            if not ok:
                break
            if i % step == 0:
                rgb = cv2.cvtColor(cv2.flip(cv2.resize(f, SIZE), 1), cv2.COLOR_BGR2RGB)
                ms.append(_real_measure(rgb))
            i += 1
        out[name] = ms
        print(f"  {name}: {len(ms)} frames at 15 fps, face in {sum(m is not None for m in ms)}", flush=True)
    pickle.dump(out, open(SIG_CACHE, "wb"))
    return out


def starts(ms, need_s, every_s=1.0):
    last = len(ms) - int(need_s * FPS)
    return list(range(0, max(last, 0) + 1, int(every_s * FPS)))


# ------------------------------------------------------------------ photo attacks

def photo_pool():
    import csv
    import glob
    import re
    pool = []
    seen = set()
    for p in sorted(glob.glob("LCC_FASD_development/real/*")):
        m = re.search(r"_id(\d+)_", os.path.basename(p))
        if m and m.group(1) not in seen and len(seen) < 10:
            seen.add(m.group(1))
            pool.append(("lcc_id" + m.group(1), p))
    rows = list(csv.DictReader(open("data/webcam/manifest.csv"))) + list(csv.DictReader(open("data/webcam_captures/manifest.csv")))
    for clip in ("rwitankar_real_1", "rwitankar_real_2", "rwitankar_real_3", "nilay_real_20261008-200707",
                 "nilay_real_20261010-220846"):
        r = [x for x in rows if x["clip"] == clip]
        pool.append((clip, r[len(r) // 2]["path"]))
    return pool


def tilt(img, axis, deg):
    """Perspective view of a flat photo rotated by `deg` about its vertical ('y') or horizontal ('x') axis."""
    h, w = img.shape[:2]
    f = d = 2.0 * max(h, w)
    t = np.radians(deg)
    pts = []
    for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        if axis == "y":
            X, Y, Z = x * np.cos(t), y, x * np.sin(t)
        else:
            X, Y, Z = x, y * np.cos(t), y * np.sin(t)
        pts.append((f * X / (d + Z) + w / 2, f * Y / (d + Z) + h / 2))
    H = cv2.getPerspectiveTransform(np.float32([(0, 0), (w, 0), (w, h), (0, h)]), np.float32(pts))
    return cv2.warpPerspective(img, H, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(128, 128, 128))


def photo_frame(photo, rng, axis=None, deg=0.0):
    """Display-space (already mirrored) RGB frame with the photo held in front of the camera."""
    frame = np.full((SIZE[1], SIZE[0], 3), 128, np.uint8)
    ph = cv2.resize(photo, (int(230 * photo.shape[1] / photo.shape[0]), 230))
    if axis:
        ph = tilt(ph, axis, deg)
    dx, dy = rng.integers(-2, 3, 2)
    y0, x0 = (SIZE[1] - ph.shape[0]) // 2 + dy, (SIZE[0] - ph.shape[1]) // 2 + dx
    frame[y0:y0 + ph.shape[0], x0:x0 + ph.shape[1]] = ph
    frame = frame.astype(np.float32) * rng.uniform(0.97, 1.03) + rng.normal(0, 3, frame.shape)
    return np.clip(frame, 0, 255).astype(np.uint8)


def photo_attack(photo, challenges, tilted, seed=0):
    """Attacker holds the photo still for calibration; if `tilted`, rotates it (up to 50 degrees,
    over ~1.5 s) in whichever direction moves the on-screen yaw/pitch the way the prompt asks."""
    rng = np.random.default_rng(seed)
    state = {"k": 0, "sign": {}}

    def best_sign(axis, want):
        # adaptive attacker: try both directions once and keep the one that moves the signal the right way
        vals = {}
        for s in (1, -1):
            m = _real_measure(photo_frame(photo, rng, axis, 30 * s))
            vals[s] = None if m is None else (m["yaw"] if axis == "y" else m["pitch"])
        base = _real_measure(photo_frame(photo, rng))
        if base is None or None in vals.values():
            return 1
        b = base["yaw"] if axis == "y" else base["pitch"]
        return max((1, -1), key=lambda s: want * (vals[s] - b))

    def nxt(p):
        state["k"] += 1
        if state["k"] > 420:
            raise StopIteration
        axis, deg = None, 0.0
        if tilted and p.state == "CHALLENGE":
            name = p.challenges[p.idx]
            spec = {"TURN_LEFT": ("y", -1), "TURN_RIGHT": ("y", 1), "LOOK_UP": ("x", -1)}.get(name)
            if spec:
                axis, want = spec
                key = name
                if key not in state["sign"]:
                    state["sign"][key] = best_sign(axis, want)
                    state["t0"] = state["k"]
                if state.get("cur") != name:
                    state["cur"], state["t0"] = name, state["k"]
                ramp = min(1.0, (state["k"] - state["t0"]) / (1.5 * FPS))
                deg = 50.0 * ramp * state["sign"][key]
        return _real_measure(photo_frame(photo, rng, axis, deg))

    return drive(nxt, challenges)


# ------------------------------------------------------------------ swap attacks

def swap_attack(spoof_ms, live_ms, gap_s, aligned=False):
    """Spoof frames until calibration completes, then `gap_s` seconds without a face, then the live
    person (who can perform any challenge; recorded live clips contain blinks, so BLINK x2 is asked)."""
    it_s, it_l = iter(spoof_ms), iter(live_ms)
    st = {"gap": None, "offset": None}

    def shift(m, last):
        if m is None or last is None:
            return m
        if st["offset"] is None:
            lw, cw = last[2] - last[0], m["box"][2] - m["box"][0]
            st["offset"] = (lw / max(cw, 1), ((last[0] + last[2]) - (m["box"][0] + m["box"][2])) / 2,
                            ((last[1] + last[3]) - (m["box"][1] + m["box"][3])) / 2)
        s, dx, dy = st["offset"]
        x1, y1, x2, y2 = m["box"]
        cx, cy = (x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy
        hw, hh = (x2 - x1) * s / 2, (y2 - y1) * s / 2
        return {**m, "box": (int(cx - hw), int(cy - hh), int(cx + hw), int(cy + hh))}

    def nxt(p):
        if p.state == "CALIBRATE" and st["gap"] is None:
            m = next(it_s)
            st["last"] = m["box"] if m else st.get("last")
            return m
        if st["gap"] is None:
            st["gap"] = int(round(gap_s * FPS))
        if st["gap"] > 0:
            st["gap"] -= 1
            return None
        m = next(it_l)
        return shift(m, st.get("last")) if aligned else m

    return drive(nxt, ["BLINK", "BLINK"])


# ------------------------------------------------------------------ field trial

def field_trial():
    if not os.path.exists("vaulttrust.db"):
        return None
    c = sqlite3.connect("vaulttrust.db")
    presence = ("ENROLMENT_REJECTED", "ACCOUNT_CREATED", "LOGIN_OK", "LOGIN_REJECTED", "STEP_UP_PRESENCE_OK",
                "STEP_UP_PRESENCE_REJECTED", "REPAIR_REJECTED")
    rows = c.execute(f"select email, event, detail, created_at from audit where event in "
                     f"({','.join('?' * len(presence))}) order by id", presence).fetchall()
    import datetime
    import json
    users = {}
    attempts = []
    for email, ev, detail, t in rows:
        d = json.loads(detail or "{}")
        when = datetime.datetime.fromtimestamp(t)
        # the 10 Oct 22:09 step-up was the documented swap attack (screen recording) - not genuine
        attack = when.strftime("%m-%d %H:%M") == "10-10 22:09" and ev == "STEP_UP_PRESENCE_OK"
        u = users.setdefault(email, f"U{len(users) + 1}")
        reasons = d.get("reasons", [])
        live_fail = [r for r in reasons if r.startswith("Active liveness failed")]
        attempts.append({"user": u, "event": ev, "day": when.strftime("%d %b"), "accepted": ev in (
            "ACCOUNT_CREATED", "LOGIN_OK", "STEP_UP_PRESENCE_OK"), "liveness_failed": bool(live_fail),
            "liveness_reason": live_fail[0].split(": ", 1)[1] if live_fail else None,
            "fas_failed": any("anti-spoofing scored" in r and "Advisory" not in r for r in reasons) and ev not in (
                "LOGIN_OK", "STEP_UP_PRESENCE_OK"),
            "match_failed": any(r.startswith("Face does not match") for r in reasons),
            "attack": attack, "fas": d.get("fas"), "match": d.get("match")})
    genuine = [a for a in attempts if not a["attack"]]
    reasons = Counter(a["liveness_reason"] for a in genuine if a["liveness_failed"])
    by_reason = Counter()
    for a in genuine:
        if a["accepted"]:
            by_reason["accepted"] += 1
        elif a["liveness_failed"]:
            by_reason["liveness"] += 1
        elif a["fas_failed"]:
            by_reason["anti-spoofing"] += 1
        elif a["match_failed"]:
            by_reason["face match"] += 1
        else:
            by_reason["other"] += 1
    k = sum(not a["liveness_failed"] for a in genuine)
    per_day = defaultdict(lambda: [0, 0])
    for a in genuine:
        per_day[a["day"]][0] += not a["liveness_failed"]
        per_day[a["day"]][1] += 1
    return {"attempts": len(attempts), "users": len(users), "genuine_attempts": len(genuine),
            "liveness_pass": k, "liveness_pass_rate": k / len(genuine), "liveness_pass_ci": wilson(k, len(genuine)),
            "liveness_fail_reasons": dict(reasons), "outcome": dict(by_reason),
            "per_day": {d: {"passed": a, "n": n} for d, (a, n) in per_day.items()},
            "accepted_rate": sum(a["accepted"] for a in genuine) / len(genuine),
            "within_3_tries_estimate": 1 - (1 - k / len(genuine)) ** 3,
            "rows": attempts}


# ------------------------------------------------------------------ main

def main():
    random.seed(0)
    sig = video_signals()
    res = {"fps": FPS, "challenge_timeout_s": le.CHALLENGE_TIMEOUT, "videos": {
        k: {"kind": VIDEOS[k], "frames": len(v), "seconds": round(len(v) / FPS, 1),
            "face_frames": sum(m is not None for m in v)} for k, v in sig.items()}}
    continuity(True)

    # 1. single-challenge achievability from many start points
    print("1. per-challenge achievability", flush=True)
    ach = defaultdict(lambda: defaultdict(list))
    for name, ms in sig.items():
        for s in starts(ms, 11.0):
            for ch in NAMES:
                r = drive(from_list(ms[s:]), [ch])
                if r["state"] == "ENDED":
                    continue
                t = r["results"][-1]["seconds"] if r["results"] and r["results"][-1]["passed"] else None
                ach[VIDEOS[name]][ch].append(t)
    res["achievability"] = {kind: {ch: {"n": len(v), "passed": sum(t is not None for t in v),
                                         "rate": sum(t is not None for t in v) / len(v),
                                         "median_s": float(np.median([t for t in v if t is not None])) if any(
                                             t is not None for t in v) else None}
                                    for ch, v in d.items()} for kind, d in ach.items()}

    # 2. random challenge pairs on genuine-natural and replay videos
    print("2. challenge pairs", flush=True)
    pairs = [(a, b) for a in NAMES for b in NAMES if a != b]
    pr = defaultdict(lambda: [0, 0])
    per_pair = defaultdict(lambda: [0, 0])
    durations = []
    for name, ms in sig.items():
        for s in starts(ms, 21.0, 2.0):
            for a, b in pairs:
                r = drive(from_list(ms[s:]), [a, b])
                if r["state"] == "ENDED":
                    continue
                pr[VIDEOS[name]][0] += r["state"] == "PASSED"
                pr[VIDEOS[name]][1] += 1
                if VIDEOS[name] == "replay":
                    per_pair[f"{a}+{b}"][0] += r["state"] == "PASSED"
                    per_pair[f"{a}+{b}"][1] += 1
                if r["state"] == "PASSED" and VIDEOS[name] == "genuine":
                    durations.append(sum(x["seconds"] for x in r["results"]))
    res["pairs"] = {k: {"passed": a, "n": n, "rate": a / n, "ci": wilson(a, n)} for k, (a, n) in pr.items()}
    res["pairs_replay_by_pair"] = {k: {"passed": a, "n": n} for k, (a, n) in per_pair.items()}
    # blink-only policy (both challenges BLINK) on replays - the weak design the random challenges replace
    bo = [0, 0]
    for name, ms in sig.items():
        if VIDEOS[name] != "replay":
            continue
        for s in starts(ms, 21.0, 2.0):
            r = drive(from_list(ms[s:]), ["BLINK", "BLINK"])
            if r["state"] != "ENDED":
                bo[0] += r["state"] == "PASSED"
                bo[1] += 1
    res["replay_blink_only"] = {"passed": bo[0], "n": bo[1], "rate": bo[0] / bo[1] if bo[1] else None}

    # 3. photo attacks
    print("3. photo attacks", flush=True)
    import common
    pool = photo_pool()
    photo = {"still": defaultdict(lambda: [0, 0]), "tilted_single": defaultdict(lambda: [0, 0]),
             "tilted_pairs": [0, 0], "still_pairs": [0, 0], "photos": [k for k, _ in pool]}
    rng = random.Random(1)
    for i, (key, path) in enumerate(pool):
        img = common.imread_rgb(path)
        for ch in NAMES:
            r = photo_attack(img, [ch], tilted=True, seed=i)
            photo["tilted_single"][ch][0] += r["state"] == "PASSED"
            photo["tilted_single"][ch][1] += 1
        for a, b in rng.sample(pairs, 3):
            r = photo_attack(img, [a, b], tilted=False, seed=i)
            photo["still_pairs"][0] += r["state"] == "PASSED"
            photo["still_pairs"][1] += 1
            photo["still"][r["state"] if r["state"] == "PASSED" else (r["fail_reason"] or "no calibration")][0] += 1
            r = photo_attack(img, [a, b], tilted=True, seed=i)
            photo["tilted_pairs"][0] += r["state"] == "PASSED"
            photo["tilted_pairs"][1] += 1
        print(f"   {key}", flush=True)
    ts = photo["tilted_single"]
    p_ch = {ch: ts[ch][0] / ts[ch][1] for ch in NAMES}
    # probability a tilted photo passes a uniformly random ordered pair, from per-challenge rates
    photo["tilted_pairs_expected"] = float(np.mean([p_ch[a] * p_ch[b] for a, b in pairs]))
    photo["tilted_single"] = {ch: {"passed": a, "n": n, "rate": a / n} for ch, (a, n) in ts.items()}
    photo["still"] = {k: v[0] for k, v in photo["still"].items()}
    photo["still_pairs"] = {"passed": photo["still_pairs"][0], "n": photo["still_pairs"][1],
                            "rate": photo["still_pairs"][0] / photo["still_pairs"][1],
                            "ci": wilson(*photo["still_pairs"])}
    photo["tilted_pairs"] = {"passed": photo["tilted_pairs"][0], "n": photo["tilted_pairs"][1],
                             "rate": photo["tilted_pairs"][0] / photo["tilted_pairs"][1],
                             "ci": wilson(*photo["tilted_pairs"])}
    res["photo"] = photo

    # 4. swap attacks
    print("4. swap attacks", flush=True)
    gaps = [0.0, 0.3, 0.6, 1.0, 1.5]
    sw = {}
    reals = [k for k in sig if VIDEOS[k] == "genuine"]
    phones = [k for k in sig if VIDEOS[k] == "replay"]
    for mode in ("continuity", "no_continuity", "aligned"):
        continuity(mode != "no_continuity")
        rows = defaultdict(lambda: [0, 0])
        reasons = Counter()
        for g in gaps:
            for ph in phones:
                for s_ph in range(0, len(sig[ph]) - 60, 75):
                    for rv in reals:
                        for s_rv in (0, 75):
                            r = swap_attack(sig[ph][s_ph:], sig[rv][s_rv:], g, aligned=(mode == "aligned"))
                            if r["state"] == "ENDED":
                                continue
                            rows[g][0] += r["state"] == "PASSED"
                            rows[g][1] += 1
                            if r["state"] == "FAILED":
                                reasons[r["fail_reason"]] += 1
        tot = [sum(v[0] for v in rows.values()), sum(v[1] for v in rows.values())]
        sw[mode] = {"by_gap": {str(g): {"passed": a, "n": n, "rate": a / n} for g, (a, n) in rows.items()},
                    "passed": tot[0], "n": tot[1], "rate": tot[0] / tot[1], "ci": wilson(*tot),
                    "fail_reasons": dict(reasons)}
    continuity(True)
    res["swap"] = sw

    # genuine videos must still pass with continuity on (no false continuity breaks)
    gen = [0, 0]
    shifts, gaps_seen = [], []
    for name in reals:
        for s in starts(sig[name], 12.0, 1.0):
            r = drive(from_list(sig[name][s:]), ["BLINK", "BLINK"])
            if r["state"] == "ENDED":
                continue
            gen[0] += r["state"] == "PASSED"
            gen[1] += 1
            shifts.append(r["continuity"]["max_shift"])
            gaps_seen.append(r["continuity"]["max_gap"])
    res["genuine_with_continuity"] = {"passed": gen[0], "n": gen[1], "rate": gen[0] / gen[1],
                                      "max_shift": float(np.max(shifts)), "max_gap": float(np.max(gaps_seen))}

    # 5. field trial
    res["field"] = field_trial()
    save_json("liveness_metrics.json", res)

    # ------------------------------------------------------------ figures
    plt = plt_setup()
    labels = {"BLINK": "Blink twice", "TURN_LEFT": "Turn left", "TURN_RIGHT": "Turn right", "SMILE": "Smile",
              "LOOK_UP": "Look up"}
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    x = np.arange(len(NAMES))
    series = [("genuine", "Live person, natural behaviour (video)", COLORS["genuine"]),
              ("replay", "Phone replay of the same person", COLORS["attack"])]
    for k, (kind, lab, c) in enumerate(series):
        vals = [100 * res["achievability"].get(kind, {}).get(ch, {}).get("rate", 0) for ch in NAMES]
        ax.bar(x + (k - 0.5) * 0.28, vals, 0.28, color=c, label=lab)
    vals = [100 * res["photo"]["tilted_single"][ch]["rate"] for ch in NAMES]
    ax.bar(x + 1.5 * 0.28 - 0.28 / 2 + 0.14, vals, 0.28, color=COLORS["grey"], label="Photo tilted by the attacker")
    ax.set_xticks(x + 0.14)
    ax.set_xticklabels([labels[c] for c in NAMES])
    ax.set_ylabel("challenge satisfied within 9 s (%)")
    ax.set_ylim(0, 105)
    ax.set_title("What each kind of presentation can satisfy (single challenge)")
    ax.legend(fontsize=8, loc="upper right")
    savefig(fig, "liveness_challenge_achievability.png")

    fig, ax = plt.subplots(figsize=(7, 3.2))
    cats = ["Replay,\nblink-only", "Replay,\nrandom pair", "Photo still,\nrandom pair", "Photo tilted,\nrandom pair",
            "Swap, no\ncontinuity", "Swap, with\ncontinuity", "Swap aligned,\nwith continuity"]
    vals = [res["replay_blink_only"]["rate"], res["pairs"]["replay"]["rate"], res["photo"]["still_pairs"]["rate"],
            res["photo"]["tilted_pairs"]["rate"], sw["no_continuity"]["rate"], sw["continuity"]["rate"],
            sw["aligned"]["rate"]]
    bars = ax.bar(range(len(cats)), [100 * v for v in vals], color=[COLORS["attack"]] * 4 + [COLORS["grey"]] + [COLORS["L"]] * 2)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, 100 * v + 1.5, f"{100 * v:.0f}%", ha="center", fontsize=8)
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, fontsize=8)
    ax.set_ylabel("attacks passing liveness (%)")
    ax.set_ylim(0, 110)
    ax.set_title("Active liveness against attacks (lower is better)")
    savefig(fig, "liveness_attacks.png")

    if res["field"]:
        f = res["field"]
        fig, ax = plt.subplots(figsize=(4.6, 3.6))
        order = [k for k in ("accepted", "liveness", "anti-spoofing", "face match", "other") if f["outcome"].get(k)]
        vals = [f["outcome"][k] for k in order]
        cols = [COLORS["genuine"], COLORS["L"], COLORS["F"], COLORS["A"], COLORS["grey"]][:len(order)]
        ax.pie(vals, labels=[f"{k}\n({v})" for k, v in zip(order, vals)], colors=cols, startangle=90,
               autopct="%1.0f%%", pctdistance=0.72, textprops={"fontsize": 8}, wedgeprops={"linewidth": 1, "edgecolor": "white"})
        ax.set_title(f"Field trial: outcome of {f['genuine_attempts']} presence checks")
        ax.grid(False)
        savefig(fig, "field_trial_outcomes.png")

    print({k: res[k] for k in ("pairs", "replay_blink_only", "genuine_with_continuity")})
    print("photo still", res["photo"]["still_pairs"], "tilted", res["photo"]["tilted_pairs"],
          "expected", res["photo"]["tilted_pairs_expected"])
    print("swap", {k: (v["passed"], v["n"]) for k, v in sw.items()})
    if res["field"]:
        print("field", {k: res["field"][k] for k in ("genuine_attempts", "liveness_pass_rate", "outcome",
                                                       "liveness_fail_reasons")})


if __name__ == "__main__":
    main()
