"""
UI screenshots for the report, cut from the 10 Oct 2026 screen recording (gitignored).
Faces are pixelated and e-mail addresses blurred before anything is written.

    python docs/report/screenshots.py
"""

import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import face_engine  # noqa: E402

REC = "recordings/2026-10-10 22-08-25.mp4"
OUT = os.path.join(ROOT, "docs", "report", "figures")

# name: (time s, crop x0, y0, x1, y1, [rectangles to blur, full-frame coordinates])
SHOTS = {
    "ui_signin_liveness": (16, 380, 100, 1900, 1080, [(560, 285, 760, 315)]),
    "ui_signin_result": (23.5, 380, 100, 1900, 900, [(560, 285, 760, 315)]),
    "ui_accounts": (30, 380, 100, 1900, 1080, [(530, 585, 1010, 625), (1180, 500, 1560, 1075), (1540, 230, 1830, 270)]),
    "ui_verify_challenge": (68, 380, 100, 1900, 1080, [(960, 340, 1335, 400)]),
    "ui_verify_qr": (88, 380, 192, 1900, 1060, [(1225, 560, 1545, 595)]),
    "ui_phone_page": (116, 640, 100, 1300, 820, [(895, 190, 1145, 226), (720, 508, 920, 542), (720, 640, 960, 680)]),
    "ui_transfer_done": (124, 380, 100, 1900, 800, [(960, 340, 1335, 400), (710, 478, 1032, 504)]),
}


def pixelate(img, x0, y0, x1, y1, block=14):
    x0, y0 = max(0, x0), max(0, y0)
    roi = img[y0:y1, x0:x1]
    if roi.size == 0:
        return
    h, w = roi.shape[:2]
    small = cv2.resize(roi, (max(1, w // block), max(1, h // block)), interpolation=cv2.INTER_LINEAR)
    img[y0:y1, x0:x1] = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def main():
    if not os.path.exists(REC):
        print("recording not present - screenshots skipped")
        return
    cap = cv2.VideoCapture(REC)
    app = face_engine._face_app()
    for name, (t, x0, y0, x1, y1, rects) in SHOTS.items():
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            continue
        top = 507 if name == "ui_verify_challenge" else 0      # keep the pixelation inside the video
        for face in app.get(f):
            bx0, by0, bx1, by1 = face.bbox.astype(int)
            m = int(0.35 * (bx1 - bx0))
            pixelate(f, bx0 - m, max(top, by0 - m), bx1 + m, by1 + m, block=max(10, (bx1 - bx0) // 6))
        for (a, b, c, d) in rects:
            f[b:d, a:c] = cv2.GaussianBlur(f[b:d, a:c], (31, 31), 12)
        cv2.imwrite(os.path.join(OUT, name + ".png"), f[y0:y1, x0:x1])
        print("  ", name)


if __name__ == "__main__":
    main()
