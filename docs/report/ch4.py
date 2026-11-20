"""Chapter 4 Design Approach and Details."""

import os

FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")


def f(name):
    return os.path.join(FIG, name)


def chapter4(R, M):
    R.chapter("Design Approach and Details")
    R.h2("Design Approach / Materials and Methods")
    R.paras("""
    We followed an iterative, evidence-driven approach. Each component was first built to the specification of
    Review 1 or of the anti-spoofing brief, then exercised end to end with real people and real attacks in front
    of the laptop camera; every failure observed was traced to a cause, fixed, and turned into an automated test.
    The development log in Table 5.4 lists twenty such findings. This section describes the resulting design,
    from the overall architecture down to each module.
    """)
    R.h3("System architecture")
    R.paras("""
    Fig. 4.1 shows the architecture. VaultTrust runs as a single Python process on the laptop. The user interacts
    through a Streamlit web application in the laptop browser; the camera stream travels from the browser to the
    server over WebRTC at 640×480 pixels and 15 frames per second, and every frame is processed by the liveness
    processor on the server. The verification pipeline in `ui_components.py` fuses the outputs of the three
    machine-learning engines – MediaPipe landmarks, the anti-spoofing network and InsightFace – with the
    cancelable template. A second, very small web server on port 8600 serves the phone authenticator, a static
    page whose JavaScript computes codes entirely on the phone. The phone never sends anything to the server:
    information reaches it only through QR codes shown on the laptop screen, and the code travels back through
    the user, who types it in.
    """)
    R.figure(f("architecture.png"), "System Architecture of VaultTrust", width=5.8)
    R.table("Main Source Modules and Their Responsibilities",
            ["Module", "Responsibility"],
            [["app.py", "Streamlit pages and routing (st.navigation with URLs, so browser back/forward work); "
              "sign-up, sign-in, accounts, step-up transfer, re-pairing, model lab; policies and limits"],
             ["ui_components.py", "Camera widget with live instruction panel; background verification job; "
              "decision fusion (verify_presence); server-side continuity; evidence card and explanation panel"],
             ["liveness_engine.py", "LivenessProcessor: calibration, random challenges, continuity rules, sampling "
              "of challenge frames; measure() wrapper around MediaPipe Face Landmarker"],
             ["fas_engine.py", "Anti-spoofing model loading, batched scoring, median decision, Grad-CAM on both "
              "branches, branch attribution, spectrum, HF energy, fractal dimension; operating point and policy"],
             ["spatial_frequency_model.py, frequency_transform.py", "Teammates' dual ResNet-18 network and the FFT input"],
             ["face_engine.py", "RetinaFace detection, 5-point alignment, ArcFace embedding, cosine similarity"],
             ["biometric_template.py", "Logistic-map key schedule, protect() and match() in the protected domain"],
             ["walk_otp.py, authenticator/walk_otp.js", "Random-walk OTP v2 (identical Python and JavaScript)"],
             ["database.py", "SQLite schema and migrations, Fernet encryption, atomic settlement, audit log, used codes"],
             ["training/train_fas_v2.py, tools/", "Retraining, calibration, labelling, reports"],
             ["tests/, semprojOTP/otp_system/tests/", "105 automated tests"]],
            widths=[1.9, 3.9], size=9)

    R.h3("Use cases and interaction")
    R.paras("""
    Fig. 4.2 shows the use cases. The customer opens an account, signs in, views accounts and the security log,
    and makes transfers; transfers above the limit include the phone approval use case. The evaluator or examiner
    uses the Model Lab page to inspect metrics, change the anti-spoofing operating point and switch between the
    enforce and advisory policies. Fig. 4.3 gives the sequence of messages for a step-up transfer, from the
    transfer request to settlement.
    """)
    R.figure(f("usecase.png"), "Use Case Diagram", width=5.4)
    R.figure(f("sequence_stepup.png"), "Sequence Diagram of a Step-Up Transfer", width=5.8)

    R.h3("Active liveness module")
    R.paras("""
    The liveness processor is a small state machine that runs on every camera frame (Fig. 4.4). Each frame is
    mirrored, reduced to 480 pixels wide and passed to the Face Landmarker; a single process-wide re-entrant
    lock serialises all MediaPipe calls, which removed an intermittent native crash we observed when the camera
    was torn down. In the CALIBRATE state the processor waits for 20 frontal frames (|yaw| < 15°,
    |pitch| < 20°), keeps every second one as a *clean frame* for the passive check, and takes the median of
    each signal as the user's baseline. It then asks two distinct challenges drawn at random from five
    (Table 4.2), each judged relative to the baseline and limited to 9 seconds. The original implementation
    used one challenge, an inverted smile metric and an uncalibrated pitch; these were replaced by
    blendshapes, the transformation matrix and baseline-relative thresholds.
    """)
    R.figure(f("liveness_state_machine.png"), "State Machine of the Liveness Processor", width=5.6)
    R.table("Liveness Challenges and Their Pass Conditions",
            ["Challenge", "Signal", "Pass condition (relative to the user's baseline)"],
            [["Blink twice", "mean eyeBlink blendshape", "rises above max(0.45, rest + 0.3), then falls below "
              "max(0.25, rest + 0.1); twice"],
             ["Turn your head left / right", "yaw from the transformation matrix", "Δyaw > 18° in the requested "
              "direction (mirrored display)"],
             ["Look up", "pitch from the transformation matrix", "pitch decreases by more than 12°"],
             ["Smile", "mean mouthSmile blendshape", "above max(0.45, rest + 0.25)"],
             ["(all)", "time and faces", "9 s per challenge; more than one face fails the attempt"]],
            widths=[1.4, 1.8, 2.6], size=9.5)
    R.figure(f("liveness_timeline.png"), "Liveness Signals of a Genuine Recording, as Seen by the Processor", width=5.8)
    R.p("Fig. 4.5 shows the signals for one of the genuine webcam recordings: natural blinks appear as sharp peaks "
        "of the eye-closure score well above the 0.45 threshold, while yaw and pitch stay within a few degrees of the "
        "baseline when the user is not asked to move. The same timeline is drawn for every attempt in the "
        "explanation panel of the application.")

    R.h3("Continuity: closing the swap attack")
    R.paras("""
    On 10 October one of us held a phone showing a photo during calibration, then removed it and performed the
    challenges in person. The attempt was accepted. The cause was a design gap rather than a bug: the passive check
    scored only the calibration frames (the phone), which the model of that day (v4) wrongly scored 0.72, while the
    challenges were performed by a live person, so each check passed on a different presentation. We added
    continuity at two levels (Table 4.3). In the processor, the face is tracked from the first calibration frame
    to the last challenge frame; a gap without a face, a jump of the face box, a sudden change of its size or a
    second face restarts calibration (discarding the frames collected so far) or, during the challenges, fails
    the attempt. On the server, frames sampled during the challenges must show the same person as the calibration
    frames and, when neutral, must also pass anti-spoofing. On genuine recordings the largest frame-to-frame shift
    we measured was 0.02–0.03 face widths and the largest gap 0.07 s; the recorded attack produced a 0.94 s gap
    and a 0.9 face-width jump, so the thresholds leave a wide margin on both sides.
    """)
    R.table("Continuity Rules",
            ["Level", "Rule", "Value", "Effect"],
            [["Processor", "Gap without a face", "> 0.7 s", "restart calibration / fail during challenges"],
             ["Processor", "Face-box centre shift between detections", "> 0.5 face widths", "restart / fail"],
             ["Processor", "Face-box scale change", "> 1.5× or < 1/1.5×", "restart / fail"],
             ["Processor", "More than one face", "any frame", "restart / fail"],
             ["Processor", "Challenge frame sampling", "every 3rd frame, max 24", "evidence for the server"],
             ["Server", "Identity: ArcFace of 3 challenge frames vs calibration", "cos ≥ 0.35", "fail if lower"],
             ["Server", "Anti-spoofing on ≥ 3 neutral challenge frames", "median ≥ τ_{F}", "fail if lower (enforce)"]],
            widths=[0.9, 2.4, 1.2, 1.4], size=9)

    R.h3("Passive anti-spoofing module")
    R.paras("""
    The network designed by our teammates (Fig. 4.6) has two ResNet-18 encoders. The spatial encoder receives the
    224×224 RGB face crop with ImageNet normalisation; the frequency encoder receives, for each colour channel, the
    shifted log-magnitude Fourier spectrum. The two 512-D features are concatenated and classified by a small head
    (fully connected 256, batch normalisation, ReLU, dropout 0.4, fully connected 2). The model has 22,616,450
    parameters: 11.18 million per encoder and 0.26 million in the head. The face crop is the bounding box of the
    MediaPipe landmarks with a 20 % margin, identical in training and inference. The decision takes the median
    real-probability over the ten clean calibration frames and compares it with a threshold calibrated on the
    deployment camera.
    """)
    R.figure(f("fas_network.png"), "Dual-Branch Spatial and Frequency Anti-Spoofing Network", width=5.8)
    R.paras("""
    The original model trained only the classification head on frozen ImageNet features using every LCC-FASD
    image, without a held-out split; it scored 1.0 AUC on LCC-FASD because it had memorised it, and it accepted
    phone replays on our webcam. We rebuilt the training procedure (Table 4.4): a subject-wise split so that no
    person appears in two splits, fine-tuning of the last two stages of both encoders, augmentation that imitates
    our camera (distance, back-light, blur, sensor noise, compression), webcam samples weighted three times, and a
    threshold chosen at the equal-error point on webcam validation clips. Table 4.5 summarises the model versions.
    """)
    R.table("Training Configuration of the Anti-Spoofing Network",
            ["Setting", "Value"],
            [["Split", "Subject-wise (LCC-FASD idNN groups 52 / 11 / 12); webcam by person; first clip per (person, "
              "attack) to validation"],
             ["Trainable layers", "layer3 and layer4 of both encoders + head (ImageNet initialisation)"],
             ["Optimiser and schedule", "AdamW, one-cycle learning rate (1e-4 backbone, 1e-3 head)"],
             ["Loss", "Cross-entropy with label smoothing 0.1"],
             ["Batch / epoch", "16 / 2,000 samples drawn per epoch; 3 epochs; best epoch by validation ACER"],
             ["Sampling", "Webcam samples weighted 3×"],
             ["Augmentation (both classes, before both branches)", "random crop 78–100 %, flip, brightness/contrast, "
              "white balance, downscale 35–80 %, blur, gamma 1.2–1.8, sensor noise, JPEG quality 35–95"],
             ["Threshold", "Equal-error point on the webcam part of the validation split"]],
            widths=[2.0, 3.8], size=9.5)
    R.table("Anti-Spoofing Model Versions",
            ["Version", "Training data", "Threshold", "Outcome"],
            [["v1 (original)", "Head only on frozen features; all 416 LCC real images; no split", "0.50",
              "Memorised LCC-FASD; accepted phone replays"],
             ["v2", "LCC-FASD, subject split, fine-tuned", "0.50", "'Blurry = spoof' bias; rejected backlit real faces"],
             ["v3", "+ Rwitankar webcam videos; Nilay held out", "0.235", "Evaluation model for an unseen person"],
             ["v4", "+ all webcam captures", "0.165", "Deployed 8–11 Oct; fooled by a phone held close"],
             ["v5 (deployed)", "+ 10 Oct phone attack and 10 Oct real sign-in", "0.185",
              "Blocks that phone (0.72 → 0.03); trained 11 Oct"]],
            widths=[1.0, 2.3, 0.7, 1.8], size=9)

    R.h3("Explainability module")
    R.paras("""
    Every decision is accompanied by an evidence card and an explanation panel. The card lists each check with its
    score and threshold and, on rejection, plain-language reasons generated from the numbers (for example, which
    challenge timed out, which branch carried the strongest evidence, how far the high-frequency energy lies from
    the live-face mean). The panel shows the Grad-CAM maps of both branches, the branch attribution, the radial
    spectrum against the mean of live training faces, the high-frequency energy and fractal dimension against
    their live ranges, and the liveness timeline. Fig. 4.7 shows the maps for two real and two replayed LCC-FASD
    faces. The original Grad-CAM targeted the average-pooling layer, whose 1×1 output produced a flat map, and fed
    an unnormalised crop with a zero frequency tensor; both were corrected so that the maps are computed on
    layer4 for the exact tensors classified. All explanation is computed locally; an unused wrapper for an
    external language-model API was removed.
    """)
    R.figure(f("gradcam_examples.png"), "Grad-CAM Maps and Branch Evidence for Real and Replayed Faces (Deployed Model)",
             width=4.6)

    R.h3("Face recognition and cancelable template")
    R.paras("""
    The first integrated version resized an unaligned MediaPipe crop to 112×112 and passed it to ArcFace, and the
    sign-in page did not run face recognition at all after enrolment. Both were replaced. Faces are now detected by
    RetinaFace (det_10g, detection size 320), aligned to the 112×112 ArcFace template by a similarity transform on
    five landmarks, and embedded by the ResNet-50 ArcFace model (w600k_r50); enrolment and sign-in average the
    embeddings of five frames. The embedding is never stored. Instead, Fig. 4.8 shows how it is turned into a
    1,024-byte protected template with a per-user key, and how a probe is matched in the protected domain. The
    template key and the OTP secret are encrypted at rest with Fernet (AES-128-CBC with HMAC-SHA256) under a
    master key kept outside the database.
    """)
    R.figure(f("template_pipeline.png"), "Cancelable Template: Enrolment and Matching", width=5.8)

    R.h3("Random-walk OTP and phone authenticator")
    R.paras("""
    The OTP engine (Fig. 4.9, Table 4.6) derives a 32-byte seed with HMAC-SHA256 from the shared secret K, the
    8-byte time step T and the SHA-256 hash of the context – empty when pairing, and `TX|reference|amount in
    cents|payee` for a transfer. The seed is expanded into a byte stream by hashing it with a counter, and
    uniform choices are drawn from the stream by rejection sampling. The walk starts at a node chosen from the
    stream and takes 16 steps on a fixed, public 64-node graph (a ring lattice of degree 6 with Watts–Strogatz
    rewiring probability 0.3, built from a public seed with the same stream construction, so every platform builds
    the same graph). The code is the RFC 4226 dynamic truncation of SHA-256 of a version tag and the whole path.
    """)
    R.figure(f("otp_pipeline.png"), "Random-Walk OTP Version 2", width=5.8)
    R.table("OTP Parameters", ["Parameter", "Value"],
            [["Secret K", "32 random bytes; shown once at pairing as base32 in a QR code"],
             ["Time step", "30 s; T = ⌊unix time / 30⌋"], ["Graph", "64 nodes, lattice degree 6, rewiring p = 0.3, public seed"],
             ["Walk", "start node + 16 steps (17 nodes)"], ["Code", "6 digits, SHA-256 of the path, dynamic truncation"],
             ["Verification window", "current step; previous step only within 10 s after it changed; next step only if "
              "the phone is ≤ 10 s ahead"],
             ["Replay protection", "a step ≤ the last accepted step is refused per account and scope"],
             ["Attempts", "3 wrong codes block the transfer"]],
            widths=[1.5, 4.3], size=9.5)
    R.paras("""
    The first version of the engine used Python's Mersenne-Twister generator for the walk and applied the
    truncation directly to the encoded path bytes. Because node identifiers are small numbers stored in two bytes,
    the four-byte truncation window covered only two node identifiers, and the 6-digit space collapsed: 20,000
    random secrets produced only 768 distinct codes, so a code could be guessed in about 800 attempts. Version 2
    hashes the whole path first and uses a cryptographic byte stream; Section 7.6 shows that its codes are as
    uniform as those of standard TOTP. The JavaScript implementation in the phone page uses a pure-JavaScript
    SHA-256 and HMAC, because browsers disable their built-in cryptography API on plain-HTTP local-network pages;
    twelve fixed test vectors give identical graphs, paths and codes in both languages.

    The phone authenticator stores K in the browser's local storage when the pairing QR is scanned; the key travels
    only in the URL fragment, which browsers never send to a server, and is removed from the address bar
    immediately. A transfer QR carries the reference, amount, payee and account; the phone shows them, and only
    after the user presses Approve does it reveal the code. Because browser storage is separated per origin (IP
    address and port), a change of the laptop's network address makes the phone report that it has no key; the
    application detects this from the stored pairing address and offers a re-pairing flow that requires a fresh
    face check.
    """)

    R.h3("Decision fusion and policies")
    R.p("The final decision is the logical AND of all checks (Fig. 4.10). The anti-spoofing check can run in two "
        "policies: *enforce*, the default, in which a low score rejects the attempt, and *advisory*, in which the score "
        "is shown and logged as a risk signal but does not block – useful while collecting data on a new camera. "
        "Table 4.7 lists the limits that apply around the decision.")
    R.figure(f("decision_fusion.png"), "Decision Fusion of the Presence Check", width=5.6)
    R.table("Limits and Policies", ["Item", "Value"],
            [["Step-up limit", "$1,000 (transfers at or above it need face + phone)"],
             ["Presence attempts per transfer", "3, then the transfer is blocked (BLOCKED_PRESENCE)"],
             ["OTP attempts per transfer", "3, then blocked (BLOCKED_OTP)"],
             ["E-mail code at sign-up", "valid 10 minutes, 5 tries"], ["Pairing check code", "5 tries"],
             ["Face check reuse for re-pairing", "180 s"], ["Anti-spoofing policy", "enforce (default) or advisory"],
             ["Match thresholds", "τ_{A} = 0.40 (template), τ_{id} = 0.35 (continuity identity)"]],
            widths=[2.4, 3.4], size=9.5)

    R.h3("Data design")
    R.p("Fig. 4.11 shows the four tables of the SQLite database and Fig. 4.12 the main classes and modules. "
        "Transactions record their status and, for step-up transfers, the full evidence of the decision as JSON. "
        "The audit table is the per-user security log; used_otps stores the last accepted time step per account and "
        "scope for replay protection. Settlement debits the sender and records the transaction inside one database "
        "transaction, so a failure cannot leave money half-moved.")
    R.figure(f("er_diagram.png"), "Entity-Relationship Diagram of the Database", width=5.2)
    R.figure(f("class_diagram.png"), "Class and Module Diagram", width=5.8)

    R.h2("Codes and Standards")
    R.p("Table 4.8 lists the standards and regulations that informed the design and how each was applied. None of "
        "them was formally certified; they were used as design references.")
    R.table("Standards and Regulations Applied",
            ["Standard / regulation", "Subject", "Application in VaultTrust"],
            [["ISO/IEC 30107-3:2017", "PAD testing and reporting", "APCER per attack type, BPCER, ACER in Chapter 7"],
             ["ISO/IEC 24745:2022", "Biometric information protection", "Irreversible, unlinkable, renewable template; "
              "unlinkability and revocation measured"],
             ["RFC 4226 (HOTP), RFC 6238 (TOTP)", "One-time passwords", "Time step, dynamic truncation, verification window"],
             ["RFC 2104 (HMAC), FIPS 180-4 (SHA-256)", "Keyed hashing", "Walk seed, byte stream, path hash, key schedule"],
             ["EU Delegated Regulation 2018/389 (PSD2 RTS)", "Strong customer authentication, dynamic linking",
              "Step-up with two factors; code bound to amount and payee"],
             ["NIST SP 800-63B", "Digital identity – authenticators", "Rate limiting of codes, replay prevention, "
              "out-of-band device"],
             ["Digital Personal Data Protection Act, 2023 (India)", "Personal data", "Faces processed locally; raw "
              "embeddings not stored; data folders excluded from version control"],
             ["OWASP secure coding practice", "Web application security", "Parameterised SQL, secrets outside the "
              "repository, no secrets in URLs sent to servers"]],
            widths=[1.9, 1.5, 2.4], size=9)

    R.h2("Threat Model")
    R.p("We assume an attacker who knows the victim's e-mail address, may have taken over the victim's session or "
        "password, can obtain photos and videos of the victim from social media, and can stand in front of the camera "
        "themselves. The attacker does not control the laptop's software or the victim's phone. Table 4.9 lists the "
        "threats, the defences and where each was tested.")
    R.table("Threats, Defences and Tests",
            ["Threat", "Defence", "Evidence"],
            [["Stolen password or hijacked session", "Step-up needs a live face and the phone at transfer time",
              "AppTest workflows (Section 6.5)"],
             ["Printed or on-screen photo", "L (cannot blink or smile) + F (texture, spectrum)", "Sections 7.3–7.5"],
             ["Replayed video", "Random, distinct challenges + F", "Section 7.4; e2e test"],
             ["Different live person", "A: template match below 0.40", "Section 7.2"],
             ["Swap: photo during calibration, live attacker", "Continuity (processor + identity + F on challenges)",
              "Recorded attack replay; Section 7.4"],
             ["Code for a modified transfer", "Context hash in the seed (dynamic linking)", "Section 7.6"],
             ["Code replay or brute force", "used_otps, 3 attempts, uniform 10⁶ code space", "Section 7.6; tests"],
             ["Template database leak", "Cancelable template; re-keying; Fernet for keys", "Section 7.2"],
             ["Not covered", "Virtual-camera / deepfake injection, 3-D masks, compromised phone or laptop, missing "
              "TLS on the LAN", "Future work"]],
            widths=[1.8, 2.3, 1.7], size=9)

    R.h2("Constraints, Alternatives and Trade-offs")
    R.paras("""
    The design was shaped by three constraints: a CPU-only laptop, an ordinary webcam, and very little labelled data
    from that webcam. Table 4.10 records the main alternatives we considered and why we chose as we did.
    """)
    R.table("Alternatives Considered and Trade-offs",
            ["Decision", "Alternatives", "Choice and reason"],
            [["Anti-spoofing backbone", "MobileNetV3, EfficientNet-B0, ResNet-50",
              "ResNet-18 ×2 (brief's recommendation): fast enough on CPU (≈ 48 ms per frame in a batch of 10), "
              "pretrained weights available"],
             ["Frequency representation", "DWT sub-bands, phase spectrum", "FFT log-magnitude: simplest; DWT left as "
              "an option in the brief"],
             ["Fine-tuning depth", "Head only; full network", "layer3–4 + head: head-only memorised LCC; full network "
              "over-fits a 2-person webcam set"],
             ["Threshold", "0.5; min-ACER; EER on LCC", "EER on webcam validation: 0.5 rejected real webcam faces; "
              "min-ACER unstable on few clips"],
             ["Liveness challenges", "Blink only; one random challenge", "Two distinct random challenges: a replay "
              "of natural blinking passes blink-only"],
             ["Where liveness runs", "In the browser (MediaPipe JS)", "Server (Python): one code base, simpler to test; "
              "costs latency and a slow first start (future work)"],
             ["Second factor", "SMS OTP, TOTP app, push", "Walk-OTP on a phone web page: offline, no app install, "
              "transaction-bound; requires same network"],
             ["Walk seed", "Walk as the only PRF (Review 1)", "HMAC-SHA256 seed: keyed security; walk adds the "
              "transaction-bound path"],
             ["Template protection", "Fuzzy vault, homomorphic encryption, BioHashing (binarised)",
              "Key-derived orthonormal projection: keeps ArcFace accuracy, revocable, fast (3.8 ms per match)"],
             ["Fractal features", "Concatenate fractal dimension to the embedding (Review 1)",
              "Explanation only: near-chance PAD power and no identity information"],
             ["Anti-spoofing policy", "Always enforce", "Enforce by default, advisory switch for data collection"]],
            widths=[1.4, 1.7, 2.7], size=8.5)
