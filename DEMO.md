# VaultTrust — demo runbook

## 1. Setup (once)

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

* Laptop app: <http://localhost:8501>
* Phone authenticator is served automatically on port **8600**.

### Phone on a hotspot
1. Connect **both** the laptop and the phone to the same hotspot (a third phone's hotspot, or
   Windows *Settings → Network → Mobile hotspot* on the laptop itself).
2. In the app sidebar → **Phone network**, pick the laptop address on that network
   (usually `192.168.x.x` / `10.x.x.x`).
3. First time only: when Windows asks, **allow Python on private and public networks**. If the phone
   cannot open `http://<laptop-ip>:8600`, that firewall prompt is the reason.
4. Phone clock must be automatic (codes change every 30 s; ±30 s drift is tolerated).

No phone? Every QR screen has **"Open the authenticator on this laptop"** — same code, computed in a
separate browser tab.

## 2. Retraining with the team's webcam data

```bash
# put the videos in data/raw_videos/  (names: <person>_<real|phone|screen|print>_<n>.mp4)
python tools/extract_frames.py
python -u training/train_fas_v2.py --ablation        # ~1 h on CPU; fused model alone: drop --ablation
```

Writes `models/fas_v2.pth`, `models/fas_calibration.json` (threshold) and `reports/metrics.json`
(shown in **Model Lab**). Restart Streamlit afterwards so the new model is loaded.

## 3. Demo script (~8 min)

| # | Do | Say |
|---|----|-----|
| 1 | Home page | "Passwords and SMS OTPs fail to session hijacking and SIM swaps. Large transfers need the person, live, plus their phone." |
| 2 | **Open account** → email code → face enrolment | "Two random challenges, judged against *your* neutral pose. Meanwhile 10 clean frames go to the spatial+frequency CNN." Open **Why?** → Grad-CAM, branch evidence, frequency profile, liveness timeline. |
| 3 | Pair phone (scan QR) → type code | "The secret K travels once in the QR fragment and is never sent again. The phone computes codes offline." Point at the walk animation on the phone. |
| 4 | Send $250 | Instant — below the step-up limit. |
| 5 | Send $5,000 | Step-up: face again → evidence card → phone shows **amount + payee** → code → done. "The code is HMAC(K, time, *this transaction*) — it is useless for any other amount or payee." |
| 6 | **Attack 1:** step-up with a photo/video of yourself on a phone | Blocked, with reasons (anti-spoofing score, branch evidence, HF energy). Show it in the **Security log**. |
| 7 | **Attack 2:** a teammate tries the step-up on your account | Liveness passes, **face match fails** in the protected-template domain. |
| 8 | **Attack 3:** type a code from the Model Lab for amount + $0.01, or reuse an accepted code | Rejected (dynamic linking / replay protection). |
| 9 | **Model Lab** | Metrics table (APCER/BPCER/ACER, ablation), OTP code-space fix (768 → ~20k distinct codes), template demo (98% genuine accepted, 0% impostors, re-keyed cosine ≈ 0). |

## 4. Questions examiners are likely to ask

**Isn't the random walk pointless if you use HMAC?** Security of the code rests on HMAC-SHA256 (a
standard PRF); we do not claim the walk adds cryptographic strength. The walk is the generation
structure: it is deterministic, reproducible on any platform (Python ↔ JS test vectors), and
visualisable. v1's walk-only design actually *lost* entropy (only 768 distinct codes from 20,000 secrets),
which we found and fixed by hashing the full path.

**Why did your anti-spoofing model give low confidence before? (the v1 → v4 story — Model Lab table 1)**
* **v1** (original): classifier head on frozen ImageNet features, 416 real images, no train/test split. It
  memorised LCC-FASD (AUC 1.000 on images it had trained on) and on our webcam **accepted 71–84% of the
  teammate's phone-replay frames**.
* **v2**: subject-wise split, fine-tuned backbones → AUC 0.970 on unseen LCC subjects, blocks every replay,
  but **rejected real webcam faces in backlight**. Grad-CAM + the high-frequency signal showed why: LCC's
  real faces are sharp and its spoofs blurry, so the model learned "blurry = spoof". *The explanation
  exposed a dataset bias.*
* **v3**: + teammate's webcam videos, augmentation that degrades real and spoof equally (blur, downscale,
  backlight, noise), threshold calibrated on webcam validation clips. Tested on a person it never saw:
  AUC 0.925, all replays blocked.
* **v4** (deployed): same recipe on all webcam data. Every live clip ≥ 0.88, every attack ≤ 0.06; a later
  attempt not in training scored 0.94. Cost: LCC AUC 0.903 (vs 0.970) — the model now favours the
  deployment camera. **Limitation:** 2 webcam people; more people/devices is the remaining 20%.

**Does the frequency branch help?** Our ablation says: not on LCC-FASD. Test AUC (12 unseen subjects):
spatial-only 0.986, spatial + frequency 0.970, frequency-only 0.736. LCC attacks are mostly blurry
re-captures that RGB texture already catches. The frequency branch is aimed at screen moiré and print
dots, which the team's webcam phone/screen recordings contain, so the ablation will be rerun on that data.
We report this rather than claim the fusion helps.

**Does the fractal dimension help?** Honestly, only a little: on LCC-FASD, FD alone is a weak
classifier (see the Model Lab table). We keep it as an interpretable texture signal in the explanation,
not in the decision. The frequency branch and HF-energy carry more signal.

**Is the template really non-invertible?** It maps 512 → 256 dimensions, so infinitely many
embeddings give the same template; an attacker with template **and** key can only recover the
projection onto a 256-D subspace. Key and secret are encrypted at rest with a separate master key. A
production system would keep that key in an HSM.

**Why liveness *and* a CNN?** Active challenges defeat photos and pre-recorded video (the challenge
order is random); the CNN catches live replays on screens and masks that can perform the action.
Each covers the other's blind spot — and the decision fusion requires both.

**Can someone show a photo for the face check and then step in for the actions?** That attack worked
on 10 Oct during our own testing: a phone was held up during calibration (the frames that are scored),
then a live person did the challenges. We fixed it with *continuity*: the face is tracked from the first
frame to the last. A gap over 0.7 s or a sudden jump in position or size restarts calibration (and
discards its frames) or, during the challenges, fails the attempt. Frames are also sampled during the
challenges: ArcFace must find the same person as at calibration (similarity ≥ 0.35), and the neutral
ones must pass anti-spoofing too. Replaying the screen recording of the original attack through the new
code fails it at the exact moment the phone is taken away (a regression test in `tests/test_e2e.py`).

## 5. If something breaks on the day
* Camera does not start → press **START** under the video; check the browser camera permission.
* Phone cannot reach the laptop → use the laptop authenticator link on the QR screen.
* Email not delivered → the app shows the code as a demo fallback.
* Anti-spoofing rejects you in bad light → face a window or lamp; the per-frame chart in **Why?**
  shows which frames scored low.
