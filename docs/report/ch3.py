"""Chapter 3 Technical Specification."""

import os

FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")


def f(name):
    return os.path.join(FIG, name)


def chapter3(R, M):
    R.chapter("Technical Specification")
    R.p("This chapter specifies what the system must do, what it runs on and with, the data it was built and "
        "evaluated with, and the concepts on which each component rests.")
    R.h2("Requirements")
    R.h3("Functional requirements")
    R.table("Functional Requirements",
            ["ID", "Requirement", "Realised by"],
            [["FR1", "Open an account with a verified e-mail, an enrolled face and a paired phone", "Sign-up page"],
             ["FR2", "Sign in with a live face check against the account's protected template", "Sign-in page"],
             ["FR3", "Show balances, transactions and a per-user security log", "Accounts page"],
             ["FR4", "Settle transfers below the step-up limit immediately and atomically", "database.settle_transaction"],
             ["FR5", "Require a fresh presence check for transfers ≥ $1,000", "Verify-transfer page"],
             ["FR6", "Require a phone code bound to the amount and payee before settling a step-up transfer",
              "walk_otp + authenticator"],
             ["FR7", "Reject replayed, expired or wrong codes; block after 3 wrong codes or 3 failed presence checks",
              "used_otps table, counters"],
             ["FR8", "Explain every decision (reasons, scores, Grad-CAM, liveness timeline)", "Evidence card"],
             ["FR9", "Pair a new phone (re-pair) after a fresh face check", "Pair-phone page"],
             ["FR10", "Switch accounts and navigate with the browser's back / forward buttons", "st.navigation pages"],
             ["FR11", "Show model metrics, the operating point and the enforce / advisory policy", "Model Lab page"]],
            widths=[0.5, 3.6, 1.7], size=9)
    R.h3("Non-functional requirements")
    R.table("Non-Functional Requirements",
            ["Category", "Requirement", "How it is met"],
            [["Security", "No raw face embedding stored; secrets encrypted at rest",
              "Cancelable template; Fernet for template key and OTP secret"],
             ["Security", "Codes valid only briefly and only for one transfer", "30-s steps, 10-s grace, context hash, replay table"],
             ["Privacy", "Faces processed locally; no third-party API", "All models run on the laptop; Gemini wrapper removed"],
             ["Performance", "Camera feedback in real time; verification within a few seconds",
              "15 fps processing at ~11 ms/frame; verification ≈ 4–5 s on CPU"],
             ["Usability", "Clear instructions and reasons; retries", "Live instruction panel, 3 attempts, evidence card"],
             ["Portability", "Runs on a CPU-only Windows laptop; phone needs only a browser", "ONNX Runtime, PyTorch CPU, pure JS"],
             ["Reliability", "Automated regression tests", "105 tests (unit, integration, end-to-end, recorded attack)"],
             ["Maintainability", "Retraining and recalibration documented", "train_fas_v2.py, tools/, PROJECT_RECORD.md"]],
            widths=[1.0, 2.4, 2.4], size=9)

    R.h2("Hardware and Software Specification")
    R.table("Hardware Used",
            ["Item", "Specification", "Role"],
            [["Laptop", "Windows 11, 16 logical CPU cores, no GPU used", "Server, training, evaluation"],
             ["Webcam", "Built-in laptop camera, used at 640×480, 15 fps", "Face capture"],
             ["Phone", "Android smartphone with a modern browser", "Authenticator (QR scan, code display)"],
             ["Network", "Phone hotspot / Wi-Fi, laptop and phone on the same network", "Phone loads the authenticator page"]],
            widths=[1.1, 2.9, 1.9], size=9.5)
    R.table("Software Stack",
            ["Layer", "Software (version)", "Use"],
            [["Language", "Python 3.14.3; JavaScript (Node 22.14 for tests)", "Server and evaluation; phone page"],
             ["Web UI", "Streamlit 1.64.0; streamlit-webrtc 0.78.1, aiortc 1.15.0, PyAV 17.1.0", "Pages, camera stream"],
             ["Vision", "MediaPipe 0.10.35 (Face Landmarker); OpenCV 5.0", "Landmarks, blendshapes, image ops"],
             ["Deep learning", "PyTorch 2.14.1, torchvision 0.29.1", "Anti-spoofing network, Grad-CAM"],
             ["Face recognition", "InsightFace 2.0 (buffalo_l), ONNX Runtime 1.30.0", "RetinaFace + ArcFace"],
             ["Numerics", "NumPy 2.4.2, SciPy 1.17, scikit-learn 1.8.0", "Metrics, statistics"],
             ["Security", "cryptography 50.0.0 (Fernet), hashlib / hmac", "Encryption, HMAC, SHA-256"],
             ["Storage", "SQLite 3 (standard library)", "Users, transactions, audit"],
             ["Other", "qrcode 8.2, Plotly 6.6.0, matplotlib, FastAPI 0.128.8, pytest 9.1.1", "QR, charts, OTP API, tests"]],
            widths=[1.1, 3.1, 1.7], size=9)

    R.h2("Datasets")
    R.paras("""
    Table 3.5 lists the data used. LCC-FASD supplied most of the training images; our own recordings supplied
    the deployment camera. All face data is personal data: the folders holding our recordings and captures, the
    database and the master key are excluded from version control, and the figures in this report that show
    faces use LCC-FASD images or are pixelated.
    """)
    R.table("Data Used for Training and Evaluation",
            ["Source", "Content", "Use"],
            [["LCC-FASD development subset", "416 real and 2,590 spoof face crops; subject groups (idNN)",
              "Training / validation / test with subject-wise split (test: 12 unseen subjects, 564 frames)"],
             ["Webcam videos (Rwitankar, 9 Oct)", "3 real (15 fps, 1280×720) and 2 phone replays (30 fps); 446 crops at 4 fps",
              "Training, calibration; liveness and continuity experiments"],
             ["App captures (Nilay, 8–10 Oct)", "10 face crops per attempt: 5 real attempts, 2 phone attacks, 1 unseen real",
              "Held-out person for the evaluation models; deployed-model checks"],
             ["Screen recording (10 Oct)", "Sign-in, step-up transfer and the swap attack (135 s, 1080p)",
              "Regression test of continuity; screenshots (redacted)"],
             ["Field log (8–12 Oct)", "Every presence decision of 4 test accounts with reasons and scores",
              "Field-trial statistics"]],
            widths=[1.5, 2.3, 2.1], size=9)

    R.h2("Background Concepts")
    R.h3("Convolutional and residual networks")
    R.paras("""
    A convolutional neural network learns banks of small filters whose responses, stacked over several layers,
    represent increasingly abstract image structure. Very deep plain networks are hard to optimise; He et al.
    (2016) introduced residual blocks that learn a correction F(x) to their input x instead of a complete
    mapping (Eqn. 3.1). ResNet-18, used for both branches of our anti-spoofing network, stacks eight such
    two-layer blocks in four stages (layer1–layer4) with 64, 128, 256 and 512 channels, followed by global
    average pooling to a 512-dimensional feature. We start from ImageNet weights and fine-tune only layer3,
    layer4 and the classifier, which keeps training feasible on a CPU and limits over-fitting to the small
    webcam set.
    """)
    R.equation("y = ", ("sub", "F", "residual"), "(x, {W_i}) + x")
    R.p("The classifier outputs two logits z_{spoof} and z_{real}; the probability that a face is real is their softmax "
        "(Eqn. 3.2), and the network is trained with label-smoothed cross-entropy.")
    R.equation(("sub", "p", "real"), " = ", ("f", ["exp(", ("sub", "z", "real"), ")"],
                                              ["exp(", ("sub", "z", "real"), ") + exp(", ("sub", "z", "spoof"), ")"]))
    R.h3("Fourier spectra of face images")
    R.paras("""
    The two-dimensional discrete Fourier transform (Eqn. 3.3) decomposes an M×N image into sinusoids of
    different frequencies and orientations; the fast Fourier transform computes it in O(MN log MN) operations.
    Re-imaging a face – printing it or showing it on a screen and photographing it again – changes the spectrum:
    printing and defocus remove high frequencies, while the pixel grid of a screen and the raster of a printer add
    periodic peaks and moiré. The frequency branch of our network receives, for each colour channel, the shifted
    log-magnitude spectrum log(1 + |F(u, v)|), min-max normalised to [0, 1]. As an interpretable summary we also
    compute the high-frequency energy ratio of Eqn. 3.4, the share of spectral power above 0.4 of the Nyquist
    frequency, in the spirit of Li et al. (2004). Fig. 3.1 shows real and replayed faces with their spectra.
    """)
    R.equation("F(u, v) = ", ("sum", "x=0", "M−1", [("sum", "y=0", "N−1", ["f(x, y) ", ("sup", "e", "−j2π(ux/M + vy/N)")])]))
    R.equation(("sub", "HF", "ratio"), " = ", ("f", [("sum", "ρ(u,v) > 0.4", "", "|F(u,v)|²")],
                                               [("sum", "u,v", "", "|F(u,v)|²")]))
    R.figure(f("fft_examples.png"), "Real and Replayed LCC-FASD Faces with Their Log-Magnitude Spectra", width=5.6)
    R.h3("Gradient-weighted class activation mapping")
    R.paras("""
    Grad-CAM (Selvaraju et al., 2017) explains a CNN decision for class c by weighting the K feature maps A^{k} of a
    convolutional layer with the average gradient of the class score y^{c} (Eqn. 3.5) and keeping the positive part
    of the weighted sum (Eqn. 3.6). We apply it to layer4 of both encoders (7×7 maps, up-sampled to 224×224) for
    the exact tensors that were classified. In addition, we split the evidence between the branches by summing
    gradient × activation over the 512 spatial and the 512 frequency features of the fused vector for the score
    difference z_{real} − z_{spoof}; a positive sum pushes towards "real", a negative one towards "spoof".
    """)
    R.equation(("subsup", "α", "k", "c"), " = ", ("f", "1", "Z"), ("sum", "i", "", [("sum", "j", "", ("f", ["∂", ("sup", "y", "c")],
                                                                                                  ["∂", ("subsup", "A", "ij", "k")]))]))
    R.equation(("sup", "L", "c"), " = ReLU(", ("sum", "k", "", [("subsup", "α", "k", "c"), ("sup", "A", "k")]), ")")
    R.h3("Fractal dimension by differential box counting")
    R.paras("""
    The fractal dimension D measures how the detail of a pattern scales with the size of the measuring box. For
    a grey-level image, the differential box-counting method of Sarkar and Chaudhuri (1994) treats intensity as a
    third dimension: the image is divided into s×s blocks, each block's intensity range is covered by boxes of
    height proportional to s, and the number of boxes N_{r} is counted for each scale r = s/M. D is the slope of
    log N_{r} against log(1/r) (Eqn. 3.7). We compute it on the inner 70 % of a 128×128 grey face crop with box
    sizes 2–32. A recaptured face is expected to be smoother; in practice, as Fig. 3.2 shows, the real and spoof
    distributions overlap almost completely, which is why D is shown as an explanation feature and not used in
    any decision.
    """)
    R.equation("D = ", ("sub", "lim", "r→0"), " ", ("f", ["log ", ("sub", "N", "r")], "log(1/r)"))
    R.figure(f("spectrum_fd.png"), "Radial Spectra of Real and Replayed Faces and Fractal-Dimension Distributions", width=5.8)
    R.h3("Facial landmarks, blendshapes and head pose")
    R.paras("""
    The MediaPipe Face Landmarker returns, for each face, 478 normalised landmarks, 52 blendshape scores in [0, 1]
    (for example eyeBlinkLeft, mouthSmileRight) and a 4×4 facial transformation matrix whose upper-left 3×3 block
    R is the head rotation. We derive yaw and pitch from R (Eqn. 3.8), blink as the mean of the two eyeBlink
    scores, and smile as the mean of the two mouthSmile scores. For reference we also log the eye aspect ratio of
    Soukupová and Čech (2016), computed from six landmarks p_{1}…p_{6} around each eye (Eqn. 3.9); it falls towards zero
    as the eye closes. All challenge thresholds are applied to the change of a signal relative to the user's own
    median during calibration, so that glasses, a resting smile or a tilted camera do not trigger or block a
    challenge.
    """)
    R.equation(("sub", "θ", "yaw"), " = atan2(", ("sub", "R", "02"), ", ", ("sub", "R", "22"), "),   ",
               ("sub", "θ", "pitch"), " = asin(−", ("sub", "R", "12"), ")")
    R.equation("EAR = ", ("f", ["‖", ("sub", "p", "2"), " − ", ("sub", "p", "6"), "‖ + ‖", ("sub", "p", "3"), " − ",
                                ("sub", "p", "5"), "‖"], ["2 ‖", ("sub", "p", "1"), " − ", ("sub", "p", "4"), "‖"]))
    R.h3("ArcFace embeddings and cosine matching")
    R.paras("""
    ArcFace trains a network so that the angle θ between a face's feature and the weight vector of its own
    identity is small. It adds an angular margin m to that angle inside the softmax loss (Eqn. 3.10, s is a
    scale), which forces embeddings of the same person into a tight cone and pushes different people apart. At
    test time the classifier is discarded: two faces are compared by the cosine of the angle between their
    L2-normalised 512-D embeddings (Eqn. 3.11). Our deployed threshold is τ_{A} = 0.40.
    """)
    R.equation("L = −log ", ("f", [("sup", "e", "s·cos(θᵧ + m)")],
                             [("sup", "e", "s·cos(θᵧ + m)"), " + ", ("sum", "j≠y", "", [("sup", "e", "s·cos θⱼ")])]))
    R.equation("cos(e, e′) = ", ("f", "e · e′", "‖e‖ ‖e′‖"))
    R.h3("Cancelable templates with a chaotic key schedule")
    R.paras("""
    The logistic map of Eqn. 3.12 is the textbook example of deterministic chaos (May, 1976): for r close to 4,
    nearby starting points diverge exponentially and the orbit fills the interval in a fractal-like pattern. We use
    it as a key schedule. From a per-user 256-bit key, HMAC-SHA256 derives a starting point x₀ ∈ (0.01, 0.99) and a
    parameter r ∈ [3.99, 3.9999]; after 500 burn-in iterations, one sequence defines a permutation π of the 512
    embedding dimensions and a second fills a 512×256 matrix that is orthonormalised by QR decomposition into W.
    The protected template is the normalised projection of Eqn. 3.13. Because W has orthonormal rows, the
    projection approximately preserves angles between embeddings (in the spirit of the Johnson–Lindenstrauss
    lemma), so matching can be done directly in the protected domain. Because it maps 512 dimensions to 256, it
    is many-to-one and cannot be inverted uniquely, and a new key gives a new, unrelated template.
    """)
    R.equation(("sub", "x", "n+1"), " = r ", ("sub", "x", "n"), " (1 − ", ("sub", "x", "n"), ")")
    R.equation("t = ", ("f", ["W · e[π]"], ["‖W · e[π]‖"]), ",   match(e′) = cos(W · e′[π], t)")
    R.h3("HMAC, HOTP/TOTP and random walks on graphs")
    R.paras("""
    HMAC turns a hash function H into a keyed message authentication code (Eqn. 3.14). HOTP (RFC 4226) applies
    HMAC-SHA1 to an 8-byte counter C and *dynamically truncates* the 20-byte result: the low four bits of the last
    byte select an offset o, the four bytes from o (with the top bit cleared) form an integer, and the code is that
    integer modulo 10^{d} (Eqn. 3.15). TOTP (RFC 6238) uses C = ⌊t/30⌋. A random walk on a graph G = (V, E) moves from
    the current node to a neighbour chosen at random; on a connected, non-bipartite graph the walk's distribution
    converges to one proportional to node degree (Lovász, 1993). Small-world graphs (Watts and Strogatz, 1998) –
    a ring lattice with a fraction of edges rewired at random – combine short average path lengths with local
    structure. In our scheme (Section 4.1.9) the choices of the walk are drawn from a keyed byte stream, and the
    code is derived from a hash of the entire path.
    """)
    R.equation("HMAC(K, m) = H((K ⊕ opad) ‖ H((K ⊕ ipad) ‖ m))")
    R.equation("HOTP(K, C) = (", ("sub", "DT", "31"), "(HMAC-SHA1(K, C)))  mod  ", ("sup", "10", "d"))
    R.h3("Evaluation metrics")
    R.paras("""
    For presentation attack detection we follow ISO/IEC 30107-3. The attack presentation classification error
    rate (APCER) is the share of attack presentations accepted as bona fide; it is computed per attack type and
    the worst type is reported. The bona fide presentation classification error rate (BPCER) is the share of
    genuine presentations rejected (Eqn. 3.16). Their mean, ACER, is common in the literature, as is the half total
    error rate HTER = (FAR + FRR)/2. The equal error rate (EER) is the error at the threshold where the two rates are
    equal, and the area under the ROC curve (AUC) summarises separability over all thresholds.

    For the system and combination study we take the *genuine* attempt as the positive class. Precision is then the
    share of accepted attempts that were genuine – a security measure – and recall is the share of genuine attempts
    accepted – a usability measure (Eqns. 3.17–3.19). Accuracy and F1 depend on the mix of genuine and attack
    attempts, which we fix at one to one and state with every table.
    """)
    R.equation("APCER = ", ("f", "FP", "FP + TN"), ",   BPCER = ", ("f", "FN", "TP + FN"),
               ",   ACER = ", ("f", "APCER + BPCER", "2"))
    R.equation("Precision = ", ("f", "TP", "TP + FP"), ",   Recall = ", ("f", "TP", "TP + FN"))
    R.equation("Accuracy = ", ("f", "TP + TN", "TP + TN + FP + FN"))
    R.equation("F1 = ", ("f", "2 · Precision · Recall", "Precision + Recall"))
