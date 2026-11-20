"""
Explainability and signal figures for the report, from the public LCC-FASD images (no team faces)
and from the cached liveness signals of a recorded genuine webcam video (numbers only).

    python docs/report/figures_extra.py
"""

import glob
import os
import pickle
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import fas_engine  # noqa: E402
from explainability.fractal import fractal_dimension  # noqa: E402
from explainability.frequency_explanation import radial_profile  # noqa: E402

OUT = os.path.join(ROOT, "docs", "report", "figures")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "savefig.dpi": 220, "savefig.bbox": "tight"})


def rgb(p):
    return cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)


def pick():
    real = sorted(glob.glob("LCC_FASD_development/real/*id48*"))[3]
    spoof = sorted(glob.glob("LCC_FASD_development/spoof/*id48*"))[40]
    real2 = sorted(glob.glob("LCC_FASD_development/real/*id43*"))[2]
    spoof2 = sorted(glob.glob("LCC_FASD_development/spoof/*id43*"))[60]
    return [(real, "real"), (spoof, "spoof (replay)"), (real2, "real"), (spoof2, "spoof (replay)")]


def log_spectrum(img):
    g = cv2.cvtColor(cv2.resize(img, (224, 224)), cv2.COLOR_RGB2GRAY).astype(np.float32)
    f = np.fft.fftshift(np.fft.fft2(g))
    m = np.log1p(np.abs(f))
    return (m - m.min()) / (m.max() - m.min() + 1e-9)


def fft_figure(items):
    fig, ax = plt.subplots(2, 4, figsize=(9, 4.6))
    for k, (p, lab) in enumerate(items[:2]):
        img = fas_engine.crop(rgb(p))
        img = img if img is not None else rgb(p)
        ax[0, 2 * k].imshow(cv2.resize(img, (224, 224)))
        ax[0, 2 * k].set_title(f"{lab} face crop", fontsize=8.5)
        ax[0, 2 * k + 1].imshow(log_spectrum(img), cmap="magma")
        ax[0, 2 * k + 1].set_title("log-magnitude spectrum", fontsize=8.5)
    for k, (p, lab) in enumerate(items[2:]):
        img = fas_engine.crop(rgb(p))
        img = img if img is not None else rgb(p)
        ax[1, 2 * k].imshow(cv2.resize(img, (224, 224)))
        ax[1, 2 * k].set_title(f"{lab} face crop", fontsize=8.5)
        ax[1, 2 * k + 1].imshow(log_spectrum(img), cmap="magma")
        ax[1, 2 * k + 1].set_title("log-magnitude spectrum", fontsize=8.5)
    for a in ax.flat:
        a.axis("off")
    fig.savefig(os.path.join(OUT, "fft_examples.png"))
    plt.close(fig)


def gradcam_figure(items):
    fig, ax = plt.subplots(len(items), 3, figsize=(7.4, 2.35 * len(items)))
    rows = []
    for i, (p, lab) in enumerate(items):
        img = fas_engine.crop(rgb(p))
        img = img if img is not None else rgb(p)
        e = fas_engine.explain(img)
        ax[i, 0].imshow(cv2.resize(img, (224, 224)))
        ax[i, 0].set_title(f"ground truth: {lab}", fontsize=8)
        ax[i, 1].imshow(e["gradcam_spatial"])
        ax[i, 1].set_title(f"spatial Grad-CAM — P(real) {e['prob_real']:.2f}", fontsize=8)
        ax[i, 2].imshow(e["gradcam_freq"])
        ev = f"evidence: spatial {e['spatial_evidence']:+.2f}, freq {e['freq_evidence']:+.2f}"
        ax[i, 2].set_title(f"frequency Grad-CAM\n{ev}", fontsize=7.5)
        rows.append({"label": lab, "prob_real": e["prob_real"], "spatial": e["spatial_evidence"],
                     "freq": e["freq_evidence"], "hf": e["hf_ratio"], "fd": e["fractal_dim"]})
        for a in ax[i]:
            a.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "gradcam_examples.png"))
    plt.close(fig)
    return rows


def profile_figure(items):
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
    info = fas_engine.model_info()
    for p, lab in items:
        img = fas_engine.crop(rgb(p))
        img = img if img is not None else rgb(p)
        f, prof = radial_profile(img)
        ax[0].plot(f, prof, lw=1.4, ls="-" if lab == "real" else "--", label=f"{lab}")
    ref = info.get("profile_ref")
    if ref:
        ax[0].plot(f[:len(ref)], ref, color="k", lw=2, alpha=0.6, label="mean of live training faces")
    ax[0].set_xlabel("normalised spatial frequency")
    ax[0].set_ylabel("log power")
    ax[0].set_title("Azimuthally averaged spectrum")
    ax[0].legend(fontsize=7)
    real = sorted(glob.glob("LCC_FASD_development/real/*"))[::4][:80]
    spoof = sorted(glob.glob("LCC_FASD_development/spoof/*"))[::25][:80]
    fr = [fractal_dimension(rgb(p)) for p in real]
    fs = [fractal_dimension(rgb(p)) for p in spoof]
    ax[1].hist(fr, 20, alpha=0.7, color="#3A9E6F", label=f"real (n={len(fr)})", density=True)
    ax[1].hist(fs, 20, alpha=0.7, color="#C8553D", label=f"spoof (n={len(fs)})", density=True)
    ax[1].set_xlabel("fractal dimension (differential box counting)")
    ax[1].set_ylabel("density")
    ax[1].set_title("Fractal dimension: real vs spoof overlap")
    ax[1].legend(fontsize=7)
    for a in ax:
        a.spines["top"].set_visible(False)
        a.spines["right"].set_visible(False)
    fig.savefig(os.path.join(OUT, "spectrum_fd.png"))
    plt.close(fig)
    return float(np.mean(fr)), float(np.std(fr)), float(np.mean(fs)), float(np.std(fs))


def liveness_timeline():
    """Signals of a genuine recorded webcam clip as the processor sees them (cached by eval_liveness.py)."""
    sig = pickle.load(open("reports/eval/cache/liveness_signals.pkl", "rb"))["rwitankar_real_3"]
    t = np.arange(len(sig)) / 15.0
    get = lambda k: np.array([np.nan if m is None else m[k] for m in sig])
    base_yaw = np.nanmedian(get("yaw")[:20])
    base_pitch = np.nanmedian(get("pitch")[:20])
    fig, ax = plt.subplots(2, 1, figsize=(9, 4.2), sharex=True)
    ax[0].plot(t, get("blink"), color="#3B6FB6", lw=1.2, label="eye closure (blendshape)")
    ax[0].plot(t, get("smile"), color="#E08A2E", lw=1.2, label="smile (blendshape)")
    ax[0].axhline(0.45, color="#3B6FB6", ls=":", lw=1)
    ax[0].text(t[-1], 0.47, "blink threshold 0.45", ha="right", fontsize=7, color="#3B6FB6")
    ax[0].set_ylim(0, 1)
    ax[0].legend(fontsize=7.5, loc="upper left", ncol=2)
    ax[0].set_title("Liveness signals of a genuine webcam recording (15 fps)")
    ax[1].plot(t, get("yaw") - base_yaw, color="#7B5EA7", lw=1.2, label="Δ yaw (deg)")
    ax[1].plot(t, get("pitch") - base_pitch, color="#3A9E6F", lw=1.2, label="Δ pitch (deg)")
    for y in (18, -18):
        ax[1].axhline(y, color="#7B5EA7", ls=":", lw=1)
    ax[1].text(t[-1], 19, "turn threshold ±18°", ha="right", fontsize=7, color="#7B5EA7")
    ax[1].set_xlabel("time (s)")
    ax[1].legend(fontsize=7.5, loc="lower left", ncol=2)
    for a in ax:
        a.axvspan(0, 20 / 15, color="#E8F0FB")
        a.spines["top"].set_visible(False)
        a.spines["right"].set_visible(False)
    ax[0].text(0.05, 0.9, "calibration", fontsize=7)
    fig.savefig(os.path.join(OUT, "liveness_timeline.png"))
    plt.close(fig)


if __name__ == "__main__":
    items = pick()
    fft_figure(items)
    rows = gradcam_figure(items)
    fd = profile_figure(items)
    liveness_timeline()
    import json
    json.dump({"gradcam_rows": rows, "fd_real_mean_std_spoof_mean_std": fd},
              open(os.path.join(ROOT, "reports", "eval", "xai_examples.json"), "w"), indent=1)
    print(rows, fd)
