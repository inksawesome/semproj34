"""
Copy the figures used by the IEEE Access draft into ./figures, trimming the white margins.

    python docs/paper/ieee_access/make_figures.py

Sources are the report diagrams (docs/report/figures, from diagrams.py) and the evaluation charts
(reports/eval/figures, from evaluation/eval_*.py). Regenerate those first if the numbers change.
No figure contains a face.
"""

import os

from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "figures")

FIGURES = {
    "fig_sequence.png": "docs/report/figures/sequence_stepup.png",
    "fig_fusion.png": "docs/report/figures/decision_fusion.png",
    "fig_fas_network.png": "docs/report/figures/fas_network.png",
    "fig_template.png": "docs/report/figures/template_pipeline.png",
    "fig_otp_pipeline.png": "docs/report/figures/otp_pipeline.png",
    "fig_combo_heatmap.png": "reports/eval/figures/combo_acceptance_heatmap.png",
    "fig_fas_roc.png": "reports/eval/figures/fas_roc_ablation.png",
    "fig_swap.png": "reports/eval/figures/swap_fix_effect.png",
    "fig_otp_uniformity.png": "reports/eval/figures/otp_uniformity.png",
    # added to the Word paper on 23 Oct 2026 (report Figs. 7.16, 7.1, 7.3, 7.6, 7.13)
    "fig_otp_graph_walk.png": "reports/eval/figures/otp_graph_walk.png",
    "fig_face_scores.png": "reports/eval/figures/face_score_distributions.png",
    "fig_template_scatter.png": "reports/eval/figures/template_raw_vs_protected.png",
    "fig_fas_scores.png": "reports/eval/figures/fas_score_distributions.png",
    "fig_combo_confusion.png": "reports/eval/figures/combo_confusion.png",
}


def trim(im, pad=12):
    """Crop uniform white margins, keeping a small border."""
    rgb = im.convert("RGB")
    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    box = ImageChops.difference(rgb, bg).getbbox()
    if not box:
        return im
    l, t, r, b = box
    return im.crop((max(0, l - pad), max(0, t - pad), min(im.width, r + pad), min(im.height, b + pad)))


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, src in FIGURES.items():
        im = Image.open(os.path.join(ROOT, src))
        dpi = im.info.get("dpi", (300, 300))
        out = trim(im)
        out.save(os.path.join(OUT, name), dpi=dpi)
        print(f"{name:24s} {out.size[0]}x{out.size[1]}  <- {src}")


if __name__ == "__main__":
    main()
