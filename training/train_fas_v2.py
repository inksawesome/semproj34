"""
Retrain + evaluate the spatial-frequency anti-spoofing model.

    python training/train_fas_v2.py                       # fused model -> models/fas_v2.pth
    python training/train_fas_v2.py --ablation            # + spatial-only and frequency-only
    python training/train_fas_v2.py --epochs 4 --max-train 3000

What changed vs the original train_fas.py
-----------------------------------------
* Group-wise train/val/test split (by person for webcam data, by source
  video for LCC-FASD): no frame of a test person/video is ever trained on.
* Backbones are fine-tuned (layer3 + layer4), not frozen ImageNet features;
  the frequency branch can finally learn spectral patterns.
* Webcam-style augmentation applied to the crop *before* both branches:
  random framing, colour/white-balance jitter, JPEG re-compression, blur.
* Threshold calibrated on the validation split (min ACER), reported on test.
* Metrics required by the brief: APCER, BPCER, ACER, AUC, per-attack APCER,
  per-video (median) decisions, plus baselines: original v1 model,
  fractal-dimension-only and high-frequency-energy-only classifiers.
"""

import argparse
import csv
import glob
import hashlib
import json
import os
import random
import re
import sys
import time
from collections import defaultdict

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from explainability.fractal import fractal_dimension  # noqa: E402
from explainability.frequency_explanation import high_frequency_ratio, radial_profile  # noqa: E402
from fas_engine import _spatial_tf  # noqa: E402
from frequency_transform import extract_fft_spectrum  # noqa: E402
from spatial_frequency_model import SpatialFrequencyFAS  # noqa: E402

torch.set_num_threads(os.cpu_count() or 4)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ------------------------------------------------------------------ data

def load_samples():
    """Returns list of dicts: path, label (1 real / 0 spoof), group, source, attack."""
    samples = []
    for cls, label in (("real", 1), ("spoof", 0)):
        for p in glob.glob(f"LCC_FASD_development/{cls}/*"):
            name = os.path.basename(p)
            # group by subject (idNN is shared by a person's real and spoof clips);
            # files without an id are grouped by their source clip
            subj = re.search(r"_id(\d+)_", name)
            group = f"lcc_id{subj.group(1)}" if subj else "lcc_" + re.sub(r"_\d+\.\w+$", "", name)
            samples.append({"path": p, "label": label, "source": "lcc", "attack": "lcc_" + cls,
                            "group": group})
    for manifest in ("data/webcam/manifest.csv", "data/webcam_captures/manifest.csv"):
        if os.path.exists(manifest):
            with open(manifest) as f:
                for r in csv.DictReader(f):
                    samples.append({"path": r["path"], "label": int(r["label"] == "real"), "source": "webcam",
                                    "attack": r["attack"], "group": "person_" + r["person"], "clip": r["clip"]})
    return samples


def split_groups(samples, seed=0, test_person=None):
    """
    Group-wise split: no person (webcam) or subject (LCC) is in two splits.
    Webcam: `test_person` (or, with >= 3 people, a random one) is held out entirely for test.
    The remaining webcam people give their first clip of each type to validation (so the
    threshold is calibrated on the deployment camera) and the rest to training.
    """
    rng = random.Random(seed)
    split = {}
    people = sorted({s["group"] for s in samples if s["source"] == "webcam"})
    if test_person:
        split["person_" + test_person] = "test"
    elif len(people) >= 3:
        split[rng.choice(people)] = "test"
    groups = sorted({s["group"] for s in samples if s["source"] == "lcc"})
    rng.shuffle(groups)
    n = len(groups)
    for i, g in enumerate(groups):
        split[g] = "test" if i < 0.15 * n else "val" if i < 0.30 * n else "train"

    first_clip = {}
    for s in sorted(samples, key=lambda s: s.get("clip", "")):
        if s["source"] == "webcam":
            first_clip.setdefault((s["group"], s["attack"]), s["clip"])
    n_clips = defaultdict(set)
    for s in samples:
        if s["source"] == "webcam":
            n_clips[(s["group"], s["attack"])].add(s["clip"])

    out = defaultdict(list)
    for s in samples:
        part = split.get(s["group"])
        if part is None:  # webcam person used for training
            key = (s["group"], s["attack"])
            part = "val" if len(n_clips[key]) >= 2 and s["clip"] == first_clip[key] else "train"
        out[part].append(s)
    return out


def augment(img):
    h, w = img.shape[:2]
    s = random.uniform(0.78, 1.0)
    ch, cw = int(h * s), int(w * s)
    y, x = random.randint(0, h - ch), random.randint(0, w - cw)
    img = img[y:y + ch, x:x + cw]
    if random.random() < 0.5:
        img = img[:, ::-1]
    img = img.astype(np.float32)
    img = img * random.uniform(0.7, 1.3) + random.uniform(-25, 25)                 # brightness/contrast
    img = img * np.array([random.uniform(0.9, 1.1) for _ in range(3)])             # white balance
    img = np.clip(img, 0, 255).astype(np.uint8)
    if random.random() < 0.4:                                                     # distance / low-res webcam
        f = random.uniform(0.35, 0.8)
        small = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        img = cv2.resize(small, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
    if random.random() < 0.3:
        img = cv2.GaussianBlur(img, (0, 0), random.uniform(0.3, 1.5))
    if random.random() < 0.3:                                                     # backlight / dim room
        img = np.clip(255 * (img / 255.0) ** random.uniform(1.2, 1.8), 0, 255).astype(np.uint8)
    if random.random() < 0.2:                                                     # sensor noise
        img = np.clip(img + np.random.normal(0, random.uniform(2, 7), img.shape), 0, 255).astype(np.uint8)
    if random.random() < 0.6:
        q = random.randint(35, 95)
        img = cv2.imdecode(cv2.imencode(".jpg", img[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, q])[1], 1)[:, :, ::-1]
    return np.ascontiguousarray(img)


class FaceDataset(Dataset):
    def __init__(self, samples, train):
        self.samples, self.train = samples, train

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        s = self.samples[i]
        img = cv2.cvtColor(cv2.imread(s["path"]), cv2.COLOR_BGR2RGB)
        if self.train:
            img = augment(img)
        return _spatial_tf(img), extract_fft_spectrum(img, (224, 224))[0], s["label"]


# ------------------------------------------------------------------ model

class Ablated(nn.Module):
    """Same network; optionally zero one branch's features (ablation study)."""

    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self.net = SpatialFrequencyFAS(pretrained=True)

    def forward(self, xs, xf):
        f_s = torch.flatten(self.net.spatial_encoder(xs), 1)
        f_f = torch.flatten(self.net.freq_encoder(xf), 1)
        if self.mode == "spatial":
            f_f = torch.zeros_like(f_f)
        elif self.mode == "freq":
            f_s = torch.zeros_like(f_s)
        return self.net.classifier(torch.cat((f_s, f_f), 1))


def trainable(model):
    net = model.net
    for enc in (net.spatial_encoder, net.freq_encoder):
        for i, layer in enumerate(enc):
            for p in layer.parameters():
                p.requires_grad = i >= 6          # layer3 (6), layer4 (7)
    backbone = [p for enc in (net.spatial_encoder, net.freq_encoder) for p in enc.parameters() if p.requires_grad]
    return [{"params": backbone, "lr": 1e-4}, {"params": net.classifier.parameters(), "lr": 1e-3}]


def predict(model, samples, bs=32):
    model.eval()
    dl = DataLoader(FaceDataset(samples, train=False), batch_size=bs, num_workers=0)
    out = []
    with torch.no_grad():
        for xs, xf, _ in dl:
            out.append(torch.softmax(model(xs.to(DEVICE), xf.to(DEVICE)), 1)[:, 1].cpu().numpy())
    return np.concatenate(out) if out else np.array([])


# ------------------------------------------------------------------ metrics

def rates(probs, labels, thr):
    labels = np.asarray(labels)
    real, spoof = probs[labels == 1], probs[labels == 0]
    apcer = float((spoof >= thr).mean()) if len(spoof) else 0.0
    bpcer = float((real < thr).mean()) if len(real) else 0.0
    return apcer, bpcer, (apcer + bpcer) / 2


def best_threshold(probs, labels):
    """Equal-error-rate threshold (APCER = BPCER). More stable than min-ACER on a small validation
    split, and never pinned to the edge of the score range by label smoothing."""
    grid = np.linspace(0.02, 0.98, 193)
    return float(min(grid, key=lambda t: abs(rates(probs, labels, t)[0] - rates(probs, labels, t)[1])))


def auc(probs, labels):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(labels, probs)) if len(set(labels)) == 2 else float("nan")


def report(name, probs, samples, thr):
    labels = [s["label"] for s in samples]
    apcer, bpcer, acer = rates(probs, labels, thr)
    by_attack = defaultdict(list)
    for p, s in zip(probs, samples):
        if s["label"] == 0:
            by_attack[s["attack"]].append(p >= thr)
    # per-video decision: median over all frames of a group/clip
    groups = defaultdict(list)
    for p, s in zip(probs, samples):
        groups[(s["group"], s["attack"], s["label"])].append(p)
    g_probs = np.array([np.median(v) for v in groups.values()])
    g_labels = [k[2] for k in groups]
    g_apcer, g_bpcer, g_acer = rates(g_probs, g_labels, thr)
    return {"model": name, "threshold": round(thr, 3), "n": len(samples),
            "APCER": apcer, "BPCER": bpcer, "ACER": acer, "AUC": auc(probs, labels),
            "accuracy": float(np.mean((probs >= thr) == np.array(labels))),
            "APCER_by_attack": {k: float(np.mean(v)) for k, v in by_attack.items()},
            "video_level": {"n": len(g_labels), "APCER": g_apcer, "BPCER": g_bpcer, "ACER": g_acer}}


def handcrafted(splits):
    """Fractal-dimension-only and HF-energy-only logistic-regression baselines."""
    from sklearn.linear_model import LogisticRegression

    def feats(samples):
        X = []
        for s in samples:
            img = cv2.cvtColor(cv2.imread(s["path"]), cv2.COLOR_BGR2RGB)
            X.append([fractal_dimension(img), high_frequency_ratio(img)])
        return np.array(X)
    Xtr, Xva, Xte = feats(splits["train"]), feats(splits["val"]), feats(splits["test"])
    ytr, yva = [s["label"] for s in splits["train"]], [s["label"] for s in splits["val"]]
    out = []
    for name, cols in (("Fractal dimension only", [0]), ("HF energy only", [1]), ("FD + HF", [0, 1])):
        clf = LogisticRegression(class_weight="balanced").fit(Xtr[:, cols], ytr)
        thr = best_threshold(clf.predict_proba(Xva[:, cols])[:, 1], yva)
        out.append(report(name, clf.predict_proba(Xte[:, cols])[:, 1], splits["test"], thr))
    return out


# ------------------------------------------------------------------ training

def train_variant(mode, splits, epochs, max_train):
    model = Ablated(mode).to(DEVICE)
    opt = torch.optim.AdamW(trainable(model), weight_decay=1e-4)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)
    labels = [s["label"] for s in splits["train"]]
    weights = [(1.0 / labels.count(s["label"])) * (3.0 if s["source"] == "webcam" else 1.0)
               for s in splits["train"]]
    n = min(max_train, len(labels))
    sampler = WeightedRandomSampler(weights, num_samples=n, replacement=True)
    dl = DataLoader(FaceDataset(splits["train"], train=True), batch_size=16, sampler=sampler, num_workers=0)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[1e-4, 1e-3], total_steps=epochs * len(dl))

    best, best_state = 9.9, None
    for ep in range(epochs):
        model.train()
        t0, total = time.time(), 0.0
        for xs, xf, y in dl:
            opt.zero_grad()
            loss = loss_fn(model(xs.to(DEVICE), xf.to(DEVICE)), y.to(DEVICE))
            loss.backward()
            opt.step()
            sched.step()
            total += loss.item()
        vp = predict(model, splits["val"])
        vl = [s["label"] for s in splits["val"]]
        thr, acer = calibrate(vp, splits["val"])
        print(f"[{mode}] epoch {ep + 1}/{epochs} loss {total / len(dl):.4f} "
              f"val ACER {acer:.3f} AUC {auc(vp, vl):.3f} ({time.time() - t0:.0f}s)", flush=True)
        if acer <= best:
            best, best_state = acer, {k: v.detach().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    thr, _ = calibrate(predict(model, splits["val"]), splits["val"])
    return model, thr


def calibrate(probs, samples):
    """EER threshold on the webcam part of validation (deployment camera) if present, else all of it.
    Returns (threshold, ACER of the whole validation split at that threshold)."""
    labels = np.array([s["label"] for s in samples])
    cam = np.array([s["source"] == "webcam" for s in samples])
    use = cam if cam.any() and len(set(labels[cam])) == 2 else np.ones_like(cam)
    thr = best_threshold(probs[use], labels[use])
    return thr, rates(probs, labels, thr)[2]


def genuine_reference(samples, k=400):
    real = [s for s in samples if s["label"] == 1]
    random.Random(0).shuffle(real)
    fds, hfs, profs = [], [], []
    for s in real[:k]:
        img = cv2.cvtColor(cv2.imread(s["path"]), cv2.COLOR_BGR2RGB)
        fds.append(fractal_dimension(img))
        hfs.append(high_frequency_ratio(img))
        profs.append(radial_profile(img)[1])
    return {"fd_ref": {"mean": float(np.mean(fds)), "std": float(np.std(fds))},
            "hf_ref": {"mean": float(np.mean(hfs)), "std": float(np.std(hfs))},
            "profile_ref": np.mean(profs, axis=0).tolist()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--max-train", type=int, default=2400, help="samples drawn per epoch")
    ap.add_argument("--ablation", action="store_true")
    ap.add_argument("--test-person", help="webcam person held out entirely for testing")
    ap.add_argument("--out", default="models/fas_v2.pth")
    ap.add_argument("--reports-dir", default="reports", help="where metrics and test scores are written")
    ap.add_argument("--save-all", action="store_true",
                    help="also save the spatial-only / frequency-only models (<out>_<mode>.pth) and thresholds")
    args = ap.parse_args()
    rdir = args.reports_dir
    random.seed(0)
    torch.manual_seed(0)

    samples = load_samples()
    splits = split_groups(samples, test_person=args.test_person)
    summary = {k: {"n": len(v), "real": sum(s["label"] for s in v),
                   "sources": sorted({s["source"] for s in v})} for k, v in splits.items()}
    print("splits:", json.dumps(summary))
    os.makedirs("models", exist_ok=True)
    os.makedirs(rdir, exist_ok=True)
    with open(os.path.join(rdir, "test_samples.json"), "w") as f:   # per-sample metadata for later analysis
        json.dump([{k: s.get(k) for k in ("path", "label", "source", "attack", "group", "clip")}
                   for s in splits["test"]], f)

    results = []
    # Baseline: the original model (frozen ImageNet backbones, head trained on ALL of LCC-FASD,
    # so its LCC test numbers are optimistic - it has seen those images).
    v1 = Ablated("fused").to(DEVICE)
    v1.net.load_state_dict(torch.load("fas_spatial_freq.pth", map_location=DEVICE))
    results.append(report("v1 original (frozen, no split)", predict(v1, splits["test"]), splits["test"], 0.5))
    del v1

    modes = ["fused", "spatial", "freq"] if args.ablation else ["fused"]
    for mode in modes:
        model, thr = train_variant(mode, splits, args.epochs, args.max_train)
        probs = predict(model, splits["test"])
        name = {"fused": "v2 spatial + frequency", "spatial": "v2 spatial only", "freq": "v2 frequency only"}[mode]
        results.append(report(name, probs, splits["test"], thr))
        results.append(report(name + " @0.5", probs, splits["test"], 0.5))   # common operating point
        cam = [i for i, s in enumerate(splits["test"]) if s["source"] == "webcam"]
        if cam:
            results.append(report(name + " - webcam test person", probs[cam], [splits["test"][i] for i in cam], thr))
        np.save(os.path.join(rdir, f"test_scores_{mode}.npy"), np.array([probs, [s["label"] for s in splits["test"]]]))
        if args.save_all and mode != "fused":
            torch.save(model.net.state_dict(), args.out.replace(".pth", f"_{mode}.pth"))
        if args.save_all:
            with open(os.path.join(rdir, f"threshold_{mode}.json"), "w") as f:
                json.dump({"threshold": thr}, f)
        print(json.dumps(results[-1], indent=1), flush=True)
        if mode == "fused":
            torch.save(model.net.state_dict(), args.out)
            calib = {"threshold": thr, "trained_at": time.strftime("%Y-%m-%d %H:%M"),
                     "splits": summary, **genuine_reference(splits["train"])}
            with open(args.out.replace(".pth", "_calibration.json").replace("fas_v2_calibration", "fas_calibration"), "w") as f:
                json.dump(calib, f, indent=1)

    print("handcrafted baselines...", flush=True)
    results.extend(handcrafted(splits))
    with open(os.path.join(rdir, "metrics.json"), "w") as f:
        json.dump({"generated_at": time.strftime("%Y-%m-%d %H:%M"), "splits": summary, "results": results}, f, indent=1)
    print("\n{:34s} {:>7s} {:>7s} {:>7s} {:>7s}".format("model", "APCER", "BPCER", "ACER", "AUC"))
    for r in results:
        print("{:34s} {:7.3f} {:7.3f} {:7.3f} {:7.3f}".format(r["model"], r["APCER"], r["BPCER"], r["ACER"], r["AUC"]))


if __name__ == "__main__":
    main()
