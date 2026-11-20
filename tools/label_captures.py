"""
Turn app captures (data/captures/<attempt>/crop_*.jpg) into labelled training data.
Duplicate attempts (identical frames saved twice) are skipped.

    python tools/label_captures.py --person nilay real=20261008-161718,20261008-200636 phone=20261008-163700

Writes data/webcam_captures/{real,spoof}/... and data/webcam_captures/manifest.csv, which
training/train_fas_v2.py loads alongside data/webcam/manifest.csv.
"""

import argparse
import csv
import glob
import hashlib
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
DST = os.path.join("data", "webcam_captures")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--person", required=True)
    ap.add_argument("groups", nargs="+", help="<attack>=<attempt>[,<attempt>...]  attack: real|phone|screen|print")
    args = ap.parse_args()

    manifest = os.path.join(DST, "manifest.csv")
    rows = []
    if os.path.exists(manifest):
        with open(manifest) as f:
            rows = [r for r in csv.DictReader(f) if r["person"] != args.person]
    seen = set()
    for group in args.groups:
        attack, attempts = group.split("=", 1)
        label = "real" if attack == "real" else "spoof"
        os.makedirs(os.path.join(DST, label), exist_ok=True)
        for attempt in attempts.split(","):
            crops = sorted(glob.glob(os.path.join("data", "captures", attempt, "crop_*.jpg")))
            if not crops:
                sys.exit(f"no crops in data/captures/{attempt}")
            digest = hashlib.md5(open(crops[0], "rb").read()).hexdigest()
            if digest in seen:
                print(f"  {attempt}: duplicate of an earlier attempt, skipped")
                continue
            seen.add(digest)
            for c in crops:
                out = os.path.join(DST, label, f"{args.person}_{attack}_{attempt}_{os.path.basename(c)}")
                shutil.copy(c, out)
                rows.append({"path": out.replace("\\", "/"), "label": label, "person": args.person,
                             "attack": attack, "clip": f"{args.person}_{attack}_{attempt}"})
            print(f"  {attempt}: {len(crops)} {label} crops ({attack})")
    with open(manifest, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "label", "person", "attack", "clip"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows in {manifest}")


if __name__ == "__main__":
    main()
