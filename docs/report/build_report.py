"""
Build the final report (.docx) from the evaluation results.

    python evaluation/run_all.py        # (or the individual eval_*.py scripts)
    python docs/report/diagrams.py
    python docs/report/figures_extra.py
    python docs/report/screenshots.py   # needs the (gitignored) screen recording
    python docs/report/build_report.py  -> docs/report/VaultTrust_Final_Report.docx

Then open it in Word (or run docx2pdf with field update) so the contents and lists are filled in.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import ch_front  # noqa: E402
from docx_engine import Report  # noqa: E402

EVAL = os.path.join(ROOT, "reports", "eval")
OUT = os.path.join(HERE, "VaultTrust_Final_Report.docx")
LOGO = os.path.join(HERE, "figures", "vit_logo.png")


def load(name):
    p = os.path.join(EVAL, name)
    return json.load(open(p)) if os.path.exists(p) else None


def pct(x, nd=1):
    return "n/a" if x is None else f"{100 * x:.{nd}f} %"


def metrics():
    M = {"face": load("face_metrics.json"), "live": load("liveness_metrics.json"), "fas": load("fas_metrics.json"),
         "sys": load("system_metrics.json"), "otp": load("otp_metrics.json"), "lat": load("latency_metrics.json"),
         "xai": load("xai_examples.json")}
    face, sysm, lat, otp, live = M["face"], M["sys"], M["lat"], M["otp"], M["live"]
    T = sysm["combinations"]["deployed"] if sysm else None
    total = lat["verify_presence_stages"]["total"] if lat else None
    M["summary_numbers"] = {
        "face_eer": pct(face["protected"]["EER"], 2) if face else "n/a",
        "impostor_pairs": f"{face['pairs_impostor']:,}" if face else "n/a",
        "face_attack_accept": pct(face["attacks_vs_own_template"]["rate"]) if face else "n/a",
        "alf_acc": pct(T["A+L+F"]["accuracy"]) if T else "n/a",
        "alf_f1": f"{T['A+L+F']['f1']:.3f}" if T else "n/a",
        "alf_attack": pct(T["A+L+F"]["APCER_max"], 2) if T else "n/a",
        "a_acc": pct(T["A"]["accuracy"]) if T else "n/a",
        "latency": f"{total['mean'] / 1000:.1f} s" if total else "about 4–5 s",
    }
    M["goals"] = {
        "face": (f"FAR {pct(face['protected']['FAR'], 2)}, FRR {pct(face['protected']['FRR'])} per frame; "
                 f"FRR {pct(face['attempt_level_protected']['FRR'])} per attempt") if face else "n/a",
        "attacks": f"worst type {pct(T['A+L+F']['APCER_max'], 2)}" if T else "n/a",
        "genuine": pct(T["A+L+F"]["recall"]) if T else "n/a",
        "swap": ("recorded attack blocked; " + pct(live["swap"]["continuity"]["rate"], 0) + " of spliced swaps pass L")
        if live else "recorded attack blocked",
        "otp": (f"{otp['distinct']['walk_v2']:,} / 20,000 (ideal {otp['distinct']['ideal_expected']:,.0f}); "
                f"p = {otp['uniformity']['buckets_100']['p_value']:.2f}") if otp else "n/a",
        "revoke": (f"{face['template']['revoked_template_scores']['accepted']} of "
                   f"{face['template']['revoked_template_scores']['n']} accepted") if face else "n/a",
        "latency": f"{total['mean'] / 1000:.2f} s mean" if total else "4.2–4.8 s (13 Oct)",
    }
    return M


def main():
    M = metrics()
    ch_front.LOGO = LOGO
    R = Report()
    R.front_matter_numbering()
    ch_front.build(R, M)
    R.new_section("main")
    import ch1_2
    import ch3
    ch1_2.chapter1(R, M)
    ch1_2.chapter2(R, M)
    ch3.chapter3(R, M)
    for mod, fns in (("ch4", ["chapter4"]), ("ch5_6", ["chapter5", "chapter6"]), ("ch7", ["chapter7"]),
                     ("ch8_9", ["chapter8", "chapter9"])):
        if os.path.exists(os.path.join(HERE, mod + ".py")):
            m = __import__(mod)
            for fn in fns:
                if fn == "chapter7" and not all(M[k] for k in ("fas", "sys", "lat", "otp", "live", "face")):
                    R.chapter("Results and Discussion")
                    R.p("(Results pending: run the evaluation scripts.)")
                    continue
                if fn == "chapter8" and not M["sys"]:
                    R.chapter("Summary")
                    R.p("(Pending.)")
                    continue
                getattr(m, fn)(R, M)
    if os.path.exists(os.path.join(HERE, "ch8_9.py")):
        import ch8_9
        R.new_section("appendix")
        ch8_9.appendices(R, M)
    R.save(OUT)
    print("saved", OUT, f"({len(R.figures)} figures, {len(R.tables)} tables)")


if __name__ == "__main__":
    main()
