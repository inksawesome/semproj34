"""
Recompute the decision threshold of models/fas_v2.pth on the validation split (EER)
and report test-set error rates at that threshold.

    python tools/recalibrate.py
"""
import json
import os
import sys

import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "training"))
os.chdir(ROOT)

import train_fas_v2 as T  # noqa: E402

splits = T.split_groups(T.load_samples())
model = T.Ablated("fused").to(T.DEVICE)
model.net.load_state_dict(torch.load("models/fas_v2.pth", map_location=T.DEVICE))
val_p = T.predict(model, splits["val"])
thr = T.best_threshold(val_p, [s["label"] for s in splits["val"]])
test_p = T.predict(model, splits["test"])
r = T.report("v2 spatial + frequency", test_p, splits["test"], thr)
print(f"EER threshold {thr:.3f}: test APCER {r['APCER']:.3f} BPCER {r['BPCER']:.3f} ACER {r['ACER']:.3f} AUC {r['AUC']:.3f}")

with open("models/fas_calibration.json") as f:
    calib = json.load(f)
calib["threshold"] = thr
calib["threshold_method"] = "EER on validation split"
with open("models/fas_calibration.json", "w") as f:
    json.dump(calib, f, indent=1)
np.save("reports/test_scores_fused.npy", np.array([test_p, [s["label"] for s in splits["test"]]]))
if os.path.exists("reports/metrics.json"):
    with open("reports/metrics.json") as f:
        m = json.load(f)
    m["results"] = [r if x["model"] == r["model"] else x for x in m["results"]]
    with open("reports/metrics.json", "w") as f:
        json.dump(m, f, indent=1)
