"""
Shared helpers for the evaluation suite: paths, metrics, confidence intervals, plotting, caching.

Conventions used throughout the report
--------------------------------------
* Authentication view (system and combination tables): the POSITIVE class is a genuine attempt
  (the right, live person). TP = genuine accepted, FN = genuine rejected, FP = attack accepted,
  TN = attack rejected. Precision = share of accepted attempts that were genuine (security);
  recall = share of genuine attempts accepted (usability, = 1 - BPCER = TAR).
* Presentation-attack view (ISO/IEC 30107-3): APCER = attacks wrongly accepted, BPCER = bona fide
  wrongly rejected, ACER = (APCER + BPCER) / 2.
* Face verification view: FAR (impostor accepted) / FRR (genuine rejected), EER, TAR @ FAR.
"""

import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "semprojOTP", "otp_system"))
os.chdir(ROOT)

OUT = os.path.join(ROOT, "reports", "eval")
FIG = os.path.join(OUT, "figures")
CACHE = os.path.join(OUT, "cache")
for d in (OUT, FIG, CACHE):
    os.makedirs(d, exist_ok=True)

# one palette for every figure in the report
COLORS = {"A": "#3B6FB6", "L": "#E08A2E", "F": "#3A9E6F", "AL": "#7B5EA7", "AF": "#2C9DB0",
          "LF": "#C8553D", "ALF": "#1F2D3D", "genuine": "#3A9E6F", "attack": "#C8553D",
          "grey": "#8A8F98", "spatial": "#3B6FB6", "freq": "#E08A2E", "fused": "#1F2D3D"}


# ------------------------------------------------------------------ io

def save_json(name, obj):
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=_np_default)
    return path


def load_json(name):
    with open(os.path.join(OUT, name)) as f:
        return json.load(f)


def _np_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


# ------------------------------------------------------------------ metrics

def wilson(k, n, z=1.96):
    """95 % Wilson score interval for a proportion k/n."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def confusion(tp, fn, fp, tn):
    """Authentication-view metrics from (possibly fractional, expected) counts."""
    tp, fn, fp, tn = map(float, (tp, fn, fp, tn))
    n = tp + fn + fp + tn
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if prec + rec and not math.isnan(prec) else float("nan")
    far = fp / (fp + tn) if fp + tn else float("nan")      # attacks accepted
    frr = fn / (tp + fn) if tp + fn else float("nan")      # genuine rejected
    return {"TP": tp, "FN": fn, "FP": fp, "TN": tn, "accuracy": (tp + tn) / n if n else float("nan"),
            "precision": prec, "recall": rec, "f1": f1, "specificity": 1 - far if not math.isnan(far) else far,
            "FAR": far, "FRR": frr, "HTER": (far + frr) / 2}


def binary_metrics(scores, labels, thr):
    """Score >= thr means 'accept as genuine/real'. labels: 1 = genuine/real, 0 = attack/impostor."""
    s, y = np.asarray(scores, float), np.asarray(labels, int)
    acc = s >= thr
    tp, fn = int((acc & (y == 1)).sum()), int((~acc & (y == 1)).sum())
    fp, tn = int((acc & (y == 0)).sum()), int((~acc & (y == 0)).sum())
    m = confusion(tp, fn, fp, tn)
    m.update({"threshold": float(thr), "n_pos": int((y == 1).sum()), "n_neg": int((y == 0).sum()),
              "APCER": m["FAR"], "BPCER": m["FRR"], "ACER": m["HTER"]})
    if len(set(y.tolist())) == 2:
        m["AUC"] = auc(s, y)
        m["EER"], m["EER_threshold"] = eer(s, y)
    return m


def auc(scores, labels):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(labels, scores))


def roc(scores, labels):
    from sklearn.metrics import roc_curve
    fpr, tpr, thr = roc_curve(labels, scores)
    return fpr, tpr, thr


def eer(scores, labels):
    fpr, tpr, thr = roc(scores, labels)
    fnr = 1 - tpr
    i = int(np.nanargmin(np.abs(fnr - fpr)))
    return float((fpr[i] + fnr[i]) / 2), float(thr[i])


def tar_at_far(scores, labels, far):
    fpr, tpr, _ = roc(scores, labels)
    ok = fpr <= far
    return float(tpr[ok].max()) if ok.any() else 0.0


def pct(x, nd=1):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.{nd}f}"


# ------------------------------------------------------------------ plotting

def plt_setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
        "grid.linestyle": "-", "legend.frameon": False, "figure.dpi": 100, "savefig.dpi": 200,
        "savefig.bbox": "tight", "savefig.pad_inches": 0.08,
    })
    return plt


def savefig(fig, name):
    path = os.path.join(FIG, name)
    fig.savefig(path)
    import matplotlib.pyplot as plt
    plt.close(fig)
    print("  figure:", os.path.relpath(path, ROOT))
    return path


# ------------------------------------------------------------------ data helpers

def imread_rgb(path):
    import cv2
    img = cv2.imread(path)
    return None if img is None else cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def ablation_test():
    """Samples of the held-out test split (LCC test subjects + Nilay, never trained on) and the
    REAL-probability of each ablation variant, with the variant's calibrated threshold."""
    d = os.path.join(OUT, "ablation")
    samples = json.load(open(os.path.join(d, "test_samples.json")))
    out = {}
    for mode in ("fused", "spatial", "freq"):
        p = os.path.join(d, f"test_scores_{mode}.npy")
        t = os.path.join(d, f"threshold_{mode}.json")
        if os.path.exists(p) and os.path.exists(t):
            probs, labels = np.load(p)
            out[mode] = {"probs": probs, "labels": labels.astype(int), "threshold": json.load(open(t))["threshold"]}
    return samples, out
