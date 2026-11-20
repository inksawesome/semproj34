"""Chapter 5 Schedule, Tasks and Milestones; Chapter 6 Project Demonstration."""

import os

FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")


def f(name):
    return os.path.join(FIG, name)


def chapter5(R, M):
    R.chapter("Schedule, Tasks and Milestones")
    R.p("The project ran from 6 July to 3 November 2026. Fig. 5.1 shows the schedule as executed. The first six "
        "weeks went into studying the problem, the literature and the design presented at Review 1 on 19 August, "
        "together with the first random-walk OTP engine. The anti-spoofing network and the active-liveness and "
        "explainability components were developed in parallel in August and September, and integrated into the "
        "banking application by early October. The week of 6–12 October was the most intensive: end-to-end testing "
        "with real people exposed the defects listed in Table 5.4, which were fixed, retrained and covered by tests. "
        "The final weeks were spent on the evaluation reported in Chapter 7 and on this report.")
    R.figure(f("gantt.png"), "Project Schedule (Gantt Chart)", width=5.9)
    R.h2("Tasks and Team Roles")
    R.table("Task Allocation", ["Member", "Primary responsibilities", "Shared work"],
            [["Magizharasan K (23BIT0319)", "Spatial-frequency anti-spoofing network (component 1), passive liveness "
              "(component 2), LCC-FASD data preparation", "Design, testing, evaluation, report"],
             ["Nilay Kant Shahi (23BIT0334)", "Active liveness (component 3), explainable AI (component 4), "
              "random-walk OTP, integration, continuity fix, retraining pipeline", "Design, testing, evaluation, report"],
             ["Rwitankar Giri (23BIT0335)", "Anti-spoofing network (components 1–2), webcam data collection "
              "(real and replay videos), face-capture pipeline", "Design, testing, evaluation, report"]],
            widths=[1.6, 2.8, 1.4], size=9.5)
    R.h2("Milestones")
    R.table("Milestones", ["Date", "Milestone", "Evidence"],
            [["19 Aug 2026", "Review 1: problem, literature, design, working OTP engine", "Review-1 report"],
             ["19 Sep 2026", "Active liveness and explainability implemented", "Repository commit"],
             ["6 Oct 2026", "Integrated application with new user interface", "Repository commit"],
             ["8–9 Oct 2026", "OTP v2, phone authenticator, face recognition at sign-in, retrained model v3/v4",
              "Test suite, field log"],
             ["10 Oct 2026", "Swap attack discovered (screen recording)", "Recording, audit log"],
             ["11 Oct 2026", "Continuity fix, model v5, 105 tests passing", "Test run"],
             ["13–24 Oct 2026", "Evaluation suite, ablation and comparative study", "reports/eval"],
             ["3 Nov 2026", "Final report and presentation", "This document"]],
            widths=[1.1, 3.2, 1.5], size=9.5)
    R.h2("Development Log: Defects Found and Fixed")
    R.p("Table 5.4 is the chronological record of the significant problems found by testing the integrated system "
        "with real users and attacks, and of their fixes. It is included because most of the design decisions of "
        "Chapter 4 originate here.")
    R.table("Defects and Attacks Found During Development, With Their Fixes",
            ["Date", "Finding", "Fix"],
            [["8 Oct", "Grad-CAM targeted the average-pool layer (flat 1×1 map) with wrong inputs", "layer4 hooks on the exact tensors classified"],
             ["8 Oct", "Original anti-spoofing model memorised LCC-FASD; low confidence on the webcam", "Retraining pipeline, subject split, fine-tuning"],
             ["8 Oct", "Anti-spoofing scored a frame captured mid-challenge with overlay text", "10 clean calibration frames, median"],
             ["8 Oct", "Face recognition never ran after sign-up; sign-in was e-mail only", "ArcFace at sign-in and step-up"],
             ["8 Oct", "OTP shown on the same screen; Python and JS codes differed; 768-code space", "Phone authenticator, OTP v2, test vectors"],
             ["8 Oct", "Smile metric inverted, pitch uncalibrated, single challenge", "Blendshapes + pose matrix, baseline-relative, 2 challenges"],
             ["8 Oct", "Lock deadlock in the camera thread (no overlay)", "Re-entrant lock"],
             ["8 Oct", "Verification repeated 2–4 times per attempt (reruns)", "Background verification job"],
             ["8 Oct", "Intermittent native crash on camera teardown", "Single MediaPipe lock; crash log (no recurrence)"],
             ["8 Oct", "'Blurry = spoof' bias: backlit real faces rejected (seen in the explanation)", "Webcam data + quality augmentation (v3/v4)"],
             ["9 Oct", "Expired OTP accepted for 30 s after the step changed", "10-s grace window + 'expired' message"],
             ["9 Oct", "No way to switch account", "Switch / back buttons on every page"],
             ["9 Oct", "Phone 'not paired' after a network change; no re-pairing", "Re-pair flow, pairing-address warning"],
             ["9 Oct", "QR image sometimes missing (media race)", "Inline data-URI QR"],
             ["9 Oct", "Browser back button left the site", "Page URLs with st.navigation"],
             ["9 Oct", "Deleted account crashed the dashboard", "Redirect home"],
             ["9 Oct", "Misleading '71 % attacks accepted' (LCC numbers at webcam threshold)", "Webcam view by default; LCC view labelled"],
             ["10 Oct", "Camera feed laggy", "Fragment polling, 15 fps, banner-only overlay, 2 cores kept free, warm-up"],
             ["10 Oct", "Swap attack succeeded: phone in calibration, live person in challenges (v4 scored the phone 0.72)",
              "Continuity (Section 4.1.5) + model v5"],
             ["11 Oct", "Unused language-model wrapper with an API key in the environment file (never committed)", "Archived; key to be revoked"]],
            widths=[0.55, 3.0, 2.25], size=8.5)


def chapter6(R, M):
    R.chapter("Project Demonstration")
    R.p("This chapter walks through the running system as it is demonstrated: installation and start-up, the "
        "normal user journey, the attacks we demonstrate, the Model Lab page and the automated tests. The "
        "screenshots are taken from the screen recording of 10 October 2026; faces are pixelated and e-mail "
        "addresses blurred.")
    R.h2("Setting Up and Running")
    R.p("The system needs Python 3.14 with the packages of Table 3.4, the model files in `models/`, and the "
        "InsightFace buffalo_l models (downloaded on first use). It is started with one command; the phone page is "
        "served automatically on port 8600, and the laptop and phone must be on the same network.")
    R.code("""
pip install -r requirements.txt
python -m streamlit run app.py              # http://localhost:8501 ; phone page on port 8600

# optional environment variables
VT_SAVE_CAPTURES=0    # do not keep face crops of sign-in attempts
VT_DB_PATH=...        # use another database file
AUTH_HOST / AUTH_PORT # address shown to the phone

# tests (temporary database; no e-mail is sent)
python -m pytest tests semprojOTP/otp_system/tests -q -p no:warnings
""")
    R.p("At start-up a background thread loads and warms the three models (ArcFace's first call alone takes "
        "about 3.7 s), so that the first user does not wait for them.")
    R.h2("User Journey")
    R.h3("Opening an account and signing in")
    R.p("Opening an account verifies the e-mail address with a one-time code, enrols the face (with the same liveness "
        "and anti-spoofing checks as sign-in), creates the protected template, and pairs the phone by QR; the user "
        "confirms the first code from the phone before the account is created with a starting balance. Signing in "
        "asks only for the e-mail address and a presence check. Fig. 6.1 shows the camera panel during the second "
        "challenge: the banner states the challenge and the time left, and a panel beside the video (not shown) lists "
        "the steps and tips. Fig. 6.2 shows the evidence card after a successful sign-in: two challenges passed, an "
        "anti-spoofing score of 0.83 and a template match of 0.49, each with its threshold.")
    R.figure(f("ui_signin_liveness.png"), "Sign-In: Active Liveness Challenge (Face Pixelated)", width=5.0)
    R.figure(f("ui_signin_result.png"), "Sign-In: Evidence Card After a Successful Check", width=5.4)
    R.h3("Accounts and transfers")
    R.p("The Accounts page (Fig. 6.3) shows the balance, the step-up limit, the state of the authenticator and the "
        "transaction list with a security-log tab. A transfer below $1,000 settles immediately. A transfer at or "
        "above the limit opens the verification page (Fig. 6.4): the amount, payee and reference are fixed at the top, "
        "and step 1 is a fresh presence check.")
    R.figure(f("ui_accounts.png"), "Accounts Page (E-mail Addresses Blurred)", width=5.4)
    R.figure(f("ui_verify_challenge.png"), "Step-Up Verification, Step 1: Presence Check", width=5.4)
    R.p("When the presence check passes, step 2 shows the transfer QR code (Fig. 6.5). The phone page opened from the "
        "QR shows the transfer and, on approval, the code; if the phone has no key for the laptop's current address it "
        "explains why and how to re-pair (Fig. 6.6). After the code is accepted the transfer is settled and confirmed "
        "(Fig. 6.7).")
    R.figure(f("ui_verify_qr.png"), "Step-Up Verification, Step 2: Transfer QR for the Phone", width=5.4)
    R.figure(f("ui_phone_page.png"), "Phone Authenticator Explaining a Missing Key After a Network Change", width=3.0)
    R.figure(f("ui_transfer_done.png"), "Transfer Settled After Face and Phone Approval", width=5.0)
    R.h2("Attack Demonstrations")
    R.p("Table 6.1 lists the attacks we demonstrate and the observed outcome. Each is also an automated test, either "
        "on recorded video through the real processor or as a full application workflow.")
    R.table("Demonstrated Attacks and Outcomes",
            ["Attack", "How it is performed", "Outcome", "Stopped by"],
            [["Photo on a phone", "Victim's photo held to the camera", "Rejected", "L (no blink/turn), F"],
             ["Video replay", "Victim's video played on a phone", "Rejected", "L (random challenge), F"],
             ["Video replay, blink-only policy", "Same video, both challenges 'blink'", "Passes L (by design of the test)",
              "F; motivates random challenges"],
             ["Different person", "Another person signs in to the account", "Rejected (similarity ≈ 0.02–0.13)", "A"],
             ["Swap", "Phone during calibration, live person for challenges", "Rejected at 70.05 s of the recording", "Continuity"],
             ["Wrong codes", "Three wrong six-digit codes", "Transfer blocked", "OTP attempt limit"],
             ["Expired code", "Code submitted after its step + 10 s", "Rejected as expired", "Grace window"],
             ["Modified transfer", "Code computed for another amount", "Rejected", "Dynamic linking"],
             ["Enrolment with a replay", "Sign-up using a video", "Rejected", "L, F at enrolment"]],
            widths=[1.3, 1.9, 1.4, 1.2], size=9)
    R.h2("Model Lab")
    R.p("The Model Lab page is meant for examiners. It shows the evaluation report of model versions v1–v5, lets the "
        "evaluator choose the anti-spoofing operating point on the held-out webcam or LCC-FASD scores and see the "
        "resulting APCER and BPCER, switches the anti-spoofing policy between enforce and advisory, and demonstrates "
        "the random-walk OTP (graph, path and code) and the cancelable template (match scores under the right and a "
        "new key).")
    R.h2("Automated Testing")
    R.p("The system is covered by 105 automated tests (Table 6.2), all passing on 11 October 2026 in about 7.5 "
        "minutes on the laptop. The end-to-end tests feed recorded webcam videos through the same "
        "LivenessProcessor.recv() method that the WebRTC stream calls, and drive the whole Streamlit application "
        "with Streamlit's AppTest, so that the workflows of Section 6.2 and the attacks of Table 6.1 are exercised "
        "on real data. The only part not exercised is the browser-to-server WebRTC transport. Tests use a temporary "
        "database, never send e-mail and never save face crops.")
    R.table("Automated Test Inventory",
            ["File", "Tests", "What is covered"],
            [["semprojOTP/otp_system/tests/test_walk_otp.py", "31", "OTP core, graph determinism, FastAPI server "
              "(enrol, verify, replay, rate limit)"],
             ["semprojOTP/otp_system/tests/test_vectors.py", "10", "Python ↔ JavaScript vectors; grace window and expiry"],
             ["tests/test_pipeline.py", "17", "Liveness state machine, real landmarker in a worker thread, continuity "
              "(jump, rescale, gap, dropout tolerance, natural movement, calibration restart, sampling), "
              "genuine / impostor / swap verification"],
             ["tests/test_e2e.py", "39", "OTP; phone page server; face and template; anti-spoofing and explanation; "
              "liveness on real video; database; recorded swap attack; 19 application workflows"],
             ["tests/test_liveness.py, tests/test_explainability.py", "8", "Earlier liveness and explainability modules"]],
            widths=[2.4, 0.5, 2.9], size=9)
    R.p("The nineteen application workflows are: sign-up with enrolment and pairing; sign-in with the face; instant "
        "low-value transfer; high-value transfer with face and phone; video replay blocked by anti-spoofing; replay "
        "failing a random challenge; a different person; wrong codes locking a transfer; enrolment with a replay; the "
        "advisory policy; the security log; dashboard and Model Lab rendering; recovery from a deleted account; "
        "switching accounts; restarting sign-up with another e-mail; expired codes; re-pairing after a network "
        "change in the middle of a transfer; re-pairing from the Accounts page; and a pending transfer surviving "
        "navigation away from the page.")
