"""Front matter: cover, inner title page, declaration, certificate, acknowledgement, executive summary,
contents, lists of figures and tables, abbreviations, symbols and notations."""

from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.shared import Inches, Pt

from docx_engine import _set_font

TITLE = "Design of an Authentication System Using Fractal Geometry with Graph-Based Random-Walk OTP Generation"
SUBTITLE = "VaultTrust: Explainable Face Anti-Spoofing with Transaction-Bound OTP for Step-Up Authentication"
STUDENTS = [("Magizharasan K", "23BIT0319"), ("Nilay Kant Shahi", "23BIT0334"), ("Rwitankar Giri", "23BIT0335")]
GUIDE = "Prof. Mohanraj G"
GUIDE_DESIG = "Assistant Professor Senior Grade 2"
LOGO = None   # set by build_report


def line(R, text, size=12, bold=False, italic=False, space_after=6, align="center", before=0):
    p = R.doc.add_paragraph()
    p.alignment = {"center": WD_ALIGN_PARAGRAPH.CENTER, "left": WD_ALIGN_PARAGRAPH.LEFT,
                   "right": WD_ALIGN_PARAGRAPH.RIGHT, "justify": WD_ALIGN_PARAGRAPH.JUSTIFY}[align]
    p.paragraph_format.first_line_indent = Inches(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    if text:
        R._runs(p, text, size=size, bold=bold or None, italic=italic or None)
    return p


def title_page(R, first):
    line(R, TITLE, 16, bold=True, space_after=8, before=0 if first else 0)
    line(R, SUBTITLE, 13, italic=True, space_after=14)
    line(R, "BITE497J – Project I", 14, bold=True, space_after=18)
    line(R, "Submitted in partial fulfillment of the requirements for the degree of", 12, italic=True, space_after=14)
    line(R, "Bachelor of Technology", 16, bold=True, space_after=4)
    line(R, "in", 12, space_after=4)
    line(R, "Information Technology", 14, bold=True, space_after=18)
    line(R, "by", 12, italic=True, space_after=8)
    for name, reg in STUDENTS:
        line(R, f"{name}  ({reg})", 13, bold=True, space_after=3)
    line(R, "", space_after=8)
    line(R, "Under the guidance of", 12, bold=True, space_after=4)
    line(R, GUIDE, 13, bold=True, space_after=2)
    line(R, f"{GUIDE_DESIG}, SCORE", 11, space_after=18)
    line(R, "School of Computer Science Engineering and Information Systems", 11, bold=True, space_after=2)
    line(R, "VIT, Vellore", 11, bold=True, space_after=12)
    p = line(R, "", space_after=12)
    p.add_run().add_picture(LOGO, width=Inches(2.6))
    line(R, "November, 2026", 12, space_after=0)


def build(R, M):
    # ---------------- cover and inner title page (cover page number hidden: different first page)
    title_page(R, True)
    R.page_break()
    title_page(R, False)

    # ---------------- declaration
    R.heading1("DECLARATION")
    stud = ", ".join(f"{n} ({r})" for n, r in STUDENTS[:-1]) + f" and {STUDENTS[-1][0]} ({STUDENTS[-1][1]})"
    R.p(f"We hereby declare that the BITE497J – Project I thesis entitled “**{TITLE}**” submitted by us, for "
        "the award of the degree of ***Bachelor of Technology in Information Technology, School of Computer Science "
        "Engineering and Information Systems*** to VIT is a record of bonafide work carried out by us under the "
        f"supervision of **{GUIDE}, {GUIDE_DESIG}, SCORE, VIT, Vellore.**", indent=True)
    R.p("We further declare that the work reported in this thesis has not been submitted and will not be "
        "submitted, either in part or in full, for the award of any other degree or diploma in this institute or "
        "any other institute or university.", indent=True)
    line(R, "", space_after=24)
    line(R, "Place: Vellore", align="left")
    line(R, "Date:", align="left", space_after=40)
    for n, r in STUDENTS:
        line(R, f"{n} ({r})", align="right", space_after=30)
    line(R, "Signature of the Candidates", bold=True, align="right")

    # ---------------- certificate
    R.heading1("CERTIFICATE")
    R.p(f"This is to certify that the BITE497J – Project I thesis entitled “**{TITLE}**” submitted by {stud}, "
        "SCORE, VIT, for the award of the degree of ***Bachelor of Technology in Information Technology, School of "
        "Computer Science Engineering and Information Systems***, is a record of bonafide work carried out by them "
        "under my supervision during the period 06.07.2026 to 03.11.2026, as per the VIT code of academic and "
        "research ethics.", indent=True)
    R.p("The contents of this report have not been submitted and will not be submitted either in part or in full, "
        "for the award of any other degree or diploma in this institute or any other institute or university. The "
        "thesis fulfils the requirements and regulations of the University and in my opinion meets the necessary "
        "standards for submission.", indent=True)
    line(R, "", space_after=20)
    line(R, "Place: Vellore", align="left")
    line(R, "Date:", align="left", space_after=36)
    line(R, "Signature of the Guide", bold=True, align="right", space_after=4)
    line(R, f"{GUIDE}, {GUIDE_DESIG}", align="right", space_after=56)
    p = line(R, "", align="left", space_after=56)
    r = p.add_run("Internal Examiner")
    _set_font(r, 12, bold=True)
    r = p.add_run("\t\t\t\t\t\tExternal Examiner")
    _set_font(r, 12, bold=True)
    line(R, "Head of the Department", bold=True, space_after=2)
    line(R, "Department of Information Technology", bold=True)

    # ---------------- acknowledgement
    R.heading1("ACKNOWLEDGEMENT")
    R.p(f"It is our pleasure to express with a deep sense of gratitude to our BITE497J – Project I guide **{GUIDE}, "
        f"{GUIDE_DESIG}**, School of Computer Science Engineering and Information Systems, Vellore Institute of "
        "Technology, Vellore, for the constant guidance, continual encouragement and understanding we received "
        "during this project. Our association with our guide is not confined to academics only; it has been a great "
        "opportunity to work with an intellectual and an expert in the field of **information security and "
        "biometric authentication**.", indent=True)
    R.p("We would like to express our heartfelt gratitude to the Honourable Chancellor **Dr. G Viswanathan**; "
        "respected Vice Presidents **Dr. Sankar Viswanathan** and **Dr. Sekar Viswanathan**; Vice Chancellor "
        "**Dr. V. S. Kanchana Bhaaskaran**; Pro-Vice Chancellor **Dr. Partha Sharathi Mallick**; and Registrar "
        "**Dr. Jayabarathi T**.", indent=True)
    R.p("Our whole-hearted thanks to Dean **Dr. Daphne Lopez**, School of Computer Science Engineering and "
        "Information Systems; Head, Department of Information Technology, **Dr. Arivuselvan K**; Information "
        "Technology Project Coordinator **Dr. Suganya P**; SCORE School Project Coordinator **Dr. Karthikeyan P**; "
        "and all faculty, staff and members working as limbs of our university for their continuous guidance "
        "throughout our course of study in unlimited ways.", indent=True)
    R.p("It is indeed a pleasure to thank our parents and friends who persuaded and encouraged us to take up and "
        "complete this project successfully, and the classmates who volunteered their time in front of the camera "
        "while we tested the system. Last, but not least, we express our gratitude and appreciation to all those "
        "who have helped us directly or indirectly towards the successful completion of the project.", indent=True)
    line(R, "", space_after=18)
    line(R, "Place: Vellore", align="left")
    p = line(R, "Date:", align="left", space_after=4)
    for n, r in STUDENTS:
        line(R, f"{n} ({r})", align="right", space_after=4)

    # ---------------- executive summary (<= 200 words)
    R.heading1("EXECUTIVE SUMMARY")
    s = M["summary_numbers"]
    R.p(
        "Passwords and SMS codes do not prove that the account holder is present when money leaves an account. "
        "VaultTrust is a step-up authentication system for a mock bank: every transfer of $1,000 or more must be "
        "approved, at that moment, by the account holder's live face and paired phone. The face check combines "
        "active liveness (two random challenges with face-continuity tracking), a dual-branch spatial and "
        "frequency-domain anti-spoofing network with Grad-CAM explanations, and ArcFace matching on a cancelable, "
        "chaotic-map-keyed template. The phone computes a random-walk one-time password bound to the amount and "
        f"payee. On held-out data, ArcFace on the protected template reached {s['face_eer']} EER with no false "
        f"accepts in {s['impostor_pairs']} impostor pairs, but alone it accepted {s['face_attack_accept']} of photo "
        f"and replay attacks. The full A+L+F combination reached {s['alf_acc']} accuracy and F1 {s['alf_f1']} "
        f"against {s['alf_attack']} attack acceptance, versus {s['a_acc']} for ArcFace alone. A recorded swap attack "
        "that defeated an earlier version is now blocked, OTP codes are uniform (19,781 distinct in 20,000), and "
        f"verification takes {s['latency']} on a laptop CPU. Generalising anti-spoofing to unseen people remains "
        "the main limitation.", indent=False)

    # ---------------- contents and lists
    R.heading1("CONTENTS")
    R.toc()
    R.heading1("LIST OF FIGURES")
    R.list_of("Figure Caption")
    R.heading1("LIST OF TABLES")
    R.list_of("Table Caption")

    R.heading1("LIST OF ABBREVIATIONS")
    abbr = [("ACER", "Average Classification Error Rate"), ("AES", "Advanced Encryption Standard"),
            ("APCER", "Attack Presentation Classification Error Rate"), ("API", "Application Programming Interface"),
            ("AUC", "Area Under the ROC Curve"), ("BPCER", "Bona fide Presentation Classification Error Rate"),
            ("CDCN", "Central Difference Convolutional Network"), ("CNN", "Convolutional Neural Network"),
            ("CPU", "Central Processing Unit"), ("DBC", "Differential Box Counting"),
            ("DFT", "Discrete Fourier Transform"), ("DPDP", "Digital Personal Data Protection (Act, 2023)"),
            ("EAR", "Eye Aspect Ratio"), ("EER", "Equal Error Rate"), ("FAR", "False Acceptance Rate"),
            ("FAS", "Face Anti-Spoofing"), ("FFT", "Fast Fourier Transform"), ("FN", "False Negative"),
            ("FP", "False Positive"), ("FPS", "Frames Per Second"), ("FRR", "False Rejection Rate"),
            ("FTA", "Failure To Acquire"), ("Grad-CAM", "Gradient-weighted Class Activation Mapping"),
            ("HF", "High Frequency"), ("HMAC", "Hash-based Message Authentication Code"),
            ("HOTP", "HMAC-based One-Time Password (RFC 4226)"), ("HTER", "Half Total Error Rate"),
            ("ISO/IEC", "International Organization for Standardization / International Electrotechnical Commission"),
            ("JS", "JavaScript"), ("LBP", "Local Binary Patterns"),
            ("LCC-FASD", "Large Crowd-Collected Face Anti-Spoofing Dataset"), ("LOPO", "Leave-One-Person-Out"),
            ("MFA", "Multi-Factor Authentication"), ("ONNX", "Open Neural Network Exchange"),
            ("OTP", "One-Time Password"), ("PAD", "Presentation Attack Detection"),
            ("PAI", "Presentation Attack Instrument"), ("PRNG", "Pseudo-Random Number Generator"),
            ("PSD2", "Revised Payment Services Directive (EU)"), ("QR", "Quick Response (code)"),
            ("ResNet", "Residual Network"), ("ROC", "Receiver Operating Characteristic"),
            ("RTS", "Regulatory Technical Standards"), ("SCA", "Strong Customer Authentication"),
            ("SHA", "Secure Hash Algorithm"), ("SQL", "Structured Query Language"),
            ("TAR", "True Acceptance Rate"), ("TN", "True Negative"),
            ("TOTP", "Time-based One-Time Password (RFC 6238)"), ("TP", "True Positive"),
            ("UI", "User Interface"), ("UML", "Unified Modeling Language"),
            ("WebRTC", "Web Real-Time Communication"), ("XAI", "Explainable Artificial Intelligence")]
    _two_col(R, abbr)

    R.heading1("SYMBOLS AND NOTATIONS")
    sym = [("A, L, F", "Face-match, active-liveness and anti-spoofing components"),
           ("e, e′", "512-D L2-normalised ArcFace embeddings (enrolled, probe)"),
           ("t", "256-D protected (cancelable) template"),
           ("W, π", "Key-derived orthonormal projection (256×512) and permutation"),
           ("r, x_{n}", "Logistic-map parameter and state"),
           ("cos(a, b)", "Cosine similarity"),
           ("τ_{A}, τ_{F}, τ_{id}", "Thresholds: face match 0.40, anti-spoofing (calibrated), continuity identity 0.35"),
           ("p_{real}", "Anti-spoofing network output: probability that the face is real"),
           ("K", "Shared OTP secret (32 bytes)"), ("T", "OTP time step ⌊t / 30 s⌋"),
           ("ctx", "Transaction context TX|reference|amount in cents|payee"),
           ("G = (V, E)", "Public 64-node small-world graph used by the walk"),
           ("F(u, v)", "2-D discrete Fourier transform of an image"),
           ("D", "Fractal dimension (differential box counting)"),
           ("α_{k}^{c}, L^{c}", "Grad-CAM channel weights and class activation map for class c"),
           ("θ_{yaw}, θ_{pitch}", "Head rotation angles from the facial transformation matrix"),
           ("Δ", "Change of a liveness signal relative to the user's calibrated baseline"),
           ("m", "Additive angular margin of the ArcFace loss"),
           ("TP, FP, TN, FN", "Confusion-matrix counts (genuine = positive)")]
    _two_col(R, sym)


def _two_col(R, rows):
    from docx.enum.table import WD_TABLE_ALIGNMENT
    tbl = R.doc.add_table(rows=0, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for a, b in rows:
        cells = tbl.add_row().cells
        cells[0].width, cells[1].width = Inches(1.5), Inches(4.2)
        for c, v, bold in ((cells[0], a, True), (cells[1], b, False)):
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            p.paragraph_format.first_line_indent = Inches(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            R._runs(p, v, size=11, bold=bold or None)
