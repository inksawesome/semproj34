"""Chapter 8 Summary, Chapter 9 References, Appendices."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def P(x, nd=1):
    return f"{100 * x:.{nd}f}"


def chapter8(R, M):
    face, live, fas, sysm, otp, lat = M["face"], M["live"], M["fas"], M["sys"], M["otp"], M["lat"]
    T = sysm["combinations"]["deployed"]
    R.chapter("Summary")
    R.h2("Conclusion")
    R.p("We set out to authorise high-value bank transfers with evidence that the account holder is present and "
        "approves exactly that transfer, using only a laptop webcam, a laptop CPU and a phone browser. VaultTrust does "
        "this with a presence check that combines face recognition on a cancelable template (A), active liveness with "
        "continuity (L) and passive spatial-frequency anti-spoofing (F), followed by a random-walk one-time password "
        "bound to the amount and the payee. The system works end to end, is covered by 105 automated tests, and explains "
        "each of its decisions. The evaluation supports the following conclusions:")
    R.bullets([
        f"Face recognition on the protected template is accurate – EER {P(face['protected']['EER'], 2)} %, no false accept "
        f"in {face['pairs_impostor']:,} impostor pairs, {P(face['attempt_level_protected']['FRR'], 2)} % genuine rejection per "
        f"attempt – but alone it accepted {P(face['attacks_vs_own_template']['rate'])} % of photo and replay attacks of the "
        "right person.",
        f"Randomised two-challenge liveness stopped every replay ({live['pairs']['replay']['n']} pairs) and photo attempt, "
        f"whereas a blink-only policy let {P(live['replay_blink_only']['rate'], 0)} % of replays through.",
        "The continuity mechanism closes the swap attack found in our own system; the recorded attack is blocked, and "
        "quick, well-aligned swaps that pass the motion rules are caught by the identity check on the challenge frames.",
        f"The combination A+L+F achieves {P(T['A+L+F']['accuracy'])} % accuracy, {P(T['A+L+F']['precision'])} % precision and "
        f"F1 {T['A+L+F']['f1']:.3f} on a balanced population, with every attack type accepted in at most "
        f"{P(T['A+L+F']['APCER_max'], 2)} % of attempts, against {P(T['A']['accuracy'])} % accuracy for A alone.",
        f"The random-walk OTP v2 is as uniform as TOTP ({otp['distinct']['walk_v2']:,} distinct codes from 20,000 secrets; "
        f"χ² p = {otp['uniformity']['buckets_100']['p_value']:.2f}) and changes completely when the amount changes by one cent.",
        f"A full presence verification takes {lat['verify_presence_stages']['total']['mean'] / 1000:.1f} s on the CPU, "
        "dominated by face detection for ArcFace.",
        "The weakest link is the generalisation of anti-spoofing to people and conditions not seen in training, which "
        "lowers the genuine acceptance of the full system and must be addressed with more diverse data.",
    ], kind="check")
    R.p("Against the registered title, the project delivered a working graph-based random-walk OTP – in a corrected, "
        "verified and transaction-bound form – and used fractal geometry through the chaotic logistic-map key schedule "
        "of the cancelable template and the fractal-dimension explanation feature, while our measurements showed that "
        "fractal features should not be part of the decision.")
    R.h2("Future Work")
    R.bullets([
        "**Data.** Record ten or more people and more attack instruments (prints, tablets, monitors, masks) under varied "
        "light, and make leave-one-person-out evaluation the standard for every model update.",
        "**Generalisation.** Try domain-generalisation training (for example single-side domain generalisation), central "
        "difference convolutions or auxiliary depth supervision, and calibrate per camera.",
        "**In-browser liveness.** Run the MediaPipe landmarker in the browser (MediaPipe JS) so that only the selected "
        "frames reach the server, removing camera lag and the slow first start.",
        "**Injection attacks.** Detect virtual cameras and deepfake streams, for example with challenge-dependent screen "
        "illumination or device attestation.",
        "**Second factor hardening.** Serve the phone page over HTTPS, keep the key in a WebAuthn credential or a "
        "native app's secure storage, cache the graph, and add push approval.",
        "**Latency.** Pass face crops to ArcFace instead of full frames and reuse detections, targeting under 2 s for "
        "verification.",
        "**Delegated access.** Implement the team's third idea – letting an account holder delegate limited transfers to "
        "another person with their own face and phone.",
    ])


REFS = [
    "Boulkenafet, Z., Komulainen, J., & Hadid, A. (2016). Face spoofing detection using colour texture analysis. *IEEE Transactions on Information Forensics and Security, 11*(8), 1818–1830. https://doi.org/10.1109/TIFS.2016.2555286",
    "Boulkenafet, Z., Komulainen, J., Li, L., Feng, X., & Hadid, A. (2017). OULU-NPU: A mobile face presentation attack database with real-world variations. In *12th IEEE International Conference on Automatic Face & Gesture Recognition (FG 2017)* (pp. 612–618). IEEE.",
    "Chingovska, I., Anjos, A., & Marcel, S. (2012). On the effectiveness of local binary patterns in face anti-spoofing. In *Proceedings of the International Conference of the Biometrics Special Interest Group (BIOSIG)* (pp. 1–7). IEEE.",
    "Commission Delegated Regulation (EU) 2018/389 of 27 November 2017 supplementing Directive (EU) 2015/2366 of the European Parliament and of the Council with regard to regulatory technical standards for strong customer authentication and common and secure open standards of communication. (2018). *Official Journal of the European Union, L 69*, 23–43.",
    "Cooley, J. W., & Tukey, J. W. (1965). An algorithm for the machine calculation of complex Fourier series. *Mathematics of Computation, 19*(90), 297–301.",
    "Deng, J., Dong, W., Socher, R., Li, L.-J., Li, K., & Fei-Fei, L. (2009). ImageNet: A large-scale hierarchical image database. In *IEEE Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 248–255).",
    "Deng, J., Guo, J., Xue, N., & Zafeiriou, S. (2019). ArcFace: Additive angular margin loss for deep face recognition. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 4690–4699).",
    "Deng, J., Guo, J., Ververas, E., Kotsia, I., & Zafeiriou, S. (2020). RetinaFace: Single-shot multi-level face localisation in the wild. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 5203–5212).",
    "George, A., & Marcel, S. (2019). Deep pixel-wise binary supervision for face presentation attack detection. In *2019 International Conference on Biometrics (ICB)* (pp. 1–8). IEEE.",
    "Government of India. (2023). *The Digital Personal Data Protection Act, 2023* (No. 22 of 2023). Ministry of Law and Justice.",
    "Grassi, P. A., Fenton, J. L., Newton, E. M., Perlner, R. A., Regenscheid, A. R., Burr, W. E., Richer, J. P., Lefkovitz, N. B., Danker, J. M., Choong, Y.-Y., Greene, K. K., & Theofanos, M. F. (2017). *Digital identity guidelines: Authentication and lifecycle management* (NIST Special Publication 800-63B). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-63b",
    "He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning for image recognition. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 770–778).",
    "International Organization for Standardization. (2017). *Information technology — Biometric presentation attack detection — Part 3: Testing and reporting* (ISO/IEC Standard No. 30107-3:2017).",
    "International Organization for Standardization. (2022). *Information security, cybersecurity and privacy protection — Biometric information protection* (ISO/IEC Standard No. 24745:2022).",
    "Jia, Y., Zhang, J., Shan, S., & Chen, X. (2020). Single-side domain generalization for face anti-spoofing. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 8484–8493).",
    "Johnson, W. B., & Lindenstrauss, J. (1984). Extensions of Lipschitz mappings into a Hilbert space. *Contemporary Mathematics, 26*, 189–206.",
    "Jourabloo, A., Liu, Y., & Liu, X. (2018). Face de-spoofing: Anti-spoofing via noise modeling. In *Proceedings of the European Conference on Computer Vision (ECCV)* (pp. 290–306).",
    "Kartynnik, Y., Ablavatski, A., Grishchenko, I., & Grundmann, M. (2019). *Real-time facial surface geometry from monocular video on mobile GPUs* (arXiv:1907.06724). arXiv.",
    "Kollreider, K., Fronthaler, H., Faraj, M. I., & Bigun, J. (2007). Real-time face detection and motion analysis with application in “liveness” assessment. *IEEE Transactions on Information Forensics and Security, 2*(3), 548–558. https://doi.org/10.1109/TIFS.2007.902037",
    "Kong, A., Cheung, K.-H., Zhang, D., Kamel, M., & You, J. (2006). An analysis of BioHashing and its variants. *Pattern Recognition, 39*(7), 1359–1368.",
    "Krawczyk, H., Bellare, M., & Canetti, R. (1997). *HMAC: Keyed-hashing for message authentication* (RFC 2104). Internet Engineering Task Force.",
    "Li, J., Wang, Y., Tan, T., & Jain, A. K. (2004). Live face detection based on the analysis of Fourier spectra. In *Biometric Technology for Human Identification* (Proc. SPIE 5404, pp. 296–303). https://doi.org/10.1117/12.541955",
    "Liu, Y., Jourabloo, A., & Liu, X. (2018). Learning deep models for face anti-spoofing: Binary or auxiliary supervision. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 389–398).",
    "Liu, Y., Stehouwer, J., Jourabloo, A., & Liu, X. (2019). Deep tree learning for zero-shot face anti-spoofing. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 4680–4689).",
    "Loshchilov, I., & Hutter, F. (2019). Decoupled weight decay regularization. In *International Conference on Learning Representations (ICLR)*.",
    "Lovász, L. (1993). Random walks on graphs: A survey. In *Combinatorics, Paul Erdős is Eighty* (Vol. 2, pp. 1–46). János Bolyai Mathematical Society.",
    "Lugaresi, C., Tang, J., Nash, H., McClanahan, C., Uboweja, E., Hays, M., Zhang, F., Chang, C.-L., Yong, M. G., Lee, J., Chang, W.-T., Hua, W., Georg, M., & Grundmann, M. (2019). *MediaPipe: A framework for building perception pipelines* (arXiv:1906.08172). arXiv.",
    "Määttä, J., Hadid, A., & Pietikäinen, M. (2011). Face spoofing detection from single images using micro-texture analysis. In *2011 International Joint Conference on Biometrics (IJCB)* (pp. 1–7). IEEE.",
    "May, R. M. (1976). Simple mathematical models with very complicated dynamics. *Nature, 261*(5560), 459–467.",
    "M'Raihi, D., Bellare, M., Hoornaert, F., Naccache, D., & Ranen, O. (2005). *HOTP: An HMAC-based one-time password algorithm* (RFC 4226). Internet Engineering Task Force.",
    "M'Raihi, D., Machani, S., Pei, M., & Rydell, J. (2011). *TOTP: Time-based one-time password algorithm* (RFC 6238). Internet Engineering Task Force.",
    "National Institute of Standards and Technology. (2015). *Secure hash standard (SHS)* (FIPS PUB 180-4). U.S. Department of Commerce.",
    "Pan, G., Sun, L., Wu, Z., & Lao, S. (2007). Eyeblink-based anti-spoofing in face recognition from a generic webcamera. In *IEEE 11th International Conference on Computer Vision (ICCV)* (pp. 1–8). https://doi.org/10.1109/ICCV.2007.4409068",
    "Pan, S., Hoque, S., & Deravi, F. (2022). An attention-guided framework for explainable biometric presentation attack detection. *Sensors, 22*(9), 3365.",
    "Paszke, A., Gross, S., Massa, F., Lerer, A., Bradbury, J., Chanan, G., Killeen, T., Lin, Z., Gimelshein, N., Antiga, L., Desmaison, A., Köpf, A., Yang, E., DeVito, Z., Raison, M., Tejani, A., Chilamkurthy, S., Steiner, B., Fang, L., Bai, J., & Chintala, S. (2019). PyTorch: An imperative style, high-performance deep learning library. In *Advances in Neural Information Processing Systems 32* (pp. 8024–8035).",
    "Patel, V. M., Ratha, N. K., & Chellappa, R. (2015). Cancelable biometrics: A review. *IEEE Signal Processing Magazine, 32*(5), 54–65.",
    "Prokofiev, K. (n.d.). *Light-weight face anti-spoofing* [Computer software]. GitHub. https://github.com/kprokofi/light-weight-face-anti-spoofing",
    "Ratha, N. K., Connell, J. H., & Bolle, R. M. (2001). Enhancing security and privacy in biometrics-based authentication systems. *IBM Systems Journal, 40*(3), 614–634.",
    "Sarkar, N., & Chaudhuri, B. B. (1994). An efficient differential box-counting approach to compute fractal dimension of image. *IEEE Transactions on Systems, Man, and Cybernetics, 24*(1), 115–120. https://doi.org/10.1109/21.259692",
    "Selvaraju, R. R., Cogswell, M., Das, A., Vedantam, R., Parikh, D., & Batra, D. (2017). Grad-CAM: Visual explanations from deep networks via gradient-based localization. In *Proceedings of the IEEE International Conference on Computer Vision (ICCV)* (pp. 618–626).",
    "Sequeira, A. F., Gonçalves, T., Silva, W., Pinto, J. R., & Cardoso, J. S. (2021). An exploratory study of interpretability for face presentation attack detection. *IET Biometrics, 10*(4), 441–455. https://doi.org/10.1049/bme2.12045",
    "Smith, L. N., & Topin, N. (2019). Super-convergence: Very fast training of neural networks using large learning rates. In *Artificial Intelligence and Machine Learning for Multi-Domain Operations Applications* (Proc. SPIE 11006, 1100612).",
    "Soukupová, T., & Čech, J. (2016). Real-time eye blink detection using facial landmarks. In *21st Computer Vision Winter Workshop (CVWW)*, Rimske Toplice, Slovenia.",
    "Szegedy, C., Vanhoucke, V., Ioffe, S., Shlens, J., & Wojna, Z. (2016). Rethinking the Inception architecture for computer vision. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 2818–2826).",
    "Teoh, A. B. J., Ngo, D. C. L., & Goh, A. (2004). BioHashing: Two factor authentication featuring fingerprint data and tokenised random number. *Pattern Recognition, 37*(11), 2245–2255.",
    "Timoshenko, D., Simonchik, K., Shutov, V., Zhelezneva, P., & Grishkin, V. (2019). Large crowdcollected facial anti-spoofing dataset. In *2019 Computer Science and Information Technologies (CSIT)* (pp. 123–126). IEEE. https://doi.org/10.1109/CSITechnol.2019.8895208",
    "Wang, Z., Zhao, C., Qin, Y., Zhou, Q., & Lei, Z. (2018). *Exploiting temporal and depth information for multi-frame face anti-spoofing* (arXiv:1811.05118). arXiv.",
    "Watts, D. J., & Strogatz, S. H. (1998). Collective dynamics of ‘small-world’ networks. *Nature, 393*(6684), 440–442.",
    "Wen, D., Han, H., & Jain, A. K. (2015). Face spoof detection with image distortion analysis. *IEEE Transactions on Information Forensics and Security, 10*(4), 746–761.",
    "Yu, Z., Qin, Y., Li, X., Zhao, C., Lei, Z., & Zhao, G. (2023). Deep learning for face anti-spoofing: A survey. *IEEE Transactions on Pattern Analysis and Machine Intelligence, 45*(5), 5609–5631. https://doi.org/10.1109/TPAMI.2022.3215850",
    "Yu, Z., Zhao, C., Wang, Z., Qin, Y., Su, Z., Li, X., Zhou, F., & Zhao, G. (2020). Searching central difference convolutional networks for face anti-spoofing. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 5295–5305).",
    "Zhang, Y., Yin, Z., Li, Y., Yin, G., Yan, J., Shao, J., & Liu, Z. (2020). CelebA-Spoof: Large-scale face anti-spoofing dataset with rich annotations. In *Proceedings of the European Conference on Computer Vision (ECCV)* (pp. 70–85).",
    "Zhang, Z., Yan, J., Liu, S., Lei, Z., Yi, D., & Li, S. Z. (2012). A face antispoofing database with diverse attacks. In *2012 5th IAPR International Conference on Biometrics (ICB)* (pp. 26–31). IEEE.",
    "Zhu, Z., Huang, G., Deng, J., Ye, Y., Huang, J., Chen, X., Zhu, J., Yang, T., Lu, J., Du, D., & Zhou, J. (2021). WebFace260M: A benchmark unveiling the power of million-scale deep face recognition. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 10492–10502).",
]


def chapter9(R, M):
    R.chapter("References")
    for ref in REFS:
        p = R.doc.add_paragraph(style="Reference")
        R._runs(p, ref, size=11)
    R.h2("Software")
    for ref in ["Streamlit Inc. (2026). *Streamlit* (Version 1.64.0) [Computer software]. https://streamlit.io",
                "Google. (2026). *MediaPipe Face Landmarker* (MediaPipe 0.10.35) [Computer software]. https://ai.google.dev/edge/mediapipe",
                "InsightFace contributors. (n.d.). *InsightFace: 2D and 3D face analysis project* (buffalo_l models) [Computer software]. https://github.com/deepinsight/insightface",
                "Python Cryptographic Authority. (2026). *cryptography* (Version 50.0.0; Fernet) [Computer software]. https://cryptography.io"]:
        p = R.doc.add_paragraph(style="Reference")
        R._runs(p, ref, size=11)


def _snippet(path, start_pat, n_lines):
    try:
        lines = open(os.path.join(ROOT, path), encoding="utf8").read().split("\n")
    except OSError:
        return "# (source not found)"
    for i, ln in enumerate(lines):
        if start_pat in ln:
            return "\n".join(lines[i:i + n_lines])
    return "# (snippet not found)"


def appendices(R, M):
    R.unnumbered_chapter("Appendix A – Sample Code")
    R.p("The following excerpts are taken unchanged from the project source. The complete code is in the project "
        "repository.", indent=False)
    for title, path, pat, n in (
            ("A.1  Decision fusion (ui_components.py)", "ui_components.py", "def verify_presence", 46),
            ("A.2  Server-side continuity check (ui_components.py)", "ui_components.py", "def _check_continuity", 28),
            ("A.3  Face continuity in the liveness processor (liveness_engine.py)", "liveness_engine.py", "def _continuity", 22),
            ("A.4  Cancelable template (biometric_template.py)", "biometric_template.py", "def _logistic_sequence", 34),
            ("A.5  Random-walk OTP core (walk_otp.py)", "semprojOTP/otp_system/walk_otp.py", "def _derive_walk_seed", 64),
            ("A.6  Verification with grace window (walk_otp.py)", "semprojOTP/otp_system/walk_otp.py", "def verify_otp", 40)):
        p = R.p(f"**{title}**", indent=False, keep=True)
        R.code(_snippet(path, pat, n))

    R.unnumbered_chapter("Appendix B – User Manual")
    R.p("**Starting the system.** On the laptop run `python -m streamlit run app.py` and open http://localhost:8501. "
        "Connect the phone to the same Wi-Fi or hotspot as the laptop.", indent=False)
    R.p("**Opening an account.**", indent=False)
    R.numbered([
        "Choose *Open an account* and enter your e-mail address; type the six-digit code sent to it.",
        "Face enrolment: look straight at the camera until calibration completes, then follow the two prompts (for "
        "example *Blink twice*, *Turn your head LEFT*). Keep only your face in view and avoid strong light behind you.",
        "Scan the pairing QR code with the phone camera. The phone page stores the key; the laptop shows a pairing check "
        "code, which you type in to confirm. The account is created.",
    ])
    R.p("**Signing in.** Choose *Sign in*, enter the e-mail address and complete the face check. The evidence card "
        "shows the result of every check; expand *Why? Explainable-AI evidence* to see the Grad-CAM maps, spectrum and "
        "liveness timeline.", indent=False)
    R.p("**Making a transfer.**", indent=False)
    R.numbered([
        "On *Accounts*, choose the payee and the amount and press *Send*. Amounts below $1,000 are sent immediately.",
        "For $1,000 or more, the *Verify this transfer* page opens. Complete the face check (step 1).",
        "Scan the transfer QR with the phone. Check the amount and payee shown on the phone, press *Approve*, and type the "
        "six-digit code into the laptop within its 30-second window. Press *Sign & send*.",
        "If the phone says it has no key for this address (for example after the laptop changed network), use *Re-pair my "
        "phone*; a fresh face check is required.",
    ])
    R.p("**Troubleshooting.**", indent=False)
    R.chapter_no, R.tab_no = "B", 0
    R.table("Troubleshooting", ["Symptom", "Remedy"],
            [["Calibration does not finish", "Face the camera; only one face in view; improve front lighting"],
             ["A turn challenge times out", "Turn further (about 20°) and hold briefly; the view is mirrored"],
             ["Anti-spoofing rejects a real face", "Avoid back-light; move closer; retry (3 attempts)"],
             ["Phone shows 'not paired'", "Re-pair from the transfer page or Accounts (laptop IP changed)"],
             ["Code rejected as expired", "Use the code currently shown on the phone; codes change every 30 s"],
             ["First check is slow", "Models load at start-up; wait a few seconds after launching"]],
            widths=[2.2, 3.6], size=9.5)

    R.unnumbered_chapter("Appendix C – Reproducing the Evaluation")
    R.p("All results of Chapter 7 are produced by scripts in `evaluation/`, which write JSON files and figures to "
        "`reports/eval/`. The report itself is generated from those files by `docs/report/build_report.py`.", indent=False)
    R.code("""
# held-out anti-spoofing models (Nilay held out): fused and spatial-only
python -u training/train_fas_v2.py --ablation --save-all --test-person nilay --epochs 3 --max-train 2000 \\
       --out models/eval/fas_ablation.pth --reports-dir reports/eval/ablation

python evaluation/eval_face.py        # A: verification, attacks, template properties
python evaluation/eval_fas.py         # F: ablation, attempt level, versions
python evaluation/eval_liveness.py    # L: challenges, photo / replay / swap attacks, field trial
python evaluation/eval_system.py      # unit-wise and combination study
python evaluation/eval_otp.py         # OTP uniformity, binding, graph, speed
python evaluation/eval_latency.py     # per-stage latency (run on an idle machine)

python docs/report/diagrams.py && python docs/report/figures_extra.py && python docs/report/screenshots.py
python docs/report/build_report.py
""")
