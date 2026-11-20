"""Chapter 1 Introduction and Chapter 2 Project Description and Goals (incl. literature survey)."""

import os

FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
EVF = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "reports", "eval", "figures")


def f(name):
    return os.path.join(FIG, name)


def chapter1(R, M):
    R.chapter("Introduction")
    R.paras("""
    Online banking has made it possible to move large sums of money from anywhere, at any time, with a few
    clicks. The same convenience is what attackers exploit. Once a password has been phished, guessed or reused
    from another breach, or a session cookie has been stolen, nothing in a typical banking session proves that
    the person who opened the session is the person who is now sending the money. One-time passwords sent by SMS
    or e-mail help, but they can be intercepted, forwarded under social-engineering pressure, or approved without
    reading what they authorise. This project builds and evaluates an authentication system, VaultTrust, that asks
    for stronger evidence exactly when it matters: at the moment a high-value transfer is made.

    VaultTrust is a working mock bank built in Python. Ordinary actions need only a face sign-in, but any transfer
    of $1,000 or more must be approved twice, there and then: first by the account holder's live, genuine face,
    and then by a code from the account holder's paired phone that is cryptographically bound to the amount and
    the payee of that transfer. The face check is itself built from three complementary components – face
    recognition (A), active liveness (L) and passive anti-spoofing (F) – and a central question of this report is
    how much each of them contributes, alone and in combination.
    """)
    R.h2("Objective")
    R.p("The objective of the project is to design, implement and evaluate a step-up authentication system for "
        "high-value transactions that verifies inherence (a live, genuine, matching face) and possession (a paired "
        "device) at transaction time, explains its decisions, and protects the stored biometric data. The specific "
        "objectives are:")
    R.bullets([
        "To detect presentation attacks (printed or on-screen photos and replayed videos) with a dual-branch "
        "spatial and frequency-domain convolutional network, and to make its decisions inspectable through "
        "Grad-CAM, branch attribution, spectral and fractal descriptors.",
        "To add an active, challenge-response liveness check that a static photo or a replayed video cannot satisfy, "
        "and to make it robust to *swap* attacks by tracking the same face from calibration to the last challenge.",
        "To recognise the account holder with ArcFace embeddings matched in a cancelable, revocable template domain "
        "derived from a chaotic (logistic-map) key schedule, so that the raw embedding is never stored.",
        "To generate second-factor codes with a graph-based random walk, seeded by a shared secret, the time step and "
        "a hash of the transaction, so that a code approves exactly one amount and payee (dynamic linking).",
        "To evaluate every component and every combination of components with standard metrics (accuracy, precision, "
        "recall, F1, APCER, BPCER, ACER, EER, AUC) and latency, and to compare the results with published work.",
    ], kind="check")
    R.h2("Motivation")
    R.paras("""
    Three observations motivated the design. First, authentication in banking is usually strongest at login and
    weakest afterwards: a session, once open, can be used for anything. Regulation has started to address this.
    The European Union's regulatory technical standards for strong customer authentication (Commission Delegated
    Regulation (EU) 2018/389) require that, for remote payments, the payer is shown the amount and the payee and
    that the authentication code is specific to that amount and payee, so that any change invalidates it – a
    principle called dynamic linking. A step-up check at transfer time, with a transaction-bound code, follows the
    same principle.

    Second, face recognition is convenient but, on its own, it answers only *who* is in front of the camera, not
    *whether a person is actually there*. A photograph or a video of the account holder, easily taken from social
    media, presents the right face. Our own measurements in Chapter 7 confirm this sharply: ArcFace matched photo
    and replay attacks of the enrolled person to that person's template in more than 99 % of cases. Presentation
    attack detection (PAD) is therefore not optional, and it must cope with cheap attacks on ordinary laptop
    webcams rather than with laboratory datasets alone.

    Third, both biometric systems and OTP schemes carry secrets that must be protected. A leaked face template
    cannot be changed like a password unless it was protected by a revocable transform, and an OTP scheme is only
    as good as the uniformity of its codes. Our first OTP prototype illustrated this: a subtle truncation error
    collapsed its output to 768 distinct codes, which we discovered only by measuring it (Section 4.1.9). The
    project was therefore driven as much by evaluation as by implementation.
    """)
    R.h2("Background")
    R.paras("""
    Authentication factors are traditionally grouped as something the user *knows* (a password or PIN), *has*
    (a phone, token or card) or *is* (a biometric trait). Multi-factor authentication combines at least two
    independent factors so that compromising one is not enough. Table 1.1 summarises the factors used in this
    project and the attacks each is exposed to.
    """)
    R.table("Authentication Factors and Their Typical Attacks",
            ["Factor", "Example in VaultTrust", "Strength", "Typical attacks"],
            [["Knowledge", "E-mail one-time code at sign-up", "Familiar, cheap", "Phishing, reuse, interception"],
             ["Possession", "Paired phone computing a walk-OTP", "Independent device; offline generation",
              "Device theft, malware, social engineering"],
             ["Inherence", "Live face: liveness + anti-spoofing + ArcFace", "Cannot be forgotten; present at the time",
              "Photo, video replay, mask, deepfake injection, template theft"]],
            widths=[1.0, 1.7, 1.5, 1.8])
    R.paras("""
    A *presentation attack* is an attempt to interfere with a biometric system by presenting an artefact – a
    printed photo, a phone or tablet screen showing a photo or video, a mask – to the sensor (ISO/IEC 30107-3).
    PAD methods are either *passive*, analysing the captured images for texture, reflections, moiré, blur or
    spectral artefacts, or *active*, asking the user to respond to a challenge such as blinking or turning the
    head. The two are complementary: passive methods can be fooled by high-quality media they were not trained
    on, while active methods can be fooled by any medium that happens to contain the requested action. Step-up
    authentication, finally, means asking for additional evidence only when the risk of an action warrants it –
    here, when the amount reaches a limit – so that everyday use stays fast.
    """)
    R.h2("Problem Definition")
    R.p("We state the problem as follows. Given a signed-in banking session and a transfer request "
        "(reference, amount, payee) whose amount is at least a step-up limit, decide in a few seconds, using only a "
        "laptop webcam, a laptop CPU and the account holder's phone, whether the request is being made by the "
        "enrolled account holder who is physically present and who approves exactly this transfer. The decision must:")
    R.bullets([
        "reject printed or on-screen photos, replayed videos, different live people, and combinations of these "
        "(for example a photo during calibration followed by a live attacker) – the attacks listed in Fig. 1.1;",
        "accept the genuine user in the large majority of attempts under normal indoor lighting, with at most a few "
        "retries;",
        "never store the raw face embedding, and allow a leaked template to be revoked;",
        "bind the second factor to the amount and the payee so that a code cannot be reused for a modified transfer, "
        "replayed, or guessed in a few attempts;",
        "explain every rejection in terms a user or an examiner can check.",
    ])
    R.figure(f("threat_map.png"), "Threats Considered and the Defence Responsible for Each", width=5.6)
    R.p("Attacks that require injecting synthetic video directly into the camera stream (virtual cameras, deepfake "
        "injection), three-dimensional masks, and attacks on the operating system or the phone itself are outside "
        "the scope of this project and are discussed as limitations.")
    R.h2("Scope of the Project")
    R.table("Scope of the Project", ["In scope", "Out of scope"],
            [["Web application (Streamlit) for sign-up, sign-in, accounts and transfers with a step-up limit",
              "Integration with a real core-banking system or payment network"],
             ["Active liveness, continuity, passive spatial + frequency anti-spoofing, ArcFace, cancelable template",
              "3-D masks, deepfake / virtual-camera injection, infrared or depth sensors"],
             ["Random-walk OTP with dynamic linking, phone authenticator page, replay protection",
              "Push notifications, app-store mobile app, hardware-backed key storage"],
             ["Training and evaluation on LCC-FASD and on our own webcam recordings; component and combination study",
              "Large-scale user study; certification-grade PAD testing"],
             ["Explanation of decisions (Grad-CAM, attribution, spectra, fractal dimension, liveness timeline)",
              "Natural-language explanations from an external large language model (removed by design)"]],
            widths=[2.9, 2.9])
    R.h2("Contributions")
    R.bullets([
        "An end-to-end, working step-up authentication system with four entry points (sign-up, sign-in, "
        "transfer, re-pairing) and a security log, covered by 105 automated tests.",
        "A *continuity* mechanism that closes a swap attack we discovered in our own system (photo during "
        "calibration, live person during the challenges), verified by replaying the screen recording of the attack.",
        "A retraining pipeline for the teammates' spatial-frequency anti-spoofing network with subject-wise "
        "splits, quality augmentation and threshold calibration on the deployment camera, and an ablation of the "
        "spatial and frequency branches under identical conditions.",
        "A transaction-bound random-walk OTP (version 2) whose code distribution we verified to be uniform after "
        "finding and fixing a 768-code collapse in the first version, with identical Python and JavaScript "
        "implementations.",
        "A unit-wise and combination study of A, L and F over five attempt categories, quantifying what each "
        "component adds, and a comparative study against published results.",
    ], kind="check")
    R.h2("Organisation of the Report")
    R.p("Chapter 2 describes the project and surveys the literature on face anti-spoofing, liveness, face "
        "recognition, template protection, one-time passwords and explainability, ending with the research gaps and "
        "measurable goals. Chapter 3 gives the technical specification: requirements, hardware and software, "
        "datasets and the background concepts with their equations. Chapter 4 presents the design – architecture, "
        "modules, UML diagrams, data design, standards, threat model and trade-offs. Chapter 5 gives the schedule and "
        "milestones, Chapter 6 demonstrates the system, and Chapter 7 reports and discusses all results, including "
        "the combination study, latency, the comparison with previous work and a cost analysis. Chapter 8 concludes "
        "and outlines future work; Chapter 9 lists the references, and the appendices give sample code and a user "
        "manual.")


def chapter2(R, M):
    R.chapter("Project Description and Goals")
    R.h2("Project Description")
    R.paras("""
    The project began, at Review 1 (19 August 2026), as the merger of two ideas registered under the title
    *Design of an Authentication System Using Fractal Geometry with Graph-Based Random-Walk OTP Generation*:
    a face-authentication pipeline whose template is protected by a chaotic or fractal transform, and a second
    factor whose codes come from a random walk on a graph instead of the usual HMAC construction. During the
    semester the face pipeline grew into a full face anti-spoofing module, specified in a separate implementation
    brief with four components: (1) spatial and frequency-domain analysis, (2) passive liveness, (3) active
    liveness and (4) explainable AI. Components 1 and 2 were developed by Magizharasan K and Rwitankar Giri, and
    components 3 and 4 and the random-walk OTP by Nilay Kant Shahi; integration, evaluation and the final
    corrections were carried out together.

    The final system, VaultTrust, places all of this in the setting where it is most useful: authorising a
    high-value bank transfer. Fig. 2.1 shows the complete step-up flow. A transfer below the limit settles at
    once. A transfer at or above it creates a pending transaction and starts the presence check. Only when the
    face check passes does the laptop show a QR code carrying the transfer reference, amount and payee; the phone
    authenticator displays these details, and on approval computes a six-digit code from its secret, the current
    30-second step and a hash of the transfer. The server recomputes the code, checks that the step has not been
    used before and settles the transfer atomically. Every decision, with its reasons and evidence, is written to
    a per-user security log.
    """)
    R.figure(f("stepup_flow.png"), "Step-Up Authorisation Flow of a High-Value Transfer", width=5.2)

    R.h2("Literature Survey")
    R.p("The survey is organised by the components of the system. For every published number quoted in this "
        "section we give the source; numbers were read from the papers themselves.")
    R.h3("Face presentation attack detection")
    R.paras("""
    Early PAD research relied on handcrafted cues. Li et al. (2004) observed that a photograph of a face contains
    less high-frequency energy than the live face, because printing and re-imaging act as low-pass filters, and
    proposed a Fourier-spectrum ratio as a liveness measure; the idea is simple and fast but fails on large,
    sharp photographs. Määttä, Hadid and Pietikäinen (2011) used micro-texture (multi-scale local binary
    patterns) of single images, and Boulkenafet, Komulainen and Hadid (2016) showed that colour texture in
    luminance-chrominance spaces separates live faces from recaptured ones much better than grey-scale texture.
    Wen, Han and Jain (2015) used image-distortion features (specular reflection, blur, colour moments).

    Deep networks replaced these features from about 2017. Liu, Jourabloo and Liu (2018) showed that binary
    supervision alone over-fits and proposed auxiliary supervision with pseudo-depth maps and remote
    photoplethysmography (rPPG) signals; Jourabloo, Liu and Liu (2018) modelled the spoof as additive noise to be
    removed ("face de-spoofing"); George and Marcel (2019) supervised every pixel (DeepPixBiS). Yu et al. (2020)
    introduced central difference convolution, which aggregates both intensity and gradient information, and
    searched a backbone for it (CDCN and CDCN++). Fig. 2.2 places these families in context; Table 2.1 lists the
    results on the four OULU-NPU protocols reported by Yu et al. (2020), where protocol 4 – unseen lighting, unseen
    attack instrument and unseen camera together – is the hardest.
    """)
    R.figure(f("fas_taxonomy.png"), "Families of Face Presentation Attack Detection Methods", width=5.6)
    R.table("ACER (%) on the Four OULU-NPU Protocols as Reported by Yu et al. (2020)",
            ["Method", "Protocol 1", "Protocol 2", "Protocol 3", "Protocol 4"],
            [["GRADIANT", "6.9", "2.5", "3.8 ± 2.4", "10.0 ± 5.0"],
             ["STASN", "1.9", "2.2", "2.8 ± 1.6", "7.5 ± 4.7"],
             ["Auxiliary (Liu et al., 2018)", "1.6", "2.7", "2.9 ± 1.5", "9.5 ± 6.0"],
             ["Face de-spoofing (Jourabloo et al., 2018)", "1.5", "4.3", "3.6 ± 1.6", "5.6 ± 5.7"],
             ["FAS-TD (Wang et al., 2018)", "1.3", "1.9", "5.9 ± 1.0", "9.2 ± 3.4"],
             ["DeepPixBiS (George & Marcel, 2019)", "0.4", "6.0", "11.1 ± 9.4", "25.0 ± 12.7"],
             ["CDCN (Yu et al., 2020)", "1.0", "1.5", "2.3 ± 1.4", "6.9 ± 2.9"],
             ["CDCN++ (Yu et al., 2020)", "0.2", "1.3", "1.8 ± 0.7", "5.0 ± 2.9"]],
            widths=[2.4, 0.8, 0.8, 0.9, 0.9], align=["l", "c", "c", "c", "c"])
    R.paras("""
    Intra-dataset numbers such as these are near zero for the best methods, but they hide the central
    difficulty of the field: generalisation. When a model is trained on one dataset and tested on another, error
    rates rise by an order of magnitude. Table 2.2 shows the cross-dataset half total error rates (HTER) between
    CASIA-FASD and Replay-Attack reported by Yu et al. (2020); even CDCN++, with 0.2 % ACER on OULU-NPU protocol 1,
    has 29.8 % HTER when trained on Replay-Attack and tested on CASIA-FASD. Jia et al. (2020) attacked this problem
    with single-side domain generalisation (SSDG): real faces from all source domains are pulled together while
    spoof faces of different domains are allowed to stay apart. Their leave-one-dataset-out results are in
    Table 2.3. For our project the lesson was direct: a model trained on a public dataset could not be trusted on
    our laptop webcam until it was retrained and calibrated on data from that camera, and even then its
    behaviour on new people had to be measured rather than assumed.
    """)
    R.table("Cross-Dataset HTER (%) Between CASIA-FASD and Replay-Attack (Yu et al., 2020)",
            ["Method", "Train CASIA → test Replay", "Train Replay → test CASIA"],
            [["Motion-Mag", "50.1", "47.0"], ["LBP-TOP", "49.7", "60.6"], ["LBP", "47.0", "39.6"],
             ["Spectral cubes", "34.4", "50.0"], ["Colour texture", "30.3", "37.7"], ["STASN", "31.5", "30.9"],
             ["Face de-spoofing", "28.5", "41.1"], ["Auxiliary", "27.6", "28.4"], ["FAS-TD", "17.5", "24.0"],
             ["CDCN", "15.5", "32.6"], ["CDCN++", "6.5", "29.8"]],
            widths=[2.2, 1.8, 1.8], align=["l", "c", "c"])
    R.table("Leave-One-Dataset-Out HTER / AUC (%) Reported by Jia et al. (2020)",
            ["Method", "O&C&I → M", "O&M&I → C", "O&C&M → I", "I&C&M → O"],
            [["MS-LBP", "29.76 / 78.50", "54.28 / 44.98", "50.30 / 51.64", "50.29 / 49.31"],
             ["Binary CNN", "29.25 / 82.87", "34.88 / 71.94", "34.47 / 65.88", "29.61 / 77.54"],
             ["IDA", "66.67 / 27.86", "55.17 / 39.05", "28.35 / 78.25", "54.20 / 44.59"],
             ["Colour texture", "28.09 / 78.47", "30.58 / 76.89", "40.40 / 62.78", "63.59 / 32.71"],
             ["LBP-TOP", "36.90 / 70.80", "42.60 / 61.05", "49.45 / 49.54", "53.15 / 44.09"],
             ["Auxiliary (depth)", "22.72 / 85.88", "33.52 / 73.15", "29.14 / 71.69", "30.17 / 77.61"],
             ["MADDG", "17.69 / 88.06", "24.50 / 84.51", "22.19 / 84.99", "27.89 / 80.02"],
             ["SSDG-M", "16.67 / 90.47", "23.11 / 85.45", "18.21 / 94.61", "25.17 / 81.83"],
             ["SSDG-R", "7.38 / 97.17", "10.44 / 95.94", "11.71 / 96.59", "15.61 / 91.54"]],
            widths=[1.5, 1.1, 1.1, 1.1, 1.1], align=["l", "c", "c", "c", "c"], size=9)
    R.p("O = OULU-NPU, C = CASIA-FASD, I = Idiap Replay-Attack, M = MSU-MFSD; the three datasets left of the "
        "arrow are used for training and the fourth for testing.", indent=False, size=10, italic=True)

    R.h3("Datasets for face anti-spoofing")
    R.paras("""
    Table 2.4 lists the datasets most often used in the works above and the one used in this project. The
    classic datasets are small – tens of subjects, recorded in a laboratory – which partly explains the
    cross-dataset gap. LCC-FASD (Timoshenko et al., 2019) was assembled from publicly available videos and
    therefore contains many devices, faces and lighting conditions; we used its development subset because it is
    the dataset the teammates' original model had been trained on, and we added our own webcam recordings.
    The open-source light-weight anti-spoofing repository by Prokofiev publishes reference results on LCC-FASD
    (MobileNetV3-large: AUC 0.921, EER 16.13 %, ACER 16.33 %; AENet: AUC 0.868, EER 20.91 %), which we use as a
    point of comparison in Chapter 7, with the caveat that its training protocol is not stated.
    """)
    R.table("Public Face Anti-Spoofing Datasets",
            ["Dataset", "Year", "Subjects", "Size", "Attacks", "Notes"],
            [["CASIA-FASD (Zhang et al.)", "2012", "50", "600 videos", "print, cut photo, replay", "3 image qualities"],
             ["Replay-Attack (Chingovska et al.)", "2012", "50", "1,300 videos", "print, mobile, tablet replay",
              "controlled / adverse light"],
             ["MSU-MFSD (Wen et al.)", "2015", "35", "280 videos", "print, replay", "laptop and phone cameras"],
             ["OULU-NPU (Boulkenafet et al.)", "2017", "55", "4,950 videos", "print, display replay",
              "6 phones, 4 protocols"],
             ["SiW-M (Liu et al.)", "2019", "493", "1,630 videos", "13 types incl. masks, makeup", "unknown-attack test"],
             ["CelebA-Spoof (Zhang et al.)", "2020", "10,177", "625,537 images", "10 spoof types", "rich annotations"],
             ["LCC-FASD (Timoshenko et al.)", "2019", "crowd-sourced", "dev subset: 416 real, 2,590 spoof crops",
              "replay, print", "used in this project"]],
            widths=[1.6, 0.45, 0.75, 1.2, 1.2, 1.1], size=9)

    R.h3("Active liveness and challenge-response")
    R.paras("""
    Active methods exploit the fact that a static artefact cannot move on request. Pan et al. (2007) detected
    spontaneous eye blinks with a conditional random field and showed that this defeats photo attacks on a
    generic webcam. Kollreider et al. (2007) analysed lip movement while the user read out random digits, so
    that the response could not be prepared in advance. Soukupová and Čech (2016) reduced blink detection to the
    eye aspect ratio computed from six landmarks per eye, which runs in real time on any face-landmark detector.
    The landmark detectors themselves have become very fast and dense: the face mesh of Kartynnik et al. (2019),
    the basis of MediaPipe, estimates 468 three-dimensional points at 100–1,000 frames per second on mobile GPUs,
    and the current MediaPipe Face Landmarker adds iris points (478 in total), 52 facial blendshape scores and a
    head transformation matrix. We use these blendshapes and the matrix directly.

    The weakness of challenge-response is equally well known: a replayed video passes any challenge whose
    action appears in the video (people blink naturally), and a photo can be tilted to imitate a head turn. Our
    measurements in Section 7.4 reproduce both effects, which is why the system combines active and passive
    checks and randomises two distinct challenges per attempt. A further weakness – that the challenges and the
    passive check may see different presentations – is not usually discussed; we found it in our own system and
    address it with the continuity mechanism of Section 4.1.5.
    """)
    R.h3("Face recognition")
    R.paras("""
    Modern face recognition maps an aligned face to an embedding in which the cosine similarity of two faces
    reflects identity. Deng et al. (2019) proposed ArcFace, an additive angular margin added to the angle between
    a feature and its class centre during training, which produces more discriminative embeddings than the
    softmax, SphereFace and CosFace losses (Table 2.5). The InsightFace project distributes ArcFace models with a
    RetinaFace detector (Deng et al., 2020); we use its ResNet-50 model trained on WebFace600K, a subset of the
    WebFace260M collection (Zhu et al., 2021). The numbers in Table 2.5 are for the paper's ResNet-100 model
    trained on MS1M and are quoted as the method's reference performance, not as the performance of our model.
    """)
    R.table("Verification Accuracy (%) of Margin Losses Reported by Deng et al. (2019)",
            ["Loss (LResNet100E-IR, MS1M)", "LFW", "CFP-FP", "AgeDB-30"],
            [["Softmax", "99.70", "91.4", "95.56"], ["SphereFace", "99.76", "93.7", "97.56"],
             ["CosineFace (m = 0.35)", "99.80", "94.4", "97.91"], ["ArcFace (m = 0.4)", "99.80", "94.5", "98.0"],
             ["ArcFace (m = 0.5)", "99.83", "94.04", "98.08"]],
            widths=[2.4, 1.0, 1.0, 1.0], align=["l", "c", "c", "c"])

    R.h3("Biometric template protection")
    R.paras("""
    Ratha, Connell and Bolle (2001) introduced *cancelable biometrics*: instead of the biometric itself, the
    system stores the result of a repeatable, non-invertible, key-dependent transform, so that a compromised
    template can be revoked by changing the key. ISO/IEC 24745 (2022) formalises the requirements as
    irreversibility, unlinkability (templates of the same person under different keys cannot be linked) and
    renewability. BioHashing (Teoh, Ngo and Goh, 2004) projects the feature vector on token-derived random
    orthonormal vectors and binarises the result; the original papers reported equal error rates near zero, but
    later analyses showed that this relied on the token never being stolen – with a stolen token, accuracy is no
    better than that of the unprotected biometric (Kong et al., 2006). Patel, Ratha and Chellappa (2015) review
    the family of cancelable transforms. Our template uses the same idea of a key-derived orthonormal projection,
    with the key schedule driven by a logistic map, and – heeding the BioHashing critique – we report its
    accuracy in the stolen-key setting, where the matcher knows the key, rather than claiming an improvement in
    recognition.
    """)
    R.h3("One-time passwords and transaction authentication")
    R.paras("""
    The HMAC-based one-time password (HOTP, RFC 4226) computes HMAC-SHA1 of a counter under a shared key and
    reduces it to six digits by *dynamic truncation*; TOTP (RFC 6238) replaces the counter by the number of
    30-second steps since the Unix epoch. Both are deliberately simple and well analysed. Our second factor keeps
    their structure – shared secret, time step, dynamic truncation, verification window – but derives the code
    from a deterministic random walk on a public small-world graph (Watts and Strogatz, 1998), as proposed at
    Review 1. Two points from the literature shaped the final design. First, codes should authorise *what* is
    being done, not only *who* is doing it: the dynamic-linking requirement of the EU payment regulation makes the
    code specific to amount and payee. Second, any non-standard pseudo-random construction must be validated
    empirically for uniformity and must not weaken the underlying keyed primitive; we therefore seed the walk with
    HMAC-SHA256 and hash the whole path, and we test the output distribution (Section 7.6).
    """)
    R.h3("Explainability in presentation attack detection")
    R.paras("""
    Grad-CAM (Selvaraju et al., 2017) weights the feature maps of a convolutional layer by the gradient of the
    class score and produces a coarse map of the image regions that drove the decision. Sequeira et al. (2021)
    applied such interpretability tools to face PAD and argued that error rates alone do not show whether a model
    relies on meaningful cues; Pan, Hoque and Deravi (2022) combined attention maps with short verbal explanations.
    The survey of Yu et al. (2023) lists interpretability as an open problem of deep PAD. In our project the
    explanations proved their value in a practical way: Grad-CAM maps and the high-frequency energy feature showed
    that an early model had learned "blurry means spoof", which explained why backlit real faces were rejected
    and led to the retraining described in Section 4.1.6.
    """)
    R.h3("Summary of the surveyed work")
    R.table("Summary of Surveyed Works and Their Relation to This Project",
            ["Work", "Approach", "Reported result (source)", "Limitation / relevance"],
            [["Li et al. (2004)", "Fourier high-frequency ratio", "Photo vs live separation on own data",
              "Fails on sharp photos; we use HF energy as an explanation feature"],
             ["Määttä et al. (2011)", "Multi-scale LBP micro-texture", "Single-image PAD", "Handcrafted; poor cross-dataset"],
             ["Boulkenafet et al. (2016)", "Colour texture (HSV, YCbCr LBP)", "HTER 30.3 / 37.7 % cross C↔I (Yu et al.)",
              "Colour cues help; still dataset-bound"],
             ["Wen et al. (2015)", "Image distortion analysis", "AUC 27.9–78.3 % leave-one-out (Jia et al.)",
              "Sensitive to camera and lighting"],
             ["Liu et al. (2018)", "CNN-RNN, depth + rPPG supervision", "ACER 1.6 % OULU P1 (Yu et al.)",
              "Needs auxiliary labels"],
             ["Jourabloo et al. (2018)", "Spoof-noise modelling", "ACER 1.5 % OULU P1", "Complex generator"],
             ["George & Marcel (2019)", "Pixel-wise binary supervision", "ACER 0.4 % P1, 25.0 % P4", "Large P4 variance"],
             ["Yu et al. (2020)", "Central difference convolution (CDCN++)", "ACER 0.2 % P1; HTER 6.5 / 29.8 % cross",
              "Generalisation still limited"],
             ["Jia et al. (2020)", "Single-side domain generalisation", "HTER 7.38–15.61 % leave-one-out",
              "Needs several source domains"],
             ["Timoshenko et al. (2019)", "LCC-FASD dataset", "Crowd-sourced, diverse devices", "Dataset used here"],
             ["Prokofiev (repository)", "MobileNetV3 on LCC-FASD", "AUC 0.921, EER 16.13 %", "Not peer reviewed"],
             ["Pan et al. (2007)", "Spontaneous blink (CRF)", "Defeats photo attacks", "Fooled by video replay"],
             ["Kollreider et al. (2007)", "Lip motion while reading digits", "Real-time challenge-response",
              "Needs speech prompt"],
             ["Soukupová & Čech (2016)", "Eye aspect ratio from landmarks", "Real-time blink detection",
              "Basis of our blink signal (logged)"],
             ["Kartynnik et al. (2019)", "468-point face mesh", "100–1,000+ FPS on mobile GPUs",
              "Landmarker used for liveness"],
             ["Deng et al. (2019)", "ArcFace additive angular margin", "LFW 99.83 %, AgeDB-30 98.08 %",
              "Our recogniser (ResNet-50 variant)"],
             ["Deng et al. (2020)", "RetinaFace single-shot detector", "Face + 5 landmarks", "Our detector / aligner"],
             ["Ratha et al. (2001)", "Cancelable biometrics", "Revocable non-invertible transforms", "Template concept"],
             ["Teoh et al. (2004)", "BioHashing", "Near-zero EER claimed", "Fails if token stolen (Kong et al., 2006)"],
             ["Selvaraju et al. (2017)", "Grad-CAM", "Class-discriminative saliency", "Used on both branches"],
             ["Sequeira et al. (2021)", "Interpretability of PAD", "Grad-CAM + error rates", "Motivates our XAI panel"],
             ["M'Raihi et al. (2005, 2011)", "HOTP / TOTP", "Standard OTP", "Structure reused by walk-OTP"],
             ["EU RTS 2018/389", "Dynamic linking", "Code specific to amount and payee", "Implemented via context hash"],
             ["Watts & Strogatz (1998)", "Small-world graphs", "Short paths, rewired lattice", "Graph of the walk"]],
            widths=[1.35, 1.55, 1.55, 1.55], size=8.5)

    R.h2("Research Gaps")
    R.p("From the survey and from our early experiments we identified the following gaps, which this project "
        "addresses within its scope:")
    R.numbered([
        "**Evaluation by component combination.** Papers usually report a single PAD model or a single liveness "
        "method. There is little published evidence, on the same attempts, of how face recognition, active liveness "
        "and passive anti-spoofing perform alone and in every combination against the same set of attacks.",
        "**Consistency between active and passive checks.** Systems that run an active challenge and a passive "
        "classifier rarely guarantee that both observed the same presentation. We show that, without this "
        "guarantee, a swap attack passes both.",
        "**Deployment-camera generalisation.** Public datasets do not represent a particular laptop webcam with "
        "back-light and low resolution; calibration on the deployment camera and evaluation on unseen people are "
        "seldom reported in student or prototype systems.",
        "**Transaction binding of biometric step-up.** Biometric checks typically authenticate a session, not a "
        "particular payment; combining them with a dynamically linked second factor is uncommon in academic "
        "prototypes.",
        "**Validated non-standard OTP constructions.** Graph- and chaos-based code generators are proposed in the "
        "literature, but their output distributions are rarely tested; our own first version shows why this matters.",
    ])

    R.h2("Goals and Measurable Objectives")
    g = M["goals"]
    R.p("Table 2.6 turns the objectives of Section 1.1 into measurable goals. The last column gives the result "
        "achieved, taken from Chapter 7.")
    R.table("Measurable Goals and Results Achieved",
            ["Goal", "Measure", "Target", "Achieved"],
            [["Recognise the account holder", "FAR / FRR at τ_{A} = 0.40 (protected template)", "FAR ≤ 0.1 %, FRR ≤ 5 %",
              g["face"]],
             ["Block photo and replay attacks", "Attack acceptance of A+L+F", "≤ 5 %", g["attacks"]],
             ["Accept the genuine user", "Genuine acceptance of A+L+F (first attempt)", "≥ 70 %", g["genuine"]],
             ["Block the swap attack", "Recorded attack and spliced replays", "blocked", g["swap"]],
             ["Uniform second-factor codes", "Distinct codes from 20,000 secrets; χ² p-value", "≈ ideal; p > 0.05",
              g["otp"]],
             ["Revocable template", "Old template vs probe under a new key", "0 accepted", g["revoke"]],
             ["Responsive verification", "Presence verification compute time (CPU)", "≤ 6 s", g["latency"]],
             ["Explain every decision", "Reasons + Grad-CAM + timeline on every attempt", "always", "always shown"],
             ["Regression safety", "Automated tests passing", "all", "105 / 105"]],
            widths=[1.6, 2.0, 1.1, 1.3], size=9)

    R.h2("Deviations from the Review-1 Plan")
    R.paras("""
    Two elements of the registered title were implemented differently from the Review-1 plan, and we state this
    plainly. First, Review 1 proposed combining the face embedding with fractal-dimension features before
    protection. Our measurements showed that the fractal dimension of face crops separates real from spoof faces
    no better than chance (AUC 0.52 on the LCC-FASD test split), and it carries no identity information; adding it
    to the template would only add noise. Fractal geometry therefore appears in the final system in two other
    roles: as an explanation feature (differential box counting, Section 3.4.4) and through the chaotic logistic
    map, a classic generator of fractal structure, that drives the template's key schedule. Second, Review 1
    proposed the random walk as a replacement for HMAC. We kept the random walk as the code generator but seed it
    with HMAC-SHA256, because a walk alone provides no keyed security guarantee; the walk then adds a
    transaction-bound, verifiable path from which the code is derived. Both choices are discussed with their
    alternatives in Section 4.4.
    """)
