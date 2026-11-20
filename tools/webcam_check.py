"""
Score the saved webcam captures (data/captures/<attempt>/crop_*.jpg) with the original v1 model
and the retrained v2 model -> reports/webcam_check.json (shown in the Model Lab).

    python tools/webcam_check.py real=20261008-161718 phone_photo=20261008-163700
"""
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


def load(path):
    m = SpatialFrequencyFAS(pretrained=False)
    m.load_state_dict(torch.load(path, map_location="cpu"))
    return m.eval()


models = {"v1 original": load("fas_spatial_freq.pth"), "v2 retrained": load("models/fas_v2.pth")}
rows = []
for arg in sys.argv[1:]:
    label, folder = arg.split("=", 1)
    crops = [cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
             for p in sorted(glob.glob(os.path.join("data", "captures", folder, "crop_*.jpg")))]
    batch = [fas_engine.preprocess(c) for c in crops]
    xs, xf = torch.cat([b[0] for b in batch]), torch.cat([b[1] for b in batch])
    row = {"attempt": label, "frames": len(crops)}
    for name, m in models.items():
        with torch.no_grad():
            p = torch.softmax(m(xs, xf), 1)[:, 1].numpy()
        row[name] = {"median": float(np.median(p)), "min": float(p.min()), "max": float(p.max())}
    rows.append(row)
    print(label, {k: round(v["median"], 3) for k, v in row.items() if isinstance(v, dict)})
os.makedirs("reports", exist_ok=True)
with open("reports/webcam_check.json", "w") as f:
    json.dump(rows, f, indent=1)
