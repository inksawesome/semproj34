"""
Render PDF pages to PNG and tile them into contact sheets for a quick visual check.

    pip install --target <scratchpad>/pylib pymupdf      (kept out of the project environment)
    PYTHONPATH=<scratchpad>/pylib python docs/tools/render_pdf.py report.pdf out_dir [first-last] [cols]

Example: render pages 60-75 of the report, 8 per row:
    python docs/tools/render_pdf.py docs/report/VaultTrust_Final_Report.pdf <scratchpad>/pages 60-75 8
"""

import os
import sys

import pymupdf
from PIL import Image


def main():
    pdf, out = sys.argv[1], sys.argv[2]
    rng = sys.argv[3] if len(sys.argv) > 3 else None
    cols = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    doc = pymupdf.open(pdf)
    first, last = (1, len(doc)) if not rng else map(int, rng.split("-"))
    os.makedirs(out, exist_ok=True)
    files = []
    for i in range(first - 1, min(last, len(doc))):
        p = os.path.join(out, f"p{i + 1:03d}.png")
        doc[i].get_pixmap(dpi=60).save(p)
        files.append(p)
    ims = [Image.open(f) for f in files]
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, h * rows), "white")
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * w, (k // cols) * h))
    sheet_path = os.path.join(out, f"sheet_{first}-{last}.png")
    sheet.save(sheet_path)
    print(f"{len(doc)} pages; sheet: {sheet_path}")


if __name__ == "__main__":
    main()
