"""
Unit-wise and combination study: A (ArcFace on the cancelable template), L (active liveness with
continuity), F (spatial + frequency anti-spoofing), and every AND-combination of them.

    python evaluation/eval_system.py     (after eval_face.py, eval_liveness.py and the FAS runs)

Attempt categories (ground truth)
  genuine   the enrolled person, live
  impostor  a different live person claiming the account (zero-effort impostor)
  photo     a photo / screen still of the enrolled person (attacker may tilt it to fake turns)
  replay    a video of the enrolled person replayed on a phone
  swap      victim's photo during calibration, the attacker's own live face for the challenges

How each cell is measured
  A and F are measured per attempt on held-out data (an attempt = up to 10 consecutive frames of one
  clip; F = median REAL probability >= threshold, A = protected-template match of the mean embedding
  of 5 frames >= 0.40), so A AND F is taken jointly per attempt. L acts on the presenter's behaviour,
  which still frames do not have, so L enters as the rate measured for that category on video
  (eval_liveness.py) and is combined assuming independence from A and F.
  F uses models that never saw the person: the fused model trained with Nilay held out (LCC test
  subjects + Nilay) and, for Rwitankar's clips, the model trained with Rwitankar held out.
  Swap: A and F see the victim's photo during calibration; when L is present the processor's continuity
  rules apply, and A / F are also applied to the challenge frames (identity at 0.35, anti-spoofing at
  the F threshold), which then show the attacker's live face.
"""

import json
import os
import re
from collections import defaultdict

import numpy as np

from common import COLORS, OUT, confusion, load_json, plt_setup, save_json, savefig, wilson
from eval_face import ENROL_N, embeddings, lcc_items, unit, webcam_items
from eval_fas import attempt_groups

import biometric_template as bt  # noqa: E402
import face_engine  # noqa: E402

THR_A = face_engine.MATCH_THRESHOLD
THR_ID = 0.35                       # ui_components.CONTINUITY_THRESHOLD
COMBOS = ["A", "L", "F", "A+L", "A+F", "L+F", "A+L+F"]
CATS = ["genuine", "impostor", "photo", "replay", "swap"]
WEIGHTS = {"genuine": 0.5, "impostor": 0.125, "photo": 0.125, "replay": 0.125, "swap": 0.125}


def fas_scorer(model_path):
    """REAL probability of face crops for a saved SpatialFrequencyFAS state dict."""
    import cv2
    import torch
    import fas_engine
    from spatial_frequency_model import SpatialFrequencyFAS
    net = SpatialFrequencyFAS(pretrained=False)
    net.load_state_dict(torch.load(model_path, map_location="cpu"))
    net.eval()

    def score(paths):
        out = []
        for i in range(0, len(paths), 32):
            b = [fas_engine.preprocess(cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)) for p in paths[i:i + 32]]
            with torch.no_grad():
                out.append(torch.softmax(net(torch.cat([x[0] for x in b]), torch.cat([x[1] for x in b])), 1)[:, 1].numpy())
        return np.concatenate(out)
    return score


def main():
    face = load_json("face_metrics.json")
    live = load_json("liveness_metrics.json")

    # ---------------- enrolment identical to eval_face.py (first ENROL_N real crops per identity)
    items = lcc_items() + webcam_items()
    emb = embeddings([p for p, _, _ in items])
    real = defaultdict(list)
    for p, ident, kind in items:
        if kind == "real" and emb[p] is not None:
            real[ident].append(p)
    ids = sorted(i for i in real if len(real[i]) > ENROL_N)
    enrol_paths = {p for i in ids for p in real[i][:ENROL_N]}
    keys = {i: bt.new_key() for i in ids}
    tmpl = {i: bt.protect(unit(np.mean([emb[p] for p in real[i][:ENROL_N]], 0)), keys[i]) for i in ids}
    ident_of = {p: i for p, i, _ in items}

    def attempt_embedding(paths):
        e = [emb[p] for p in paths if emb.get(p) is not None][:5]
        return unit(np.mean(e, 0)) if e else None

    # ---------------- F scores: ablation (Nilay held out) for LCC test + Nilay; LOPO model for Rwitankar
    abl = os.path.join(OUT, "ablation")
    samples = json.load(open(os.path.join(abl, "test_samples.json")))
    probs = np.load(os.path.join(abl, "test_scores_fused.npy"))[0]
    thr_f = json.load(open(os.path.join(abl, "threshold_fused.json")))["threshold"]
    f_score = {s["path"].replace("\\", "/"): float(p) for s, p in zip(samples, probs)}
    lopo = os.path.join(OUT, "lopo_rwitankar")
    thr_lopo = None
    if os.path.exists(os.path.join(lopo, "test_scores_fused.npy")):
        ls = json.load(open(os.path.join(lopo, "test_samples.json")))
        lp = np.load(os.path.join(lopo, "test_scores_fused.npy"))[0]
        thr_lopo = json.load(open(os.path.join(lopo, "threshold_fused.json")))["threshold"]
        for s, p in zip(ls, lp):
            if s["source"] == "webcam":
                f_score[s["path"].replace("\\", "/")] = float(p)
    extra = sorted(p for p, i, _ in items if p.startswith("data/captures/") and p not in f_score)
    if extra and os.path.exists("models/eval/fas_ablation.pth"):
        for p, s in zip(extra, fas_scorer("models/eval/fas_ablation.pth")(extra)):
            f_score[p] = float(s)

    def f_pass(paths):
        sc = [f_score[p] for p in paths if p in f_score]
        if not sc:
            return None
        t = thr_lopo if (thr_lopo is not None and "rwitankar" in paths[0]) else thr_f
        return float(np.median(sc)) >= t

    # ---------------- attempts per category with joint A, F outcomes
    att = {c: [] for c in CATS}
    # LCC test split (subjects never trained on), grouped into attempts of <= 10 frames
    for key, label, idx in attempt_groups([s for s in samples if s["source"] == "lcc"]):
        lcc = [s for s in samples if s["source"] == "lcc"]
        paths = [lcc[i]["path"].replace("\\", "/") for i in idx]
        paths = [p for p in paths if p not in enrol_paths]
        if not paths:
            continue
        ident = ident_of.get(paths[0])
        e = attempt_embedding(paths)
        fp = f_pass(paths)
        if label == 1 and ident in tmpl:
            a = e is not None and bt.match(e, tmpl[ident], keys[ident]) >= THR_A
            att["genuine"].append({"src": "lcc", "A": a, "F": fp})
            for j in ids:
                if j != ident:
                    aj = e is not None and bt.match(e, tmpl[j], keys[j]) >= THR_A
                    att["impostor"].append({"src": "lcc", "A": aj, "F": fp, "id_cont": e is not None and
                                            bt.match(e, tmpl[j], keys[j]) >= THR_ID})
        elif label == 0 and ident in tmpl:
            a = e is not None and bt.match(e, tmpl[ident], keys[ident]) >= THR_A
            att["photo"].append({"src": "lcc", "A": a, "F": fp})

    # webcam clips (Nilay captures: one attempt per clip; Rwitankar video crops: windows of 10)
    import csv
    rows = list(csv.DictReader(open("data/webcam/manifest.csv"))) + list(csv.DictReader(open("data/webcam_captures/manifest.csv")))
    by_clip = defaultdict(list)
    for r in rows:
        by_clip[(r["clip"], r["person"], r["label"])].append(r["path"])
    by_clip[("nilay_real_20261008-210638", "nilay", "real")] = sorted(
        p for p, i, k in items if p.startswith("data/captures/20261008-210638"))
    for (clip, person, label), paths in by_clip.items():
        paths = [p for p in paths if p not in enrol_paths]
        for j in range(0, len(paths) - 4, 10):
            win = paths[j:j + 10]
            e = attempt_embedding(win)
            fp = f_pass(win)
            if fp is None:
                continue
            a = e is not None and bt.match(e, tmpl[person], keys[person]) >= THR_A
            if label == "real":
                att["genuine"].append({"src": person, "A": a, "F": fp})
                for o in ids:
                    if o != person:
                        so = e is not None and bt.match(e, tmpl[o], keys[o])
                        att["impostor"].append({"src": person, "A": bool(e is not None and so >= THR_A), "F": fp,
                                                "id_cont": bool(e is not None and so >= THR_ID)})
            else:
                cat = "replay" if person == "rwitankar" else "photo"
                att[cat].append({"src": person, "A": a, "F": fp})

    # A replay and a photo present the same kind of still frames to A and F (both are re-imaged faces of the
    # enrolled person on a screen or paper); they differ only in what L sees. Without an anti-spoofing model that
    # never saw Rwitankar, his phone-replay crops cannot be scored fairly, so the replay category reuses the
    # held-out photo/screen attempts for A and F and takes its L rate from the replay videos.
    if not att["replay"]:
        att["replay"] = [dict(x) for x in att["photo"]]
        replay_from_photo = True
    else:
        replay_from_photo = False

    # ---------------- L rates per category (from eval_liveness.py)
    field = live.get("field") or {}
    p_live = field.get("liveness_pass_rate", live["genuine_with_continuity"]["rate"])
    # swap: a live attacker completes the challenges like a genuine user (p_live); the continuity rules then
    # pass a share of the spliced swaps that completed their challenges = passed(continuity) / passed(none),
    # measured on the same splices (the live clips only contain natural blinks, so some splices time out
    # in both settings and are not counted against continuity).
    sw = live["swap"]
    p_cont = sw["continuity"]["passed"] / max(1, sw["no_continuity"]["passed"])
    l_rate = {"genuine": p_live, "impostor": p_live,
              "photo": live["photo"]["tilted_pairs"]["rate"],
              "replay": live["pairs"]["replay"]["rate"],
              "swap": p_live * p_cont}
    l_rate_before_fix = dict(l_rate, swap=p_live)
    # identity continuity for swaps: attacker's live face vs victim's calibration embedding (impostor attempts)
    imp = att["impostor"]
    p_id_cont = float(np.mean([x["id_cont"] for x in imp])) if imp else 0.0
    gen_f = float(np.mean([x["F"] for x in att["genuine"]]))     # live face passing F on challenge frames

    def rate(cat, combo, design="deployed"):
        members = combo.split("+")
        lr = (l_rate if design == "deployed" else l_rate_before_fix)[cat]
        src = att["photo"] if cat == "swap" else att[cat]
        vals = []
        for x in src:
            ok = True
            if "A" in members:
                ok &= bool(x["A"])
            if "F" in members:
                ok &= bool(x["F"])
            vals.append(ok)
        r = float(np.mean(vals)) if vals else float("nan")
        if "L" in members:
            r *= lr
            if cat == "swap" and design == "deployed":
                if "A" in members:
                    r *= p_id_cont
                if "F" in members:
                    r *= gen_f
        return r

    table = {}
    for design in ("deployed", "before_continuity_fix"):
        table[design] = {}
        for combo in COMBOS:
            acc = {c: rate(c, combo, design) for c in CATS}
            n = 1000
            tp = WEIGHTS["genuine"] * n * acc["genuine"]
            fn = WEIGHTS["genuine"] * n - tp
            fp = sum(WEIGHTS[c] * n * acc[c] for c in CATS if c != "genuine")
            tn = sum(WEIGHTS[c] * n for c in CATS if c != "genuine") - fp
            m = confusion(tp, fn, fp, tn)
            m["acceptance"] = acc
            m["APCER_by_attack"] = {c: acc[c] for c in CATS if c != "genuine"}
            m["APCER_max"] = max(m["APCER_by_attack"].values())
            m["BPCER"] = 1 - acc["genuine"]
            m["ACER"] = (np.mean(list(m["APCER_by_attack"].values())) + m["BPCER"]) / 2
            table[design][combo] = m

    counts = {c: len(att[c]) for c in CATS if c != "swap"}
    counts["swap"] = len(att["photo"])
    comp_rates = {c: {"A": float(np.mean([x["A"] for x in (att["photo"] if c == "swap" else att[c])])),
                      "F": float(np.mean([x["F"] for x in (att["photo"] if c == "swap" else att[c])])),
                      "L": l_rate[c]} for c in CATS}
    for c in CATS:
        n = counts[c]
        for k in ("A", "F"):
            comp_rates[c][k + "_ci"] = wilson(round(comp_rates[c][k] * n), n)
    res = {"weights": WEIGHTS, "attempt_counts": counts, "component_acceptance": comp_rates,
           "replay_af_from_photo_attempts": replay_from_photo, "l_rates": l_rate, "l_rates_before_fix": l_rate_before_fix, "swap_continuity_pass_given_challenges": p_cont, "identity_continuity_pass_impostor": p_id_cont,
           "genuine_F_pass": gen_f, "thresholds": {"A": THR_A, "identity": THR_ID, "F": thr_f, "F_lopo": thr_lopo},
           "sources": {c: dict(sorted({x["src"]: sum(1 for y in att[c] if y["src"] == x["src"]) for x in att[c]}.items()))
                       for c in CATS if c != "swap"},
           "combinations": table}
    save_json("system_metrics.json", res)

    # ------------------------------------------------------------ figures
    plt = plt_setup()
    T = table["deployed"]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    mets = [("accuracy", "Accuracy"), ("precision", "Precision"), ("recall", "Recall"), ("f1", "F1-score")]
    x = np.arange(len(COMBOS))
    shades = ["#1F2D3D", "#3B6FB6", "#3A9E6F", "#E08A2E"]
    for k, (mk, lab) in enumerate(mets):
        vals = [100 * T[c][mk] for c in COMBOS]
        ax.bar(x + (k - 1.5) * 0.2, vals, 0.2, color=shades[k], label=lab)
    for i, c in enumerate(COMBOS):
        ax.text(i + 0.3, 100 * T[c]["f1"] + 1.5, f"{100 * T[c]['f1']:.1f}", ha="center", fontsize=7, color=shades[3])
    ax.set_xticks(x)
    ax.set_xticklabels(COMBOS)
    ax.set_ylim(0, 108)
    ax.set_ylabel("%")
    ax.set_title("Components alone and combined (genuine = positive; 50 % genuine, 50 % attacks)")
    ax.legend(ncol=4, fontsize=8, loc="upper left")
    savefig(fig, "combo_metrics_bars.png")

    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    M = np.array([[100 * T[c]["acceptance"][k] for k in CATS] for c in COMBOS])
    im = ax.imshow(M, cmap="RdYlGn_r", vmin=0, vmax=100, aspect="auto")
    M[:, 0] = 100 - M[:, 0]
    disp = np.array([[100 * T[c]["acceptance"][k] for k in CATS] for c in COMBOS])
    for i in range(len(COMBOS)):
        for j in range(len(CATS)):
            v = disp[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=8,
                    color="white" if (v > 60 or v < 15) and j > 0 else "black")
    ax.set_xticks(range(len(CATS)))
    ax.set_xticklabels(["genuine\n(accepted ↑)", "impostor", "photo", "replay", "swap"])
    ax.set_yticks(range(len(COMBOS)))
    ax.set_yticklabels(COMBOS)
    ax.grid(False)
    ax.set_title("Acceptance rate (%) by attempt type — attacks: lower is better")
    fig.colorbar(im, ax=ax, fraction=0.04)
    savefig(fig, "combo_acceptance_heatmap.png")

    fig, axes = plt.subplots(1, 4, figsize=(11, 2.9))
    for a, c in zip(axes, ["A", "L", "F", "A+L+F"]):
        m = T[c]
        cm = np.array([[m["TP"], m["FN"]], [m["FP"], m["TN"]]])
        a.imshow(cm, cmap="Blues", vmin=0, vmax=500)
        for i in range(2):
            for j in range(2):
                a.text(j, i, f"{cm[i, j]:.0f}", ha="center", va="center", fontsize=11,
                       color="white" if cm[i, j] > 250 else "black")
        a.set_xticks([0, 1])
        a.set_xticklabels(["accepted", "rejected"])
        a.set_yticks([0, 1])
        a.set_yticklabels(["genuine", "attack"])
        a.set_title(f"{c}  (acc {100 * m['accuracy']:.1f} %)")
        a.grid(False)
    fig.suptitle("Confusion matrices per 1,000 attempts (500 genuine, 500 attacks)", fontsize=10, y=1.03)
    savefig(fig, "combo_confusion.png")

    B = table["before_continuity_fix"]
    fig, ax = plt.subplots(figsize=(6.5, 3))
    cs = ["A+L", "L+F", "A+L+F"]
    ax.bar(np.arange(3) - 0.18, [100 * B[c]["acceptance"]["swap"] for c in cs], 0.36, color=COLORS["grey"],
           label="before the continuity fix")
    ax.bar(np.arange(3) + 0.18, [100 * T[c]["acceptance"]["swap"] for c in cs], 0.36, color=COLORS["L"],
           label="deployed (continuity)")
    for i, c in enumerate(cs):
        ax.text(i - 0.18, 100 * B[c]["acceptance"]["swap"] + 1, f"{100 * B[c]['acceptance']['swap']:.1f}", ha="center", fontsize=8)
        ax.text(i + 0.18, 100 * T[c]["acceptance"]["swap"] + 1, f"{100 * T[c]['acceptance']['swap']:.2f}", ha="center", fontsize=8)
    ax.set_xticks(range(3))
    ax.set_xticklabels(cs)
    ax.set_ylabel("swap attacks accepted (%)")
    ax.set_title("Effect of the continuity fix on swap attacks")
    ax.legend(fontsize=8)
    savefig(fig, "swap_fix_effect.png")

    print("counts", counts)
    print("component acceptance", {c: {k: round(v, 3) for k, v in d.items() if not k.endswith("_ci")} for c, d in comp_rates.items()})
    print(f"{'combo':7s} {'acc':>6s} {'prec':>6s} {'rec':>6s} {'F1':>6s} {'APCERmax':>8s}  " + " ".join(f"{c:>8s}" for c in CATS))
    for c in COMBOS:
        m = T[c]
        print(f"{c:7s} {100 * m['accuracy']:6.1f} {100 * m['precision']:6.1f} {100 * m['recall']:6.1f} {100 * m['f1']:6.1f} "
              f"{100 * m['APCER_max']:8.1f}  " + " ".join(f"{100 * m['acceptance'][k]:8.2f}" for k in CATS))


if __name__ == "__main__":
    main()
