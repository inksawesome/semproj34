"""
Component A - face recognition (ArcFace) on the cancelable template.

    python evaluation/eval_face.py

Measures, on face crops from LCC-FASD (25 identities) and our webcam data (2 people):
* verification: genuine vs impostor scores, raw embedding vs protected template (ROC, EER,
  TAR @ FAR, FAR/FRR/accuracy/precision/recall/F1 at the deployed threshold 0.40);
* failure to acquire (no face found by RetinaFace);
* what ArcFace alone does with presentation attacks: a photo or replay of the enrolled person is
  scored against that person's own template (it is the right face, so A alone accepts it);
* template properties: raw-vs-protected score correlation, same face under two keys (unlinkability),
  revocation (old template vs probe under a new key).
Embeddings are cached in reports/eval/cache/arcface.npz for the system-level evaluation.
"""

import glob
import os
import re
import time
from collections import defaultdict

import numpy as np

from common import (CACHE, COLORS, binary_metrics, imread_rgb, plt_setup, roc, save_json, savefig,
                    tar_at_far, wilson)

import biometric_template as bt  # noqa: E402
import face_engine  # noqa: E402

THR = face_engine.MATCH_THRESHOLD
CACHE_FILE = os.path.join(CACHE, "arcface.npz")
ENROL_N = 5          # the app enrols from 5 frames (embed_best)


# ------------------------------------------------------------------ data

def lcc_items():
    """(path, identity, kind) for LCC-FASD crops whose file name carries a subject id."""
    items = []
    for cls, kind in (("real", "real"), ("spoof", "spoof")):
        for p in sorted(glob.glob(f"LCC_FASD_development/{cls}/*")):
            m = re.search(r"_id(\d+)_", os.path.basename(p))
            if m:
                items.append((p.replace("\\", "/"), "lcc" + m.group(1), kind))
    # keep every real image; spoof images only for identities that also have real ones (to have a
    # template to attack), all of the test-split identities and 40 per other identity
    real_ids = {i for _, i, k in items if k == "real"}
    test_ids = {"lcc42", "lcc5"}
    by = defaultdict(list)
    for it in items:
        if it[2] == "spoof" and it[1] in real_ids:
            by[it[1]].append(it)
    keep = [it for it in items if it[2] == "real"]
    rng = np.random.default_rng(0)
    for ident, lst in by.items():
        if ident in test_ids or len(lst) <= 40:
            keep += lst
        else:
            keep += [lst[i] for i in sorted(rng.choice(len(lst), 40, replace=False))]
    return keep


def webcam_items():
    import csv
    items = []
    for man in ("data/webcam/manifest.csv", "data/webcam_captures/manifest.csv"):
        for r in csv.DictReader(open(man)):
            items.append((r["path"], r["person"], "real" if r["label"] == "real" else "spoof"))
    for p in sorted(glob.glob("data/captures/20261008-210638/crop_*.jpg")):     # unseen real attempt
        items.append((p.replace("\\", "/"), "nilay", "real"))
    return items


def embeddings(paths):
    """ArcFace embedding per path (None if RetinaFace finds no face), cached on disk."""
    cache = {}
    if os.path.exists(CACHE_FILE):
        z = np.load(CACHE_FILE, allow_pickle=True)
        cache = dict(zip(z["paths"].tolist(), z["embs"]))
    todo = [p for p in paths if p not in cache]
    if todo:
        print(f"  embedding {len(todo)} crops...", flush=True)
        t0 = time.time()
        for i, p in enumerate(todo):
            e, _ = face_engine.embed(imread_rgb(p))
            cache[p] = e if e is not None else np.full(512, np.nan, np.float32)
            if i % 200 == 199:
                print(f"    {i + 1}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
        np.savez(CACHE_FILE, paths=np.array(list(cache)), embs=np.stack(list(cache.values())))
    return {p: (None if np.isnan(cache[p]).any() else cache[p]) for p in paths}


def unit(v):
    return v / np.linalg.norm(v)


# ------------------------------------------------------------------ main

def main():
    items = lcc_items() + webcam_items()
    emb = embeddings([p for p, _, _ in items])

    # failure to acquire
    fta = defaultdict(lambda: [0, 0])
    for p, ident, kind in items:
        src = "webcam" if not ident.startswith("lcc") else "lcc"
        fta[(src, kind)][1] += 1
        fta[(src, kind)][0] += emb[p] is None
    fta = {f"{s}_{k}": {"missed": a, "n": n, "rate": a / n} for (s, k), (a, n) in sorted(fta.items())}

    # enrol: first ENROL_N real crops of each identity (embed_best = normalised mean)
    real = defaultdict(list)
    spoof = defaultdict(list)
    for p, ident, kind in items:
        if emb[p] is not None:
            (real if kind == "real" else spoof)[ident].append(p)
    ids = sorted(i for i in real if len(real[i]) > ENROL_N)          # need probes beyond enrolment
    enrol = {i: unit(np.mean([emb[p] for p in real[i][:ENROL_N]], 0)) for i in ids}
    keys = {i: bt.new_key() for i in ids}
    tmpl = {i: bt.protect(enrol[i], keys[i]) for i in ids}

    probes = [(p, i) for i in ids for p in real[i][ENROL_N:]]
    g_raw, g_pro, i_raw, i_pro = [], [], [], []
    for p, i in probes:
        e = emb[p]
        g_raw.append(float(np.dot(e, enrol[i])))
        g_pro.append(bt.match(e, tmpl[i], keys[i]))
        for j in ids:
            if j != i:
                i_raw.append(float(np.dot(e, enrol[j])))
                i_pro.append(bt.match(e, tmpl[j], keys[j]))

    def verif(gs, ims):
        s = np.r_[gs, ims]
        y = np.r_[np.ones(len(gs)), np.zeros(len(ims))]
        m = binary_metrics(s, y, THR)
        m.update({"TAR@FAR=1%": tar_at_far(s, y, 0.01), "TAR@FAR=0.1%": tar_at_far(s, y, 0.001),
                  "genuine_mean": float(np.mean(gs)), "genuine_std": float(np.std(gs)),
                  "impostor_mean": float(np.mean(ims)), "impostor_std": float(np.std(ims)),
                  "impostor_max": float(np.max(ims)),
                  "FRR_ci": wilson(int((np.array(gs) < THR).sum()), len(gs)),
                  "FAR_ci": wilson(int((np.array(ims) >= THR).sum()), len(ims))})
        return m

    raw_m, pro_m = verif(g_raw, i_raw), verif(g_pro, i_pro)

    # attempt level: the app averages 5 frames per attempt
    def chunks(lst, k=5):
        return [lst[i:i + k] for i in range(0, len(lst) - k + 1, k)]
    ga, ia = [], []
    for i in ids:
        for ch in chunks(real[i][ENROL_N:]):
            e = unit(np.mean([emb[p] for p in ch], 0))
            ga.append(bt.match(e, tmpl[i], keys[i]))
            ia += [bt.match(e, tmpl[j], keys[j]) for j in ids if j != i]
    attempt_m = verif(ga, ia)

    # presentation attacks of the enrolled person against their own template (A alone)
    atk = {}
    for i in ids:
        if spoof.get(i):
            sc = [bt.match(emb[p], tmpl[i], keys[i]) for p in spoof[i]]
            atk[i] = {"n": len(sc), "accepted": int((np.array(sc) >= THR).sum()), "mean": float(np.mean(sc))}
    n_atk = sum(v["n"] for v in atk.values())
    k_atk = sum(v["accepted"] for v in atk.values())
    attacks = {"by_identity": atk, "n": n_atk, "accepted": k_atk, "rate": k_atk / n_atk,
               "ci": wilson(k_atk, n_atk)}

    # template properties
    pairs = np.array([[r, p] for r, p in zip(g_raw + i_raw, g_pro + i_pro)])
    corr = float(np.corrcoef(pairs[:, 0], pairs[:, 1])[0, 1])
    mad = float(np.mean(np.abs(pairs[:, 0] - pairs[:, 1])))
    rng = np.random.default_rng(1)
    cross_key, revoked = [], []
    for i in ids:
        for p in real[i][ENROL_N:ENROL_N + 5]:
            k2 = bt.new_key()
            cross_key.append(float(np.dot(bt.protect(emb[p], keys[i]), bt.protect(emb[p], k2))))
            revoked.append(bt.match(emb[p], tmpl[i], k2))          # old template, probe under a new key
    t0 = time.perf_counter()
    for _ in range(20):
        bt.match(emb[probes[0][0]], tmpl[probes[0][1]], keys[probes[0][1]])
    match_ms = (time.perf_counter() - t0) / 20 * 1000
    t0 = time.perf_counter()
    bt._transform.cache_clear() if hasattr(bt._transform, "cache_clear") else None
    bt.protect(emb[probes[0][0]], bt.new_key())
    keygen_ms = (time.perf_counter() - t0) * 1000
    template = {"raw_vs_protected_corr": corr, "raw_vs_protected_mean_abs_diff": mad,
                "same_face_two_keys": {"mean": float(np.mean(cross_key)), "max_abs": float(np.max(np.abs(cross_key))),
                                       "n": len(cross_key)},
                "revoked_template_scores": {"mean": float(np.mean(revoked)), "max": float(np.max(revoked)),
                                            "accepted": int((np.array(revoked) >= THR).sum()), "n": len(revoked)},
                "match_ms": match_ms, "new_key_transform_ms": keygen_ms,
                "template_bytes": int(tmpl[ids[0]].nbytes)}

    res = {"threshold": THR, "identities": len(ids),
           "identities_lcc": sum(1 for i in ids if i.startswith("lcc")),
           "probes_genuine": len(g_raw), "pairs_impostor": len(i_raw),
           "failure_to_acquire": fta, "raw": raw_m, "protected": pro_m, "attempt_level_protected": attempt_m,
           "attempt_level_n": {"genuine": len(ga), "impostor": len(ia)},
           "attacks_vs_own_template": attacks, "template": template,
           "enrolment": {i: real[i][:ENROL_N] for i in ids}}
    save_json("face_metrics.json", res)

    # ------------------------------------------------------------ figures
    plt = plt_setup()
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    bins = np.linspace(-0.3, 1.0, 66)
    for a, (gs, ims, title) in zip(ax, ((g_raw, i_raw, "Raw ArcFace embedding (512-D)"),
                                        (g_pro, i_pro, "Cancelable template (256-D)"))):
        a.hist(ims, bins, color=COLORS["attack"], alpha=0.75, density=True, label=f"impostor pairs (n={len(ims):,})")
        a.hist(gs, bins, color=COLORS["genuine"], alpha=0.75, density=True, label=f"genuine pairs (n={len(gs):,})")
        a.axvline(THR, color="k", ls="--", lw=1)
        a.text(THR + 0.01, a.get_ylim()[1] * 0.9, f"threshold {THR:.2f}", fontsize=8)
        a.set_title(title)
        a.set_xlabel("cosine similarity")
        a.set_ylabel("density")
        a.legend(fontsize=8, loc="upper left")
    savefig(fig, "face_score_distributions.png")

    fig, ax = plt.subplots(figsize=(5, 4))
    for gs, ims, lab, c in ((g_raw, i_raw, "raw embedding", COLORS["A"]), (g_pro, i_pro, "protected template", COLORS["F"])):
        s = np.r_[gs, ims]
        y = np.r_[np.ones(len(gs)), np.zeros(len(ims))]
        fpr, tpr, _ = roc(s, y)
        ax.plot(np.maximum(fpr, 1e-5), tpr, color=c, lw=1.8, label=f"{lab} (EER {100 * binary_metrics(s, y, THR)['EER']:.2f} %)")
    ax.set_xscale("log")
    ax.set_xlim(1e-4, 1)
    ax.set_xlabel("false accept rate (log)")
    ax.set_ylabel("true accept rate")
    ax.set_title("ArcFace verification ROC")
    ax.legend(loc="lower right", fontsize=8)
    savefig(fig, "face_roc.png")

    fig, ax = plt.subplots(figsize=(4.4, 4))
    ax.scatter(i_raw, i_pro, s=3, alpha=0.25, color=COLORS["attack"], label="impostor")
    ax.scatter(g_raw, g_pro, s=6, alpha=0.6, color=COLORS["genuine"], label="genuine")
    ax.plot([-0.3, 1], [-0.3, 1], "k--", lw=0.8)
    ax.set_xlabel("raw cosine (512-D)")
    ax.set_ylabel("protected cosine (256-D)")
    ax.set_title(f"Raw vs protected score (r = {corr:.3f})")
    ax.legend(fontsize=8, loc="upper left")
    savefig(fig, "template_raw_vs_protected.png")

    print(f"identities {len(ids)}, genuine {len(g_raw)}, impostor {len(i_raw)}")
    for k, m in (("raw", raw_m), ("protected", pro_m), ("attempt", attempt_m)):
        print(f"  {k:10s} EER {100 * m['EER']:.2f}%  FAR {100 * m['FAR']:.3f}%  FRR {100 * m['FRR']:.2f}%  "
              f"acc {100 * m['accuracy']:.2f}%  F1 {m['f1']:.4f}  AUC {m['AUC']:.4f}")
    print(f"  attacks vs own template accepted: {k_atk}/{n_atk} ({100 * k_atk / n_atk:.1f}%)")
    print(f"  template corr {corr:.3f}, two keys {np.mean(cross_key):.3f}, revoked max {np.max(revoked):.3f}")
    print("  FTA", fta)


if __name__ == "__main__":
    main()
