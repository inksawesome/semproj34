"""
Build reports/summary.json (shown in the Model Lab) from the training runs of 2026-10-08
and a clip-level comparison of every model on the webcam data.

    python tools/build_report.py
"""
import csv
import glob
import json
import os
import sys

import cv2
import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import fas_engine  # noqa: E402
from spatial_frequency_model import SpatialFrequencyFAS  # noqa: E402

# Numbers copied from reports_train_lcc.log, reports_train_v3.log, reports_train_v4.log
LCC_ABLATION = [  # LCC-FASD test split: 12 unseen subjects, threshold-free AUC
    {"model": "v1 original (frozen ImageNet, head trained on ALL images)", "AUC": 1.000,
     "note": "memorised - these test images were in its training data"},
    {"model": "v2 spatial + frequency (LCC only)", "AUC": 0.970, "note": "@0.5: APCER 21.5%, BPCER 4.9%"},
    {"model": "v2 spatial only", "AUC": 0.986, "note": "ablation"},
    {"model": "v2 frequency only", "AUC": 0.736, "note": "ablation"},
    {"model": "High-frequency energy only (logistic regression)", "AUC": 0.691, "note": "handcrafted baseline"},
    {"model": "Fractal dimension only (logistic regression)", "AUC": 0.523, "note": "handcrafted baseline"},
    {"model": "v3 (+ teammate webcam data)", "AUC": 0.832, "note": "trades LCC accuracy for webcam accuracy"},
    {"model": "v4 (+ all webcam data)", "AUC": 0.903, "note": ""},
    {"model": "v5 deployed (+ 10 Oct phone attack, real sign-in)", "AUC": 0.944, "note": "11 Oct"},
]
HELD_OUT = {  # v3 trained without any data from this person
    "model": "v3", "person": "nilay", "frames": 50, "threshold": 0.235,
    "APCER": 0.100, "BPCER": 0.250, "ACER": 0.175, "AUC": 0.925,
}

MODELS = {
    "v1": ("fas_spatial_freq.pth", 0.5),
    "v2": ("models/fas_v2_lcc_only.pth", 0.5),
    "v3": ("models/fas_v3.pth", json.load(open("models/fas_v3_calibration.json"))["threshold"]),
    "v4": ("models/fas_v4.pth", json.load(open("models/fas_v4_calibration.json"))["threshold"]),
    "v5": ("models/fas_v5.pth", json.load(open("models/fas_v5_calibration.json"))["threshold"]),
}
SEEN = {  # clips each model trained or calibrated on
    "v3": {"rwitankar_real_1", "rwitankar_real_2", "rwitankar_real_3", "rwitankar_phone_1", "rwitankar_phone_2"},
    "v4": {"rwitankar_real_1", "rwitankar_real_2", "rwitankar_real_3", "rwitankar_phone_1", "rwitankar_phone_2",
           "nilay_phone_20261008-163700", "nilay_real_20261008-161718", "nilay_real_20261008-200636",
           "nilay_real_20261008-200707", "nilay_real_20261008-200829"},
    "v5": "all labelled",
}


def load(p):
    m = SpatialFrequencyFAS(pretrained=False)
    m.load_state_dict(torch.load(p, map_location="cpu"))
    return m.eval()


nets = {k: (load(p), t) for k, (p, t) in MODELS.items()}
clips = {}
for man in ("data/webcam/manifest.csv", "data/webcam_captures/manifest.csv"):
    for r in csv.DictReader(open(man)):
        clips.setdefault(r["clip"], {"paths": [], "label": r["label"]})["paths"].append(r["path"])
for extra, label in (("20261008-210638", "real"),):   # later attempt, not in any training set
    p = sorted(glob.glob(f"data/captures/{extra}/crop_*.jpg"))
    if p:
        clips[f"nilay_real_{extra} (new)"] = {"paths": p, "label": label}

rows = []
for clip, c in sorted(clips.items()):
    b = [fas_engine.preprocess(cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)) for p in c["paths"]]
    xs, xf = torch.cat([x[0] for x in b]), torch.cat([x[1] for x in b])
    row = {"clip": clip, "label": c["label"]}
    for k, (m, t) in nets.items():
        with torch.no_grad():
            med = float(np.median(torch.softmax(m(xs, xf), 1)[:, 1].numpy()))
        row[k] = {"score": med, "pass": med >= t}
    seen = [k for k in ("v3", "v4", "v5") if SEEN[k] == "all labelled" and "(new)" not in clip
            or SEEN[k] != "all labelled" and clip in SEEN[k]]
    row["trained_on_by"] = seen
    rows.append(row)
    print(clip, {k: round(row[k]["score"], 2) for k in MODELS})

json.dump({"lcc_ablation": LCC_ABLATION, "held_out_person": HELD_OUT,
           "thresholds": {k: t for k, (_, t) in MODELS.items()}, "webcam_clips": rows},
          open("reports/summary.json", "w"), indent=1)
print("wrote reports/summary.json")
