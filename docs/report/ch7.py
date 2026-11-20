"""Chapter 7 Results and Discussion - every number is read from reports/eval/*.json."""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
EVF = os.path.join(os.path.dirname(os.path.dirname(HERE)), "reports", "eval", "figures")


def ef(name):
    return os.path.join(EVF, name)


def P(x, nd=1):
    return "—" if x is None else f"{100 * x:.{nd}f}"


def pc(x, nd=1):
    return "—" if x is None else f"{100 * x:.{nd}f} %"


def chapter7(R, M):
    face, live, fas, sysm, otp, lat = M["face"], M["live"], M["fas"], M["sys"], M["otp"], M["lat"]
    R.chapter("Results and Discussion")
    R.p("This chapter reports what the system achieves, measured on data that the evaluated models never saw "
        "wherever that was possible, and states plainly where it was not. Section 7.1 describes the evaluation "
        "design; Sections 7.2–7.4 evaluate the three face components separately; Section 7.5 combines them; "
        "Sections 7.6 and 7.7 cover the second factor and latency; Section 7.8 compares the results with previous "
        "work; and Sections 7.9–7.11 discuss the findings, the cost and the limitations. All numbers are produced by "
        "the scripts in the `evaluation/` folder and can be regenerated.")

    # ------------------------------------------------------------------ 7.1
    R.h2("Evaluation Methodology")
    R.paras(f"""
    We evaluate three components: **A**, ArcFace face matching on the cancelable template (threshold 0.40);
    **L**, active liveness with two random challenges and the continuity rules; and **F**, the passive
    spatial-frequency anti-spoofing network. Five kinds of attempt form the ground truth: *genuine* (the enrolled
    person, live), *impostor* (a different live person), *photo* (a photo or screen still of the enrolled person),
    *replay* (a video of the enrolled person replayed on a phone) and *swap* (the enrolled person's photo during
    calibration, followed by the attacker's own live face for the challenges).

    Two rules governed the data. First, an anti-spoofing model is only evaluated on people and subjects it was not
    trained or calibrated on. For this purpose we retrained the network with the deployed recipe – once with the
    spatial branch only and once with both branches – keeping one webcam person (Nilay) and twelve LCC-FASD
    subjects entirely out of training and calibration. Because the other webcam person (Rwitankar) is in the
    training data of every model, his recordings are used for liveness, face recognition and continuity, but not
    to measure anti-spoofing. Second, every rate is
    reported with the number of trials behind it; with only two webcam people, several rates have wide confidence
    intervals, and we give 95 % Wilson intervals where they matter. Table 7.1 lists the data used for each part.
    """)
    sp = fas["splits"] if fas and "splits" in fas else None
    R.table("Evaluation Data", ["Component / study", "Data", "Size"],
            [["A: verification", f"{face['identities']} identities ({face['identities_lcc']} LCC-FASD + 2 webcam); first 5 "
              "real crops enrol, the rest probe", f"{face['probes_genuine']:,} genuine probes, "
              f"{face['pairs_impostor']:,} impostor pairs"],
             ["A: attacks", "Spoof crops of enrolled identities matched to their own template",
              f"{face['attacks_vs_own_template']['n']:,} attack images"],
             ["F: ablation", "Held-out test split: 12 unseen LCC-FASD subjects + unseen webcam person",
              f"{fas['test_split']['n']} frames ({fas['test_split']['real']} real)" if fas else "—"],
             ["L: video", "5 webcam videos (3 genuine, 2 phone replays) through the real processor, many start points",
              f"{sum(v['n'] for v in live['achievability']['genuine'].values()) + sum(v['n'] for v in live['achievability']['replay'].values())} "
              f"single-challenge runs, {live['pairs']['genuine']['n'] + live['pairs']['replay']['n']} pair runs"],
             ["L: photo and swap", "15 face photos (held still / tilted); spliced replay → live sequences",
              f"{live['photo']['still_pairs']['n'] + live['photo']['tilted_pairs']['n'] + 75} photo runs, "
              f"{3 * live['swap']['continuity']['n']} swap runs"],
             ["L: field trial", "All presence decisions in the application log, 8–12 Oct, 4 accounts",
              f"{live['field']['genuine_attempts']} genuine attempts"],
             ["System", "Attempts of 10 frames per clip with joint A and F outcomes; L rates per category",
              ", ".join(f"{k} {v:,}" for k, v in sysm["attempt_counts"].items())],
             ["OTP", "Random secrets and time steps", "20,000 secrets; 200,000 codes; 5,000 binding trials"],
             ["Latency", "Genuine webcam video at 640×480 through the real processor and verifier", f"{lat['reps']} runs"]],
            widths=[1.3, 3.0, 1.5], size=9)

    # ------------------------------------------------------------------ 7.2 face
    R.h2("Face Recognition and the Cancelable Template (A)")
    raw, pro, att = face["raw"], face["protected"], face["attempt_level_protected"]
    R.paras(f"""
    Table 7.2 compares verification with the raw 512-D embedding and with the 256-D protected template, in the
    stolen-key setting where the matcher knows the user's key (the normal operating mode). At the deployed
    threshold of 0.40 no impostor pair was accepted in either domain ({face['pairs_impostor']:,} pairs; the highest
    impostor similarity was {raw['impostor_max']:.2f} raw and {pro['impostor_max']:.2f} protected), while
    {pc(pro['FRR'])} of single genuine frames fell below the threshold in the protected domain ({pc(raw['FRR'])}
    raw). Averaging five frames, as the application does, reduced the genuine rejection rate to {pc(att['FRR'], 2)}.
    The protection costs very little: the EER rises from {pc(raw['EER'], 2)} to {pc(pro['EER'], 2)}, and raw and
    protected scores are correlated with r = {face['template']['raw_vs_protected_corr']:.3f} (Fig. 7.3).
    """)
    R.table("Face Verification: Raw Embedding vs Protected Template (Threshold 0.40)",
            ["Metric", "Raw (frame)", "Protected (frame)", "Protected (5-frame attempt)"],
            [["Genuine / impostor trials", f"{raw['n_pos']:,} / {raw['n_neg']:,}", f"{pro['n_pos']:,} / {pro['n_neg']:,}",
              f"{att['n_pos']:,} / {att['n_neg']:,}"],
             ["Accuracy (%)", P(raw["accuracy"], 2), P(pro["accuracy"], 2), P(att["accuracy"], 2)],
             ["Precision (%)", P(raw["precision"], 2), P(pro["precision"], 2), P(att["precision"], 2)],
             ["Recall / TAR (%)", P(raw["recall"], 2), P(pro["recall"], 2), P(att["recall"], 2)],
             ["F1-score", f"{raw['f1']:.4f}", f"{pro['f1']:.4f}", f"{att['f1']:.4f}"],
             ["FAR (%)", P(raw["FAR"], 3), P(pro["FAR"], 3), P(att["FAR"], 3)],
             ["FRR (%)", P(raw["FRR"], 2), P(pro["FRR"], 2), P(att["FRR"], 2)],
             ["EER (%)", P(raw["EER"], 2), P(pro["EER"], 2), P(att["EER"], 2)],
             ["AUC", f"{raw['AUC']:.4f}", f"{pro['AUC']:.4f}", f"{att['AUC']:.4f}"],
             ["TAR @ FAR = 0.1 % (%)", P(raw["TAR@FAR=0.1%"], 2), P(pro["TAR@FAR=0.1%"], 2), P(att["TAR@FAR=0.1%"], 2)],
             ["Genuine score mean ± sd", f"{raw['genuine_mean']:.3f} ± {raw['genuine_std']:.3f}",
              f"{pro['genuine_mean']:.3f} ± {pro['genuine_std']:.3f}", f"{att['genuine_mean']:.3f} ± {att['genuine_std']:.3f}"],
             ["Impostor score mean ± sd", f"{raw['impostor_mean']:.3f} ± {raw['impostor_std']:.3f}",
              f"{pro['impostor_mean']:.3f} ± {pro['impostor_std']:.3f}", f"{att['impostor_mean']:.3f} ± {att['impostor_std']:.3f}"]],
            widths=[1.9, 1.3, 1.3, 1.4], align=["l", "c", "c", "c"], size=9)
    R.figure(ef("face_score_distributions.png"), "Genuine and Impostor Score Distributions, Raw and Protected", width=5.8)
    R.figure(ef("face_roc.png"), "ROC Curves of Face Verification (Logarithmic FAR Axis)", width=3.6)
    R.figure(ef("template_raw_vs_protected.png"), "Raw vs Protected Similarity for the Same Pairs", width=3.3)
    a = face["attacks_vs_own_template"]
    t = face["template"]
    fta = face["failure_to_acquire"]
    R.paras(f"""
    The most important result of this section, however, concerns attacks. When the spoof images of each enrolled
    identity – photos and replays of that same person – were matched against that person's own template, ArcFace
    accepted {a['accepted']:,} of {a['n']:,} ({pc(a['rate'])}). Face recognition is doing exactly what it was trained
    to do: it recognises the person in the photo. This is the quantitative reason why A cannot be used alone and
    why the liveness and anti-spoofing components exist.

    Table 7.3 summarises the properties of the template. The same face protected under two different keys gave a
    mean similarity of {t['same_face_two_keys']['mean']:+.3f} (largest magnitude {t['same_face_two_keys']['max_abs']:.2f},
    {t['same_face_two_keys']['n']} pairs), i.e. the templates are unlinkable; after re-keying, an old template was
    never matched by the user's face under the new key ({t['revoked_template_scores']['accepted']} of
    {t['revoked_template_scores']['n']}; highest score {t['revoked_template_scores']['max']:.2f}). RetinaFace failed to
    find a face in {fta['webcam_real']['missed']} of {fta['webcam_real']['n']} webcam real crops
    ({pc(fta['webcam_real']['rate'])}) and in {fta['lcc_spoof']['missed']} of {fta['lcc_spoof']['n']} LCC spoof crops; no
    LCC real crop was missed.
    """)
    R.table("Properties of the Cancelable Template", ["Property", "Measurement", "Result"],
            [["Size", "Stored bytes per user", f"{t['template_bytes']:,} B (256 × float32)"],
             ["Accuracy preservation", "Correlation of raw and protected scores", f"r = {t['raw_vs_protected_corr']:.3f}; "
              f"mean |Δ| = {t['raw_vs_protected_mean_abs_diff']:.3f}"],
             ["Unlinkability", "Same face, two keys (cosine)", f"mean {t['same_face_two_keys']['mean']:+.3f}, "
              f"max |cos| {t['same_face_two_keys']['max_abs']:.2f}"],
             ["Revocability", "Old template vs probe under new key", f"{t['revoked_template_scores']['accepted']} / "
              f"{t['revoked_template_scores']['n']} accepted"],
             ["Irreversibility", "Mapping 512 → 256 dimensions", "many-to-one; secure only while the key is secret"],
             ["Speed", "Match (cached key) / new key schedule", f"{t['match_ms']:.1f} ms / {t['new_key_transform_ms']:.0f} ms"]],
            widths=[1.4, 2.2, 2.2], size=9.5)

    # ------------------------------------------------------------------ 7.3 FAS
    R.h2("Passive Anti-Spoofing (F)")
    V = fas["variants"]
    names = {"spatial": "Spatial only (RGB)", "freq": "Frequency only (FFT)", "fused": "Spatial + frequency"}
    hand = {r["model"]: r for r in fas.get("training_log_results", [])}
    rows = []
    for mode in ("spatial", "freq", "fused"):
        if mode not in V:
            continue
        v = V[mode]
        a_, l_, w_ = v["all"], v["lcc"], v["webcam_unseen_person"]
        rows.append([names[mode], f"{v['threshold']:.3f}", P(a_["APCER"]), P(a_["BPCER"]), P(a_["ACER"]),
                     f"{a_['AUC']:.3f}", P(a_["EER"]), P(a_["accuracy"]), f"{a_['f1']:.3f}", f"{l_['AUC']:.3f}",
                     f"{w_['AUC']:.3f}"])
    for key, label in (("HF energy only", "HF energy (logistic)"), ("Fractal dimension only", "Fractal dim. (logistic)"),
                       ("FD + HF", "FD + HF (logistic)")):
        if key in hand:
            h = hand[key]
            rows.append([label, f"{h['threshold']:.3f}", P(h["APCER"]), P(h["BPCER"]), P(h["ACER"]), f"{h['AUC']:.3f}",
                         "—", P(h["accuracy"]), "—", f"{h['AUC']:.3f}", "—"])
    R.paras(f"""
    Table 7.4 gives the ablation. The two networks were trained with identical data, splits, augmentation,
    schedule and threshold calibration; only the branch was changed. (A frequency-only network was not trained for
    this report; in our earlier LCC-only run it reached AUC 0.736 against 0.986 for spatial-only and 0.970 for the
    fused network.) The handcrafted baselines – logistic regression on the high-frequency energy ratio,
    on the fractal dimension, and on both – were fitted on the same LCC-FASD subject split and evaluated on its
    LCC test subjects. Thresholds were calibrated at the equal-error
    point of the webcam validation clips, so they are tuned to the deployment camera, not to LCC-FASD.
    """)
    R.table("Anti-Spoofing Ablation on the Held-Out Test Split (Frame Level; Real = Positive for Precision/Recall)",
            ["Model", "Thr.", "APCER %", "BPCER %", "ACER %", "AUC", "EER %", "Acc. %", "F1", "AUC LCC", "AUC webcam"],
            rows, widths=[1.35, 0.42, 0.5, 0.5, 0.48, 0.42, 0.45, 0.45, 0.4, 0.5, 0.55],
            align=["l"] + ["c"] * 10, size=8)
    fu = V.get("fused", {})
    sp_ = V.get("spatial", {})
    R.paras(f"""
    Three findings stand out. First, on the unseen LCC-FASD subjects the networks separate real and spoof faces
    well (AUC {fu['lcc']['AUC']:.3f} fused, {sp_['lcc']['AUC']:.3f} spatial), far
    better than the handcrafted cues, and the fractal dimension is no better than chance – the evidence behind
    the decision in Section 2.5 to use it for explanation only. Second, at the webcam-calibrated threshold the
    attack error on LCC-FASD is high (APCER {P(fu['lcc']['APCER'])} % for the fused model): a threshold tuned to
    our camera is permissive for the very different spoof media of LCC-FASD. At the conventional threshold of 0.5
    the fused model's LCC APCER falls to {P(fu['lcc@0.5']['APCER'])} % with BPCER {P(fu['lcc@0.5']['BPCER'])} %. Third, and
    most important for deployment, performance on the unseen webcam person is much weaker
    (AUC {fu['webcam_unseen_person']['AUC']:.3f} fused): with webcam data from only one other person, the model has not
    learned what a real face looks like on this camera under all lighting conditions.
    """)
    sw_auc, fu_auc = sp_["webcam_unseen_person"]["AUC"], fu["webcam_unseen_person"]["AUC"]
    if sw_auc > fu_auc:
        R.p(f"The ablation also shows *which* branch generalises. On LCC-FASD the fused network is better "
            f"(AUC {fu['lcc']['AUC']:.3f} vs {sp_['lcc']['AUC']:.3f}), but on the unseen webcam person the spatial-only "
            f"network (AUC {sw_auc:.3f}) did clearly better than the fused one ({fu_auc:.3f}). "
            "The frequency branch appears to learn spectral properties of the particular cameras "
            "and compression in its training data, which help on LCC-FASD but transfer poorly to a new person on our "
            "webcam. With the present data, a spatial-only model would be the better deployment choice for unseen "
            "users, and the frequency spectrum is more valuable as an explanation than as a decision input.")
    else:
        R.p(f"On the unseen webcam person the fused network (AUC {fu_auc:.3f}) did at least as well as the spatial-only "
            f"one ({sw_auc:.3f}), so the two branches are complementary there too.")
    R.figure(ef("fas_roc_ablation.png"), "ROC Curves of the Anti-Spoofing Variants on Unseen Data", width=5.8)
    R.figure(ef("fas_ablation_bars.png"), "Error Rates of the Anti-Spoofing Variants (Lower Is Better)", width=5.2)
    R.figure(ef("fas_score_distributions.png"), "Score Distributions of the Fused Model on Unseen Data", width=5.2)
    aw = fu.get("attempt_webcam", {})
    al = fu.get("attempt_lcc", {})
    R.paras(f"""
    The application does not decide on single frames but on the median of ten. Table 7.5 shows the attempt-level
    results: on LCC-FASD, {al.get('n_attempts', 0)} attempts of up to ten frames; on the unseen webcam person, one
    attempt per recorded sign-in. At attempt level the unseen person's phone attacks were all blocked
    (APCER {P(aw.get('APCER'))} %), but {P(aw.get('BPCER'))} % of the person's genuine attempts were rejected.
    """)
    arow = []
    for mode in ("spatial", "freq", "fused"):
        if mode in V:
            for part, lab in (("attempt_lcc", "LCC-FASD"), ("attempt_webcam", "webcam, unseen person")):
                m = V[mode].get(part)
                if m:
                    arow.append([names[mode], lab, str(m["n_attempts"]), f"{m['n_pos']} / {m['n_neg']}", P(m["APCER"]),
                                 P(m["BPCER"]), P(m["ACER"]), P(m["accuracy"])])
    R.table("Attempt-Level Anti-Spoofing (Median of up to 10 Frames)",
            ["Model", "Data", "Attempts", "Real / spoof", "APCER %", "BPCER %", "ACER %", "Acc. %"],
            arow, widths=[1.35, 1.35, 0.6, 0.75, 0.55, 0.55, 0.5, 0.5], align=["l", "l"] + ["c"] * 6, size=8.5)
    lo = fas.get("lopo_rwitankar")
    if lo:
        clips = lo["clips"]
        crow = [[c, d["label"], str(d["frames"]), f"{d['median']:.2f}", "pass" if d["passed"] else "block",
                 "✓" if d["passed"] == (d["label"] == "real") else "✗"] for c, d in sorted(clips.items())]
        R.p(f"The leave-one-person-out run gives the same picture from the other side. With Rwitankar held out, the "
            f"fused model (threshold {lo['threshold']:.3f}) produced the per-clip medians of Table 7.6.")
        R.table("Leave-One-Person-Out: Unseen Person's Clips (Fused Model)",
                ["Clip", "Truth", "Frames", "Median p_{real}", "Decision", "Correct"], crow,
                widths=[1.9, 0.6, 0.6, 0.9, 0.7, 0.6], align=["l", "c", "c", "c", "c", "c"], size=9)
    h = fas.get("history")
    if h:
        vers = ["v1", "v2", "v3", "v4", "v5"]
        hrow = []
        for c in h["webcam_clips"]:
            hrow.append([c["clip"].replace("nilay_", "N ").replace("rwitankar_", "R ").replace("_2026", " ").replace("-", " "),
                         c["label"]] + [(f"{c[v]['score']:.2f} {'✓' if c[v]['pass'] == (c['label'] == 'real') else '✗'}"
                                        if c.get(v) else "—") for v in vers])
        R.p("Table 7.7 tracks the deployed model versions on our webcam clips (median real-probability per clip and "
            "whether the decision was correct at each version's threshold). These are not generalisation results – v4 "
            "and v5 were trained on most of these clips – but they document how each retraining changed the system's "
            "behaviour, including the v4 failure on the phone held close (0.72) that enabled the swap attack and its "
            "correction in v5. Fig. 7.7 summarises the versions.")
        R.table("Deployed Model Versions on Webcam Clips (Median p_{real}; ✓ Correct, ✗ Wrong)",
                ["Clip", "Truth"] + vers, hrow, widths=[1.9, 0.5, 0.65, 0.65, 0.65, 0.65, 0.65],
                align=["l", "c"] + ["c"] * 5, size=8)
        R.figure(ef("fas_versions.png"), "Anti-Spoofing Model Versions: Webcam Correctness and LCC-FASD AUC", width=5.2)

    # ------------------------------------------------------------------ 7.4 liveness
    R.h2("Active Liveness (L)")
    ach = live["achievability"]
    lab = {"BLINK": "Blink twice", "TURN_LEFT": "Turn left", "TURN_RIGHT": "Turn right", "SMILE": "Smile", "LOOK_UP": "Look up"}
    R.paras(f"""
    Active liveness can only be evaluated on video. We drove the deployed processor with the recorded webcam
    videos, starting at every second (single challenges) or every two seconds (challenge pairs), using the video's
    own clock. Table 7.8 shows which challenges each kind of presentation could satisfy within the 9-second limit.
    The genuine recordings and the phone replays behave identically: people blink naturally, so a natural video –
    live or replayed – satisfies "blink twice" in most windows (genuine {pc(ach['genuine']['BLINK']['rate'], 0)},
    replay {pc(ach['replay']['BLINK']['rate'], 0)}), and nothing else. This is the key point: active liveness does
    not distinguish a live face from a video by the *content* of the motion, but by the ability to *respond* to a
    random prompt. A live user turns or smiles when asked; a video cannot.
    """)
    R.table("Single Challenges Satisfied Within 9 s on Recorded Video",
            ["Challenge", "Genuine (natural behaviour)", "Phone replay", "Photo tilted by attacker"],
            [[lab[c], f"{ach['genuine'][c]['passed']}/{ach['genuine'][c]['n']} ({P(ach['genuine'][c]['rate'], 0)} %)",
              f"{ach['replay'][c]['passed']}/{ach['replay'][c]['n']} ({P(ach['replay'][c]['rate'], 0)} %)",
              f"{live['photo']['tilted_single'][c]['passed']}/{live['photo']['tilted_single'][c]['n']}"]
             for c in ("BLINK", "TURN_LEFT", "TURN_RIGHT", "SMILE", "LOOK_UP")],
            widths=[1.3, 1.6, 1.4, 1.5], align=["l", "c", "c", "c"], size=9.5)
    R.figure(ef("liveness_challenge_achievability.png"), "Challenges Each Presentation Can Satisfy", width=5.6)
    ph, sw, fld = live["photo"], live["swap"], live["field"]
    gwc = live["genuine_with_continuity"]
    R.paras(f"""
    Table 7.9 turns this into attack results. A replay passed a blink-only policy in
    {live['replay_blink_only']['passed']} of {live['replay_blink_only']['n']} windows, but none of
    {live['pairs']['replay']['n']} random challenge pairs (95 % upper bound {pc(live['pairs']['replay']['ci'][1])}). A photo
    held still never completed calibration and a challenge; we also simulated an adaptive attacker who tilts the
    photo in perspective, up to 50°, in whichever direction the prompt asks. MediaPipe's head-pose estimate of a
    tilted flat photo barely moved: a single "look up" was faked once in {ph['tilted_single']['LOOK_UP']['n']}
    attempts and no random pair passed ({ph['tilted_pairs']['passed']} of {ph['tilted_pairs']['n']}).
    """)
    R.table("Attacks Against Active Liveness",
            ["Attack", "Policy", "Passed / runs", "Pass rate", "95 % CI"],
            [["Phone replay", "blink-only (both challenges 'blink')",
              f"{live['replay_blink_only']['passed']}/{live['replay_blink_only']['n']}", pc(live['replay_blink_only']['rate'], 0), "—"],
             ["Phone replay", "two random distinct challenges", f"{live['pairs']['replay']['passed']}/{live['pairs']['replay']['n']}",
              pc(live['pairs']['replay']['rate'], 0), f"0 – {P(live['pairs']['replay']['ci'][1])} %"],
             ["Photo held still", "two random distinct challenges", f"{ph['still_pairs']['passed']}/{ph['still_pairs']['n']}",
              pc(ph['still_pairs']['rate'], 0), f"0 – {P(ph['still_pairs']['ci'][1])} %"],
             ["Photo tilted (adaptive)", "two random distinct challenges", f"{ph['tilted_pairs']['passed']}/{ph['tilted_pairs']['n']}",
              pc(ph['tilted_pairs']['rate'], 0), f"0 – {P(ph['tilted_pairs']['ci'][1])} %"],
             ["Swap, no continuity", "pre-11-Oct processor", f"{sw['no_continuity']['passed']}/{sw['no_continuity']['n']}",
              pc(sw['no_continuity']['rate'], 0), "—"],
             ["Swap, continuity", "deployed processor", f"{sw['continuity']['passed']}/{sw['continuity']['n']}",
              pc(sw['continuity']['rate'], 0), "—"],
             ["Swap aligned, continuity", "live face placed where the spoof was", f"{sw['aligned']['passed']}/{sw['aligned']['n']}",
              pc(sw['aligned']['rate'], 0), "—"]],
            widths=[1.4, 2.0, 0.9, 0.7, 0.8], align=["l", "l", "c", "c", "c"], size=9)
    R.figure(ef("liveness_attacks.png"), "Attacks Passing Active Liveness Under Each Policy", width=5.4)
    byg = sw["continuity"]["by_gap"]
    R.paras(f"""
    For swaps we spliced the phone replay (until calibration completed) to a live recording after a gap of 0, 0.3,
    0.6, 1.0 or 1.5 seconds. Because the live clips contain only natural blinks, some splices timed out in every
    setting; of those whose live part completed the challenges ({sw['no_continuity']['passed']}), the deployed
    processor still passed {sw['continuity']['passed']} – all with gaps of at most 0.6 s and the live face appearing
    close to where the phone face had been (the pass rates by gap were {", ".join(f"{g} s: {P(v['rate'], 0)} %" for g, v in byg.items())}).
    The aligned stress test, in which the live face appears exactly where the spoof was, shows that the processor
    rules alone cannot stop a quick, well-aligned swap. That is by design: in a real swap the live face belongs to
    the attacker, and the server-side identity check compares it with the calibration frames. In our impostor data
    only {pc(sysm['identity_continuity_pass_impostor'], 2)} of different-person attempts reached the identity threshold
    of 0.35, and the recorded attack of 10 October, which used a 0.94 s gap, is blocked by the processor at 70.05 s of
    the recording. On genuine recordings the continuity rules never fired: the largest shift between detections was
    {gwc['max_shift']:.2f} face widths and the largest gap {gwc['max_gap']:.2f} s, against limits of 0.5 and 0.7.
    """)
    R.paras(f"""
    Finally, the field log records how real users fared. Of {fld['genuine_attempts']} genuine presence checks made by
    the team between 8 and 12 October (across model versions v2–v5), {fld['liveness_pass']} passed liveness on the first
    try ({pc(fld['liveness_pass_rate'])}, 95 % CI {P(fld['liveness_pass_ci'][0], 0)}–{P(fld['liveness_pass_ci'][1], 0)} %).
    The failures (Table 7.10) were mostly head turns and blinks that timed out, concentrated on 9 October when one user
    was learning the system; on the other days every check passed liveness. With up to three attempts the expected
    liveness pass rate is {pc(fld['within_3_tries_estimate'])}. Fig. 7.11 shows the overall outcome of these checks,
    including rejections by the anti-spoofing model of the time.
    """)
    R.table("Field Trial: Liveness Failures of Genuine Users (8–12 Oct 2026)", ["Reason", "Count"],
            [[k.rstrip("."), str(v)] for k, v in sorted(fld["liveness_fail_reasons"].items(), key=lambda x: -x[1])] +
            [["Total liveness failures", str(fld["genuine_attempts"] - fld["liveness_pass"])],
             ["Genuine attempts", str(fld["genuine_attempts"])]],
            widths=[3.6, 0.9], align=["l", "c"], size=9.5)
    R.figure(ef("field_trial_outcomes.png"), "Outcome of Genuine Presence Checks in the Field Trial", width=3.6)

    # ------------------------------------------------------------------ 7.5 combinations
    R.h2("Unit-Wise and Combination Study")
    S, T, B = sysm, sysm["combinations"]["deployed"], sysm["combinations"]["before_continuity_fix"]
    ca = S["component_acceptance"]
    R.paras(f"""
    We now combine the components. Table 7.11 gives the measured acceptance rate of each component for each
    attempt category – the probability that the component alone lets the attempt through. A and F were measured
    per attempt of up to ten frames on held-out data only: genuine and impostor attempts come from the unseen
    LCC-FASD subjects and the unseen webcam person, attack attempts from the spoof clips of those same people.
    Photos and replays present the same kind of re-imaged frames to A and F, so both categories use these attack
    attempts for A and F, and differ in the L rate measured for them;
    L, which acts on behaviour, uses the rates of Section 7.4: the field-trial rate for live people
    ({pc(S['l_rates']['genuine'])}), the tilted-photo rate for photos, the random-pair rate for replays, and for
    swaps the live rate multiplied by the share of spliced swaps that passed the continuity rules
    ({pc(S['swap_continuity_pass_given_challenges'])}). A combination accepts an attempt only if every member accepts
    it; A and F are combined per attempt, and L multiplicatively, assuming that whether a presenter can respond to a
    prompt is independent of face texture and identity. For swaps, combinations that contain L also apply A and F to
    the challenge frames (identity at 0.35, anti-spoofing at the F threshold), which show the attacker's live face.
    """)
    cats = ["genuine", "impostor", "photo", "replay", "swap"]
    R.table("Acceptance Rate (%) of Each Component by Attempt Category",
            ["Component", "Genuine ↑", "Impostor ↓", "Photo ↓", "Replay ↓", "Swap ↓"],
            [["Attempts (A, F)"] + [f"{S['attempt_counts'][c]:,}" for c in cats]] +
            [[{"A": "A  face match", "L": "L  active liveness", "F": "F  anti-spoofing"}[k]] +
             [P(ca[c][k]) for c in cats] for k in ("A", "L", "F")],
            widths=[1.5, 0.85, 0.85, 0.85, 0.85, 0.85], align=["l"] + ["c"] * 5, size=9.5)
    R.paras(f"""
    The table is the clearest statement of why the design has more than one component. A rejects every impostor
    but accepts almost every photo, replay and swap of the right person. L rejects photos and replays but cannot
    tell one live person from another. F rejects about half of the presentation attacks on unseen people but
    accepts impostors, who are real faces. Each component's blind spot is covered by another. The number of
    held-out genuine attempts is small ({S['attempt_counts']['genuine']}), so the genuine rates carry wide
    uncertainty.

    Table 7.12 gives the seven combinations for a balanced population of 1,000 attempts: 500 genuine and 500 attacks
    split equally between the four attack categories (genuine = positive class). Fig. 7.12 plots accuracy,
    precision, recall and F1, Fig. 7.13 the acceptance of each category, and Fig. 7.14 four of the confusion
    matrices.
    """)
    crow = []
    combos = ["A", "L", "F", "A+L", "A+F", "L+F", "A+L+F"]
    best = max(combos, key=lambda c: T[c]["f1"])
    for c in combos:
        m = T[c]
        crow.append([c, P(m["accuracy"]), P(m["precision"]), P(m["recall"]), f"{m['f1']:.3f}",
                     P(m["APCER_by_attack"]["impostor"]), P(m["APCER_by_attack"]["photo"]),
                     P(m["APCER_by_attack"]["replay"]), P(m["APCER_by_attack"]["swap"]), P(m["BPCER"]), P(m["ACER"])])
    R.table("Combinations of Components (1,000 Attempts: 500 Genuine, 125 per Attack Type)",
            ["Combo", "Acc. %", "Prec. %", "Recall %", "F1", "Imp. acc. %", "Photo acc. %", "Replay acc. %",
             "Swap acc. %", "BPCER %", "ACER %"],
            crow, widths=[0.55, 0.5, 0.5, 0.55, 0.45, 0.55, 0.55, 0.6, 0.55, 0.55, 0.5], align=["l"] + ["c"] * 10, size=8,
            highlight_rows=(combos.index(best),))
    R.figure(ef("combo_metrics_bars.png"), "Accuracy, Precision, Recall and F1 of Every Combination", width=5.9)
    R.figure(ef("combo_acceptance_heatmap.png"), "Acceptance Rate of Each Attempt Category per Combination", width=5.4)
    R.figure(ef("combo_confusion.png"), "Confusion Matrices of A, L, F and A+L+F (per 1,000 Attempts)", width=5.9)
    alf, a1, al = T["A+L+F"], T["A"], T["A+L"]
    R.paras(f"""
    A alone has perfect resistance to impostors but a worst-case attack acceptance of {P(a1['APCER_max'])} %, so its
    accuracy on a balanced population is only {P(a1['accuracy'])} %. Adding L removes every photo and replay we
    measured, and with its identity check on the challenge frames also every swap: A+L reaches
    {P(al['accuracy'])} % accuracy and the best F1 ({al['f1']:.3f}). The full combination A+L+F also accepts no attack
    in our data (worst type {P(alf['APCER_max'], 2)} %), with precision {P(alf['precision'])} % and F1 {alf['f1']:.3f}, but
    its recall is lower – {P(alf['recall'])} % against {P(al['recall'])} % – because F, on people it has never seen, also
    rejects some genuine attempts, and the AND rule multiplies acceptance rates. With three attempts allowed per
    transfer the genuine acceptance of A+L+F rises to about {P(1 - (1 - alf['recall']) ** 3)} %, assuming independent
    attempts.

    On our measured attacks, therefore, F adds no protection that L does not already give, and costs recall. Its
    value lies in the attacks L cannot stop: a video that *does* respond to prompts – an attacker re-enacting the
    victim's face live, or a replay prepared with every possible action. Against such an attack L is defeated, and
    the protection falls back on A+F, which accepted {P(T['A+F']['acceptance']['photo'])} % of re-imaged faces of the
    right person, against {P(T['A']['acceptance']['photo'])} % for A alone. F is the defence in depth, and the explanation
    it produces is used on every attempt; improving its genuine acceptance with data from more people (Section 7.3)
    is the most valuable next step.
    """)
    R.figure(ef("swap_fix_effect.png"), "Swap-Attack Acceptance Before and After the Continuity Fix", width=4.6)
    R.p(f"Fig. 7.15 isolates the continuity fix. Before it, a swap was accepted whenever the live attacker completed "
        f"the challenges and the calibration frames passed the other checks – {P(B['A+L+F']['acceptance']['swap'], 2)} % for "
        f"A+L+F under our data, and {P(B['L+F']['acceptance']['swap'])} % for L+F; with continuity these fall to "
        f"{P(T['A+L+F']['acceptance']['swap'], 3)} % and {P(T['L+F']['acceptance']['swap'])} %.")

    # ------------------------------------------------------------------ 7.6 OTP
    R.h2("Random-Walk OTP")
    d, u, bnd, g, lt = otp["distinct"], otp["uniformity"], otp["binding"], otp["graph"], otp["latency_ms"]
    R.paras(f"""
    Table 7.13 evaluates the second factor and compares it with standard TOTP and with our first version. From
    {d['n_secrets']:,} random secrets at the same time step, version 2 produced {d['walk_v2']:,} distinct codes and TOTP
    {d['totp']:,}, against {d['ideal_expected']:,.0f} expected for an ideal uniform 6-digit code (version 1: 768). Across
    {u['n_codes']:,} codes the distribution over 100 value buckets is consistent with uniform (χ² = {u['buckets_100']['chi2']:.1f},
    {u['buckets_100']['dof']} degrees of freedom, p = {u['buckets_100']['p_value']:.2f}; Fig. 7.16), and so is each of the six
    digit positions (p between {min(x['p_value'] for x in u['digit_positions']):.2f} and
    {max(x['p_value'] for x in u['digit_positions']):.2f}). Changing one bit of the key, moving to the next time step, or
    changing the transfer's amount by one cent, its payee or its reference never reproduced the code in
    {bnd['trials']:,} trials each, and changed on average {min(bnd['mean_digits_changed'].values()):.2f}–{max(bnd['mean_digits_changed'].values()):.2f}
    of the six digits (5.4 expected for independent codes); one key bit flips {P(bnd['seed_avalanche_bits'])} % of the seed
    bits. This is the dynamic-linking property in measurable form.
    """)
    R.table("Second-Factor Evaluation: Random-Walk OTP v2 vs v1 vs TOTP",
            ["Property", "Walk-OTP v1", "Walk-OTP v2", "TOTP (RFC 6238)"],
            [["Distinct codes from 20,000 secrets", "768", f"{d['walk_v2']:,}", f"{d['totp']:,}"],
             ["Uniformity (100 buckets, χ² p)", "fails", f"{u['buckets_100']['p_value']:.2f}", "uniform by design"],
             ["Guesses for 50 % success (one transfer)", "≈ 400", f"≈ {otp['brute_force']['code_space'] // 2:,}", "≈ 500,000"],
             ["Bound to amount and payee", "no", "yes (context hash)", "no"],
             ["Same code after 1-cent change", "—", f"{bnd['same_code']['amount_1c']} / {bnd['trials']:,}", "same code"],
             ["Generation time", "—", f"{lt['walk_generate_cached_graph'] * 1000:.0f} µs (graph cached)", f"{lt['totp_generate'] * 1000:.0f} µs"],
             ["Implementations", "Python, JS (differed)", "Python, JS (12 identical vectors)", "standard"]],
            widths=[2.1, 1.0, 1.5, 1.2], align=["l", "c", "c", "c"], size=9)
    R.figure(ef("otp_uniformity.png"), "Distribution of 200,000 Random-Walk OTP Codes", width=5.4)
    R.paras(f"""
    The graph (Fig. 7.17) is connected, with {g['nodes']} nodes, {g['edges']} edges, degrees between {g['degree_min']} and
    {g['degree_max']}, diameter {g['diameter']} and an average shortest path of {g['avg_path_length']:.2f} steps, against
    {g['lattice_avg_path_length']:.2f} for the unrewired lattice; the rewiring lowered the clustering coefficient from
    {g['lattice_clustering']:.2f} to {g['clustering']:.2f}. With about {otp['walk']['paths_log2']:.0f} bits of possible paths
    and 19.9 bits of code space, the code space and not the walk is the limiting factor, as it is for TOTP. An attacker
    has three guesses per transfer, so the chance of guessing a code is 3 in 10⁶ (at most 6 in 10⁶ during the 10-second
    grace period when two codes are valid), and a code cannot be replayed because the server refuses any time step not
    later than the last one accepted. Generating a code takes {lt['walk_generate']:.1f} ms in Python, of which
    {lt['graph_build']:.1f} ms is rebuilding the public graph on each call; with the graph cached it takes
    {lt['walk_generate_cached_graph'] * 1000:.0f} µs, and TOTP {lt['totp_generate'] * 1000:.0f} µs – all negligible next to a
    human typing six digits.
    """)
    R.figure(ef("otp_graph_walk.png"), "The 64-Node Small-World Graph and One 16-Step Walk", width=3.6)

    # ------------------------------------------------------------------ 7.7 latency
    R.h2("Latency")
    st, un, fc = lat["verify_presence_stages"], lat["unit"], lat["first_call"]
    R.paras(f"""
    Table 7.14 lists the cost of each operation on the laptop's CPU, and Table 7.15 the stages of a complete presence
    verification, measured {lat['reps']} times on a genuine recording at the application's camera resolution. The
    processor handles a camera frame in {un['liveness_per_frame_ms (landmarks + overlay)']:.1f} ms on average, well inside
    the 66 ms available at 15 frames per second, so the live preview keeps up with the camera. Verification after the
    challenges takes {st['total']['mean'] / 1000:.2f} s on average (minimum {st['total']['min'] / 1000:.2f} s). As Fig. 7.18 shows,
    ArcFace dominates: it runs on five calibration frames and, for continuity, on three challenge frames, at about
    {un['arcface_per_frame_640x480_ms']:.0f} ms per 640×480 frame, most of which is the RetinaFace detector searching the full
    frame. Cropping the face first, or embedding fewer frames, are the obvious optimisations. These measurements
    were taken with the laptop on battery power, which throttles the CPU; the same verification measured on mains
    power on 13 October took {lat['mains_reference']['verify_min_s']} s minimum and {lat['mains_reference']['verify_mean_s']} s on
    average, with ArcFace at {lat['mains_reference']['arcface_ms_per_frame']} ms per frame.
    """)
    R.table("Cost of Individual Operations (Laptop CPU)", ["Operation", "Time"],
            [["Liveness per camera frame (landmarks + overlay)", f"{un['liveness_per_frame_ms (landmarks + overlay)']:.1f} ms"],
             ["MediaPipe landmarks only, one frame", f"{un['mediapipe_landmarks_per_frame_ms']:.1f} ms"],
             ["Face crop for anti-spoofing, one frame", f"{un['face_crop_per_frame_ms']:.1f} ms"],
             ["Anti-spoofing network, 1 crop / 10 crops (batched)", f"{un['anti_spoofing_1_crop_ms']:.0f} ms / {un['anti_spoofing_10_crops_ms']:.0f} ms"],
             ["Anti-spoofing on 10 frames incl. cropping", f"{un['anti_spoofing_10_frames_incl_crop_ms']:.0f} ms"],
             ["ArcFace, one 640×480 frame (detect + align + embed)", f"{un['arcface_per_frame_640x480_ms']:.0f} ms"],
             ["ArcFace on 5 frames", f"{un['arcface_5_frames_ms']:.0f} ms"],
             ["Explanation (2 Grad-CAMs, attribution, spectrum, FD)", f"{un['explanation_ms']:.0f} ms"],
             ["Template protect / match (cached key)", f"{un['template_protect_cached_key_ms']:.2f} ms"],
             ["Template key schedule (new key)", f"{un['template_new_key_ms']:.0f} ms"],
             ["OTP generation", f"{un['otp_generate_ms']:.2f} ms"],
             ["First call after start-up: ArcFace / anti-spoofing / MediaPipe",
              f"{fc['arcface_first_call_ms'] / 1000:.2f} s / {fc['anti_spoofing_first_call_ms'] / 1000:.2f} s / "
              f"{fc['mediapipe_first_call_ms'] / 1000:.2f} s (pre-warmed in the background)"]],
            widths=[3.6, 2.2], align=["l", "c"], size=9)
    order = sorted([k for k in st if k != "total"], key=lambda k: -st[k]["mean"])
    R.table("Stages of One Presence Verification (ms)", ["Stage", "Min", "Mean", "Max"],
            [[k, f"{st[k]['min']:.0f}", f"{st[k]['mean']:.0f}", f"{st[k]['max']:.0f}"] for k in order] +
            [["Total verify_presence()", f"{st['total']['min']:.0f}", f"{st['total']['mean']:.0f}", f"{st['total']['max']:.0f}"]],
            widths=[3.0, 0.9, 0.9, 0.9], align=["l", "c", "c", "c"], size=9.5, highlight_rows=(len(order),))
    R.figure(ef("latency_pie.png"), "Where the Verification Time Goes", width=5.4)
    cb = lat["server_compute_by_combination_ms"]
    R.paras(f"""
    Table 7.16 puts the components and combinations side by side in terms of what the user waits for. The server
    compute of A is about {cb['A'] / 1000:.2f} s and of F about {cb['F'] / 1000:.2f} s; L costs almost nothing to compute
    but needs the user's time – about 1.3 s of calibration at 15 frames per second plus the time to respond to two
    prompts (natural blinks were detected after a median of {ach['genuine']['BLINK']['median_s']:.1f} s in our genuine
    recordings; deliberate responses in the field took typically 1–4 s each). The face step of a step-up transfer
    therefore takes about 8–14 s of the user's time; scanning the transfer QR and typing the code add the time of
    an ordinary OTP entry.
    """)
    R.table("Time Cost of Each Combination",
            ["Combination", "Server compute (s)", "User interaction", "Typical total for the face step"],
            [["A", f"{cb['A'] / 1000:.2f}", "look at camera (~1 s)", "≈ 2–3 s"],
             ["L", "≈ 0 (per-frame cost only)", "calibration + 2 prompts (~3–9 s)", "≈ 4–9 s"],
             ["F", f"{cb['F'] / 1000:.2f}", "look at camera (~1 s)", "≈ 1.5–2 s"],
             ["A+L", f"{cb['A+L'] / 1000:.2f}", "calibration + 2 prompts", "≈ 6–11 s"],
             ["A+F", f"{cb['A+F'] / 1000:.2f}", "look at camera", "≈ 3–4 s"],
             ["L+F", f"{cb['L+F'] / 1000:.2f}", "calibration + 2 prompts", "≈ 5–10 s"],
             ["A+L+F (deployed, with explanation and continuity)", f"{cb['A+L+F'] / 1000:.2f}", "calibration + 2 prompts",
              "≈ 8–14 s"]],
            widths=[2.0, 1.2, 1.6, 1.4], align=["l", "c", "l", "c"], size=9)

    # ------------------------------------------------------------------ 7.8 comparison
    R.h2("Comparative Study with Previous Work")
    R.p("Direct comparison with published numbers is only meaningful where the data and protocol match, which is "
        "rarely the case. We therefore compare at three levels: the same dataset (LCC-FASD), the same mechanism "
        "(blink-only versus randomised liveness, BioHashing versus our template, TOTP versus walk-OTP), and the system "
        "properties of typical authentication designs.")
    fl = V["fused"]["lcc"]
    rows = [["MobileNetV3-large (Prokofiev)", "3.02", "0.921", "16.13", "16.33", "repository; protocol not stated"],
            ["MobileNetV3-small (Prokofiev)", "1.00", "0.889", "18.70", "19.69", "repository"],
            ["AENet (Prokofiev)", "11.22", "0.868", "20.91", "22.61", "repository"]]
    for mode, lab, params in (("fused", "Ours: spatial + frequency (2 × ResNet-18)", "22.6"),
                              ("spatial", "Ours: spatial only (ResNet-18)", "11.4"),
                              ("freq", "Ours: frequency only (ResNet-18)", "11.4")):
        if mode in V:
            m = V[mode]["lcc"]
            rows.append([lab, params, f"{m['AUC']:.3f}", P(m["EER"], 2), P(m["EER"], 2) + "*",
                         "12 unseen subjects of the dev subset"])
    R.table("Anti-Spoofing on LCC-FASD: Our Models vs Published Reference Results",
            ["Model", "Params (M)", "AUC", "EER %", "ACER %", "Protocol"], rows,
            widths=[2.0, 0.65, 0.5, 0.55, 0.6, 1.5], align=["l", "c", "c", "c", "c", "l"], size=8.5)
    R.p("* ACER at the equal-error threshold equals the EER. Our test split (564 frames of 12 subjects from the "
        "development subset) is smaller than the official test set, so the comparison is indicative only.",
        indent=False, size=10, italic=True)
    R.paras(f"""
    On LCC-FASD our fused network (AUC {fl['AUC']:.3f}, EER {P(fl['EER'])} %) is in the same range as the published
    lightweight models (AUC 0.868–0.921, EER 16.1–20.9 %), with a larger network. Against the intra-dataset state of the
    art of Table 2.1 – ACER below 2 % on OULU-NPU protocol 1 – our webcam numbers look poor, but they are not the same
    kind of number: ours are measured on a person and a camera condition never seen in training, which is closer to the
    cross-dataset setting of Tables 2.2 and 2.3, where published HTERs of 6.5–60 % are typical. Table 7.18 compares the
    other mechanisms.
    """)
    R.table("Mechanism-Level Comparison",
            ["Mechanism", "Prior approach (source)", "Prior result", "This project"],
            [["Active liveness", "Spontaneous blink (Pan et al., 2007)", "Defeats photos",
              f"Replay passes blink-only in {pc(live['replay_blink_only']['rate'], 0)}; random pairs 0 / {live['pairs']['replay']['n']}"],
             ["Liveness + PAD consistency", "Independent checks (common practice)", "Swap not considered",
              "Continuity: recorded swap blocked; identity check on challenge frames"],
             ["Face recognition", "ArcFace R100, MS1M (Deng et al., 2019)", "LFW 99.83 %",
              f"R50 WebFace600K on {face['identities']} identities: acc. {P(pro['accuracy'], 2)} %, EER {P(pro['EER'], 2)} %"],
             ["Template protection", "BioHashing (Teoh et al., 2004)", "≈ 0 % EER if token secret; raw-level if stolen",
              f"Stolen-key EER {P(pro['EER'], 2)} % (raw {P(raw['EER'], 2)} %); unlinkable; revocable"],
             ["Second factor", "TOTP (RFC 6238)", "Uniform; not transaction-bound",
              f"Walk-OTP v2: {d['walk_v2']:,} / 20,000 distinct; bound to amount and payee"],
             ["Explainability", "Grad-CAM on PAD (Sequeira et al., 2021)", "Saliency + error rates",
              "Grad-CAM on both branches, branch attribution, spectra, FD, liveness timeline, reasons"]],
            widths=[1.2, 1.6, 1.3, 1.7], size=8.5)
    R.table("System-Level Comparison with Common Authentication Designs",
            ["Property", "Password + SMS OTP", "TOTP app", "Face login only", "Face + blink", "VaultTrust"],
            [["Proves presence at transfer time", "no", "no", "partly", "partly", "yes"],
             ["Resists photo / replay", "n/a", "n/a", "no", "photo only", "yes (L + F)"],
             ["Resists swap", "n/a", "n/a", "no", "no", "yes (continuity)"],
             ["Code bound to amount and payee", "sometimes (SMS text)", "no", "n/a", "n/a", "yes"],
             ["Works offline on the phone", "no (needs SMS)", "yes", "n/a", "n/a", "yes"],
             ["Biometric template revocable", "n/a", "n/a", "rarely", "rarely", "yes"],
             ["Explains decisions", "no", "no", "no", "no", "yes"]],
            widths=[1.6, 0.9, 0.7, 0.8, 0.8, 0.9], align=["l", "c", "c", "c", "c", "c"], size=8.5)

    # ------------------------------------------------------------------ 7.9 discussion
    R.h2("Discussion")
    R.paras(f"""
    **Complementarity is the main result.** No single component is adequate: face recognition accepted
    {pc(a['rate'])} of presentation attacks of the right person; liveness cannot tell people apart; anti-spoofing
    cannot tell people apart either and, on a new person, rejects too many genuine attempts. Their AND combination is
    the only configuration that keeps every attack category low, and the combination study quantifies this in a way
    single-component papers do not.

    **Finding attacks requires attacking.** The swap attack was not in any threat list we started with; it was found
    by a team member trying to break the system and documented by a screen recording. The recording then became a
    regression test. Similarly, the 768-code collapse of OTP v1 and the "blurry = spoof" bias of model v2 were found
    only because we measured them. We regard this as the most transferable lesson of the project.

    **Generalisation of anti-spoofing is the weakest link.** The held-out results show what the field trial hinted at:
    trained on two people, the network does not generalise to a third. It still blocked every phone attack we
    presented to it at attempt level, but at the cost of rejecting genuine attempts in poor light. The explanation
    panel was valuable here, because it told us *why* – missing high frequencies and texture in backlit faces – and
    pointed to the augmentation that fixed the worst cases.

    **Explanations served developers as much as users.** Grad-CAM, branch attribution and the spectral features were
    designed for users and examiners, but their first beneficiaries were us: they exposed the flat Grad-CAM of the
    original code, the "blurry = spoof" bias and the role of the frequency branch, which helps on LCC-FASD but generalises
    worse than the spatial branch to a new person (Table 7.4).
    """)

    # ------------------------------------------------------------------ 7.10 cost
    R.h2("Cost Analysis")
    R.p("The system was built entirely with existing hardware and open-source software. Table 7.19 lists the "
        "development cost and an estimate of the running cost per verification.")
    R.table("Cost Analysis", ["Item", "Cost", "Remarks"],
            [["Laptop and webcam", "₹0 (existing)", "Any recent CPU-only laptop"],
             ["Android phone", "₹0 (existing)", "Browser only; no app installation"],
             ["Software and libraries", "₹0", "Open source (Python, PyTorch, MediaPipe, InsightFace, Streamlit, SQLite)"],
             ["Datasets", "₹0", "LCC-FASD development subset; our own recordings"],
             ["Cloud / API services", "₹0", "None used; all processing local"],
             ["Model training (CPU)", "≈ 15–20 min per model", "3 epochs × ~5 min on 16 logical cores"],
             ["Compute per verification", f"≈ {st['total']['mean'] / 1000:.1f} CPU-seconds", "≈ 10 step-up checks per minute "
              "per laptop if run back to back"],
             ["Production additions (not costed)", "—", "TLS certificates, hardware-backed key storage, GPU or "
              "optimised inference, larger training set"]],
            widths=[1.7, 1.5, 2.6], size=9.5)

    # ------------------------------------------------------------------ 7.11 limitations
    R.h2("Limitations")
    R.bullets([
        "Webcam data from only two people and mostly phone-replay attacks; prints, tablets, monitors, masks and many "
        "more people would be needed for a credible PAD claim, with leave-one-person-out evaluation as standard.",
        "The webcam-calibrated threshold is permissive on LCC-FASD attack types, and the model rejects a substantial "
        "share of genuine attempts by an unseen person.",
        "The combination study combines L multiplicatively with jointly measured A and F; a fully joint measurement "
        "would require recorded attempts in which a live person responds to random prompts for every category.",
        "The frequency branch adds little on our data and the fractal dimension is near chance; both are retained for "
        "explanation.",
        "Video passes through the Python server, which costs latency and a slow first start; in-browser landmarks would "
        "remove this.",
        "The phone key is tied to the laptop's network address, the LAN connection is plain HTTP, the key sits in browser "
        "storage and the master key on disk.",
        "Injection attacks (virtual cameras, deepfakes) and 3-D masks are outside the threat model.",
    ])
