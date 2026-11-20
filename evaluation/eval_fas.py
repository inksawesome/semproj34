"""
Component F - passive spatial + frequency anti-spoofing.

    python evaluation/eval_fas.py

Uses the outputs of the ablation training (training/train_fas_v2.py --ablation --save-all
--test-person nilay --out models/eval/fas_ablation.pth --reports-dir reports/eval/ablation):
three models trained with the same recipe, data and split - spatial branch only, frequency
branch only, and the fused two-branch network - scored on the held-out test split (12 LCC-FASD
subjects + one webcam person, Nilay, never seen in training or calibration).
Optionally also the leave-one-person-out model with Rwitankar held out (reports/eval/lopo_rwitankar).

Reports frame-level and attempt-level (median of 10 frames, as the app decides) APCER / BPCER /
ACER / AUC / EER / accuracy / precision / recall / F1, ROC curves and score distributions.
"""

import json
import os
import re
from collections import defaultdict

import numpy as np

from common import (COLORS, OUT, binary_metrics, plt_setup, roc, save_json, savefig, wilson)

NAMES = {"spatial": "Spatial only (RGB)", "freq": "Frequency only (FFT)", "fused": "Spatial + frequency (fused)"}


def attempt_groups(samples, k=10):
    """Indices grouped into attempts: consecutive frames of one clip, k at a time."""
    clips = defaultdict(list)
    for i, s in enumerate(samples):
        if s["source"] == "webcam":
            key = s["clip"]
        else:
            key = re.sub(r"_\d+\.\w+$", "", os.path.basename(s["path"]))
        clips[(key, s["label"])].append(i)

    def frame_no(i):
        m = re.search(r"_(\d+)\.\w+$", samples[i]["path"])
        return int(m.group(1)) if m else 0
    out = []
    for (key, label), idx in clips.items():
        idx = sorted(idx, key=frame_no)
        for j in range(0, len(idx), k):
            out.append((key, label, idx[j:j + k]))
    return out


def evaluate(samples, variants):
    res = {}
    groups = attempt_groups(samples)
    for mode, v in variants.items():
        probs, labels, thr = v["probs"], v["labels"], v["threshold"]
        r = {"threshold": thr}
        for part, mask in (("all", np.ones(len(samples), bool)),
                           ("lcc", np.array([s["source"] == "lcc" for s in samples])),
                           ("webcam_unseen_person", np.array([s["source"] == "webcam" for s in samples]))):
            if mask.sum() == 0:
                continue
            r[part] = binary_metrics(probs[mask], labels[mask], thr)
            r[part + "@0.5"] = binary_metrics(probs[mask], labels[mask], 0.5)
        # attempt level: median of up to 10 frames of the same clip
        for part, src in (("attempt_all", None), ("attempt_lcc", "lcc"), ("attempt_webcam", "webcam")):
            g = [(np.median(probs[idx]), lab) for key, lab, idx in groups
                 if src is None or samples[idx[0]]["source"] == src]
            if g:
                gp, gl = np.array([x for x, _ in g]), np.array([y for _, y in g])
                r[part] = binary_metrics(gp, gl, thr)
                r[part]["n_attempts"] = len(g)
        res[mode] = r
    return res


def main():
    d = os.path.join(OUT, "ablation")
    samples = json.load(open(os.path.join(d, "test_samples.json")))
    variants = {}
    for mode in ("spatial", "freq", "fused"):
        p, t = os.path.join(d, f"test_scores_{mode}.npy"), os.path.join(d, f"threshold_{mode}.json")
        if os.path.exists(p) and os.path.exists(t):
            probs, labels = np.load(p)
            variants[mode] = {"probs": probs, "labels": labels.astype(int), "threshold": json.load(open(t))["threshold"]}
    res = {"test_split": {"n": len(samples), "real": int(sum(s["label"] for s in samples)),
                          "lcc_frames": sum(s["source"] == "lcc" for s in samples),
                          "webcam_frames": sum(s["source"] == "webcam" for s in samples)},
           "variants": evaluate(samples, variants)}
    m = os.path.join(d, "metrics.json")
    if not os.path.exists(m):
        # the ablation run was stopped before its handcrafted baselines; the earlier full run used the same
        # subject split (same seed) for LCC-FASD, so its handcrafted rows are comparable
        m = "reports/metrics.json"
        res["handcrafted_source"] = m
    if os.path.exists(m):
        mm = json.load(open(m))
        res["training_log_results"] = mm["results"]
        res["splits"] = mm["splits"]

    # leave-one-person-out: Rwitankar held out (if that run exists)
    ld = os.path.join(OUT, "lopo_rwitankar")
    if os.path.exists(os.path.join(ld, "test_scores_fused.npy")):
        ls = json.load(open(os.path.join(ld, "test_samples.json")))
        probs, labels = np.load(os.path.join(ld, "test_scores_fused.npy"))
        thr = json.load(open(os.path.join(ld, "threshold_fused.json")))["threshold"]
        res["lopo_rwitankar"] = evaluate(ls, {"fused": {"probs": probs, "labels": labels.astype(int), "threshold": thr}})["fused"]
        # per clip
        clips = defaultdict(list)
        for p, s in zip(probs, ls):
            if s["source"] == "webcam":
                clips[(s["clip"], s["label"])].append(p)
        res["lopo_rwitankar"]["clips"] = {c: {"label": "real" if lab else "spoof", "median": float(np.median(v)),
                                             "passed": bool(np.median(v) >= thr), "frames": len(v)}
                                          for (c, lab), v in clips.items()}

    # deployed model history (v1-v5) from the earlier report
    if os.path.exists("reports/summary.json"):
        res["history"] = json.load(open("reports/summary.json"))
    save_json("fas_metrics.json", res)

    # ------------------------------------------------------------ figures
    plt = plt_setup()
    if variants:
        fig, ax = plt.subplots(1, 2, figsize=(10, 4))
        for a, (part, title) in zip(ax, (("lcc", "LCC-FASD test subjects (unseen)"),
                                         ("webcam", "Webcam, unseen person"))):
            for mode, v in variants.items():
                mask = np.array([s["source"] == part for s in samples])
                if len(set(v["labels"][mask])) < 2:
                    continue
                fpr, tpr, _ = roc(v["probs"][mask], v["labels"][mask])
                auc_ = res["variants"][mode]["lcc" if part == "lcc" else "webcam_unseen_person"]["AUC"]
                a.plot(fpr, tpr, lw=1.8, color=COLORS[mode], label=f"{NAMES[mode]} (AUC {auc_:.3f})")
            a.plot([0, 1], [0, 1], ":", color="#999", lw=1)
            a.set_xlabel("APCER (attacks accepted)")
            a.set_ylabel("1 − BPCER (real faces accepted)")
            a.set_title(title)
            a.legend(fontsize=8, loc="lower right")
        savefig(fig, "fas_roc_ablation.png")

        fig, ax = plt.subplots(figsize=(7.2, 3.4))
        metrics = ["APCER", "BPCER", "ACER"]
        x = np.arange(len(metrics))
        modes = list(variants)
        for k, mode in enumerate(modes):
            r = res["variants"][mode]["all"]
            vals = [100 * r[mm] for mm in metrics]
            b = ax.bar(x + (k - (len(modes) - 1) / 2) * 0.26, vals, 0.26, color=COLORS[mode], label=NAMES[mode])
            for bb, vv in zip(b, vals):
                ax.text(bb.get_x() + bb.get_width() / 2, vv + 1, f"{vv:.1f}", ha="center", fontsize=7)
        ax.set_xticks(x)
        ax.set_xticklabels(metrics)
        ax.set_ylabel("error rate (%) — lower is better")
        ax.set_title("Anti-spoofing ablation on the held-out test split (frame level)")
        ax.legend(fontsize=8)
        savefig(fig, "fas_ablation_bars.png")

        v = variants.get("fused")
        if v is not None:
            fig, ax = plt.subplots(figsize=(7, 3.2))
            bins = np.linspace(0, 1, 41)
            src = np.array([s["source"] for s in samples])
            for lab, name, c in ((1, "real", COLORS["genuine"]), (0, "spoof", COLORS["attack"])):
                for s_, ls_ in (("lcc", "-"), ("webcam", "--")):
                    sel = (v["labels"] == lab) & (src == s_)
                    if sel.any():
                        ax.hist(v["probs"][sel], bins, histtype="step", lw=1.6, ls=ls_, color=c, density=True,
                                label=f"{name}, {'LCC' if s_ == 'lcc' else 'webcam'} (n={sel.sum()})")
            ax.axvline(v["threshold"], color="k", lw=1, ls=":")
            ax.text(v["threshold"] + 0.01, ax.get_ylim()[1] * 0.92, f"threshold {v['threshold']:.3f}", fontsize=8)
            ax.set_xlabel("REAL probability (fused model)")
            ax.set_ylabel("density")
            ax.set_title("Score distributions on unseen data")
            ax.legend(fontsize=7, ncol=2)
            savefig(fig, "fas_score_distributions.png")

    h = res.get("history")
    if h:
        fig, ax = plt.subplots(figsize=(7.2, 3.4))
        clips = h["webcam_clips"]
        vers = ["v1", "v2", "v3", "v4", "v5"]
        ok = [sum(1 for c in clips if c.get(vv) and c[vv]["pass"] == (c["label"] == "real")) for vv in vers]
        tot = [sum(1 for c in clips if c.get(vv)) for vv in vers]
        lcc_auc = {r["model"].split()[0]: r["AUC"] for r in h["lcc_ablation"]}
        ax.bar(np.arange(5) - 0.18, [100 * a / b for a, b in zip(ok, tot)], 0.36, color=COLORS["F"],
               label="webcam clips decided correctly (%)")
        ax.bar(np.arange(5) + 0.18, [100 * lcc_auc.get(vv, np.nan) for vv in vers], 0.36, color=COLORS["A"],
               label="LCC-FASD test AUC (×100)")
        ax.set_xticks(range(5))
        ax.set_xticklabels([f"{vv}\n(thr {h['thresholds'][vv]:.3f})" for vv in vers], fontsize=8)
        ax.set_ylim(0, 110)
        ax.set_title("Anti-spoofing model versions")
        ax.legend(fontsize=8, loc="lower right")
        savefig(fig, "fas_versions.png")

    for mode, r in res["variants"].items():
        a = r["all"]
        print(f"{mode:8s} thr {r['threshold']:.3f} APCER {100 * a['APCER']:.1f} BPCER {100 * a['BPCER']:.1f} "
              f"ACER {100 * a['ACER']:.1f} AUC {a['AUC']:.3f} EER {100 * a['EER']:.1f} | webcam AUC "
              f"{r.get('webcam_unseen_person', {}).get('AUC', float('nan')):.3f}")
    if "lopo_rwitankar" in res:
        print("LOPO rwitankar clips", res["lopo_rwitankar"]["clips"])


if __name__ == "__main__":
    main()
