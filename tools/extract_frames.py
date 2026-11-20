"""
Turn the team's webcam recordings into a face-crop dataset.

    python tools/extract_frames.py                 # data/raw_videos -> data/webcam
    python tools/extract_frames.py --fps 4 --max-per-clip 120

Expected file names:  <person>_<type>_<n>.mp4
    type: real | phone | screen | print     (also: replay -> phone, photo -> print)

Crops are made with the same MediaPipe crop the app uses at login
(mediapipe_face.detect_and_crop_face), so training and inference see
identically framed faces.
"""

import argparse
import csv
import os
import re
import sys

import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from mediapipe_face import detect_and_crop_face  # noqa: E402

ALIASES = {"real": "real", "live": "real", "phone": "phone", "replay": "phone", "video": "phone",
           "screen": "screen", "laptop": "screen", "monitor": "screen", "tablet": "screen",
           "print": "print", "photo": "print", "paper": "print"}
VIDEO_EXT = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv")


def parse_name(fname):
    stem = os.path.splitext(os.path.basename(fname))[0].lower()
    parts = re.split(r"[_\-\s]+", stem)
    for i, p in enumerate(parts):
        if p in ALIASES:
            person = "_".join(parts[:i]) or "unknown"
            clip = "_".join(parts[i + 1:]) or "1"
            return person, ALIASES[p], clip
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/raw_videos")
    ap.add_argument("--dst", default="data/webcam")
    ap.add_argument("--fps", type=float, default=4.0)
    ap.add_argument("--max-per-clip", type=int, default=120)
    ap.add_argument("--min-face", type=int, default=90, help="skip crops smaller than this (px)")
    args = ap.parse_args()

    rows = []
    files = sorted(f for f in os.listdir(args.src) if f.lower().endswith(VIDEO_EXT))
    if not files:
        sys.exit(f"No videos found in {args.src}")
    for label in ("real", "spoof"):
        os.makedirs(os.path.join(args.dst, label), exist_ok=True)

    for fname in files:
        meta = parse_name(fname)
        if meta is None:
            print(f"  ! skipping {fname}: name must look like <person>_<real|phone|screen|print>_<n>.mp4")
            continue
        person, attack, clip = meta
        label = "real" if attack == "real" else "spoof"
        cap = cv2.VideoCapture(os.path.join(args.src, fname))
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        step = max(1, int(round(src_fps / args.fps)))
        skip = int(src_fps * 0.5)  # drop the first/last half second (hands on the keyboard)
        saved = idx = 0
        while saved < args.max_per_clip:
            ok, frame = cap.read()
            if not ok:
                break
            idx += 1
            if idx < skip or (total and idx > total - skip) or idx % step:
                continue
            face, box = detect_and_crop_face(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if face is None or min(box[2], box[3]) < args.min_face:
                continue
            out = os.path.join(args.dst, label, f"{person}_{attack}_{clip}_{idx:05d}.jpg")
            cv2.imwrite(out, cv2.cvtColor(face, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95])
            rows.append({"path": out.replace("\\", "/"), "label": label, "person": person,
                         "attack": attack, "clip": f"{person}_{attack}_{clip}"})
            saved += 1
        cap.release()
        print(f"  {fname:40s} -> {saved:4d} {label} crops ({attack})")

    with open(os.path.join(args.dst, "manifest.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "label", "person", "attack", "clip"])
        w.writeheader()
        w.writerows(rows)
    people = sorted({r["person"] for r in rows})
    n_real = sum(r["label"] == "real" for r in rows)
    print(f"\n{len(rows)} crops ({n_real} real / {len(rows) - n_real} spoof) from {len(people)} people: {', '.join(people)}")


if __name__ == "__main__":
    main()
