# VaultTrust — Project Record

The single source of truth for the project as built: what it is, how every part works, every number we
measured, every defect we found and fixed, and how to reproduce all of it. Written 13 Oct 2026 from the
development log (6–13 Oct 2026). Later documents (final report, slides) are derived from this file.

---

## 1. Identity

| | |
|---|---|
| Course | BITE497J – Project I, Fall Semester 2026–27, Department of Information Technology, SCORE, VIT Vellore |
| Team | Magizharasan K (23BIT0319), Nilay Kant Shahi (23BIT0334), Rwitankar Giri (23BIT0335) |
| Guide | Mohanraj G, Assistant Professor Senior Grade 2 |
| Registered title (Review 1, 19 Aug 2026) | *Design of an Authentication System Using Fractal Geometry with Graph-Based Random-Walk OTP Generation* |
| Final system name | **VaultTrust** — step-up authentication for high-value bank transfers |
| Code | `D:\sem7\semprojComponent34` (git branch `ui-overhaul`; see §12 on uncommitted work) |

Component ownership in the original Face Anti-Spoofing brief: Components 1–2 (spatial + frequency
anti-spoofing, passive liveness) by teammates; Components 3–4 (active liveness, explainable AI) and the
random-walk OTP by Nilay. The integrated system, evaluation and fixes were completed 6–13 Oct 2026.

---

## 2. What the system does

A mock bank (Streamlit web app). Small transfers (< $1,000) settle immediately. A transfer of $1,000
or more requires, **at that moment**:

1. **Inherence — the live, genuine, matching face**
   * *Active liveness*: two random challenges (blink twice, turn left, turn right, smile, look up), judged
     relative to the user's own neutral pose.
   * *Passive anti-spoofing*: a dual-branch CNN (RGB spatial branch + FFT frequency branch) scores 10
     neutral frames; median vs a calibrated threshold.
   * *Continuity*: one live face must stay in view from calibration to the last challenge; challenge-phase
     frames must show the same person and also pass anti-spoofing.
   * *Face recognition*: ArcFace (ResNet-50, WebFace600K) embedding matched against a **cancelable
     template** (chaotic-map-keyed projection, 512 → 256 dimensions); the raw embedding is never stored.
   * *Explanation*: Grad-CAM on both branches, branch attribution, radial frequency profile, high-frequency
     energy, fractal dimension, liveness timeline, plain-language reasons.
2. **Possession — the paired phone**
   * The laptop shows a QR code with the transfer reference, amount and payee. The phone authenticator
     computes a **random-walk OTP** from secret K, the 30-s time step and a hash of the transfer
     ("dynamic linking"); the code is valid only for that exact transfer.

Every decision and rejection reason is written to a per-user security log.

### User flows
* **Sign up**: email code → face enrolment (liveness + anti-spoofing) → protected template created →
  phone pairing by QR (secret K shown once) → confirm first code → account created ($25,000 starting
  balance).
* **Sign in**: email → liveness + anti-spoofing + continuity + template match → Accounts page.
* **Transfer < $1,000**: settles atomically.
* **Transfer ≥ $1,000 (step-up)**: presence check (up to 3 attempts, or block) → transfer QR → phone
  approval code → server verification (grace window, replay check, 3 wrong codes block) → settle.
* **Pair a new phone (re-pair)**: fresh face check (reused if one passed < 3 min ago) → new K → old
  pairings stop working.

---

## 3. Architecture and code map

```
Browser (Streamlit UI, WebRTC camera) ──► app.py (pages, routing, decisions)
     │                                        ├── ui_components.py   camera widget, verification pipeline,
     │                                        │                      continuity check, evidence card
     │                                        ├── liveness_engine.py MediaPipe processor (challenges, continuity)
     │                                        ├── fas_engine.py      anti-spoofing scoring + explanation
     │                                        ├── face_engine.py     InsightFace RetinaFace + ArcFace
     │                                        ├── biometric_template.py cancelable template
     │                                        ├── database.py        SQLite + Fernet
     │                                        ├── model_lab.py       evaluation/demo page
     │                                        └── semprojOTP/otp_system/walk_otp.py  OTP core
Phone browser ──► authenticator_server.py (port 8600) ──► authenticator/index.html + walk_otp.js (offline OTP)
```

| File | Role |
|---|---|
| `app.py` | Streamlit app; pages via `st.navigation` (top bar; URLs `/accounts`, `/sign-in`, `/open-account`, `/model-lab`, hidden `/verify-transfer`, `/pair-phone`); browser back/forward work |
| `ui_components.py` | `liveness_camera` (WebRTC + instruction panel), `presence_step` (background verification), `verify_presence` (decision fusion), `_check_continuity`, `evidence_card`, `explain_panel` |
| `liveness_engine.py` | `LivenessProcessor` (calibration, challenges, continuity, frame sampling), `measure()` |
| `fas_engine.py` | model loading, `assess_frames` (median of N), `explain` (Grad-CAM, attribution, spectrum, FD), operating point and enforce/advisory policy |
| `spatial_frequency_model.py`, `frequency_transform.py` | teammates' dual-branch model and FFT input |
| `face_engine.py` | `embed`, `embed_best`, `cosine`; MATCH_THRESHOLD 0.40 |
| `biometric_template.py` | `new_key`, `protect`, `match` |
| `database.py` | users, transactions, audit, used_otps; migrations; `settle_transaction` atomic |
| `authenticator_server.py`, `authenticator/` | phone page; pure-JS SHA-256/HMAC; pairing, approval, account picker |
| `semprojOTP/otp_system/walk_otp.py` | OTP v2 core (shared with the Review-1 FastAPI server) |
| `model_lab.py` | metrics tables, operating point, OTP and template demos |
| `training/train_fas_v2.py` | training/evaluation pipeline |
| `tools/` | `extract_frames.py`, `label_captures.py`, `recalibrate.py`, `webcam_check.py`, `build_report.py` |
| `tests/` | 105 automated tests (see §9) |
| `DEMO.md`, `architecture.md` | runbook and design summary |

---

## 4. Components in detail

### 4.1 Active liveness (`liveness_engine.py`)
* Model: MediaPipe Tasks **FaceLandmarker** (`face_landmarker.task`, 3.8 MB): 478 landmarks,
  52 blendshapes, 4×4 facial transformation matrix. Runs on a 480-px-wide copy of each frame;
  one process-wide re-entrant lock serialises all MediaPipe calls.
* Signals: yaw = atan2(R[0,2], R[2,2]), pitch = asin(−R[1,2]) (degrees); blink = mean(eyeBlinkLeft,
  eyeBlinkRight); smile = mean(mouthSmileLeft, mouthSmileRight); EAR (logged); mouth ratio.
* Calibration: 20 frontal frames (|yaw| < 15°, |pitch| < 20°); every 2nd frame kept → 10 clean frames;
  baseline = median of each signal.
* Challenges (2 distinct, random), 9 s each, judged relative to baseline:
  * turn left/right: yaw change > 18° (display mirrored: user's left = negative yaw)
  * look up: pitch decrease > 12°
  * blink twice: closure > max(0.45, rest + 0.3) then < max(0.25, rest + 0.1), twice
  * smile: score > max(0.45, rest + 0.25)
* Fail conditions: timeout; more than one face; **continuity broken** (see 4.2).
* Camera: WebRTC 640×480 at 15 fps (no STUN server; local stream). Processing ≈ 11 ms/frame
  (was 24 ms before the overlay was optimised); budget at 15 fps = 66 ms.
* UI: camera (max 560 px) with a live instruction panel (current step, checklist, countdown, tips);
  completion polled by a Streamlit fragment every 0.8 s (no full-page reruns).

### 4.2 Continuity (added 11 Oct after a successful swap attack, §7)
* Processor (`GAP_LIMIT` 0.7 s, `JUMP_SHIFT` 0.5 face-widths, `JUMP_SCALE` 1.5×):
  * during calibration, a gap > 0.7 s, a jump or a second face **restarts calibration and discards its
    frames**;
  * during challenges the same events **fail the attempt** ("Face left the view…", "A different face
    appeared…").
  * every 3rd frame during challenges is sampled (max 24, thinned evenly) with its signals.
* Server (`_check_continuity`, CONTINUITY_THRESHOLD 0.35): ArcFace of 3 challenge frames vs the
  calibration embedding (same person 0.5–0.8; different people < 0.25); neutral challenge frames
  (|Δyaw|,|Δpitch| < 10°, blink and smile < 0.5, ≥ 3 frames) must also pass anti-spoofing.
* Measured on genuine videos: max shift 0.02–0.03 face-widths per frame, max gap 0.07 s. The recorded
  attack: 0.94 s gap and a 0.9-face-width jump.

### 4.3 Passive anti-spoofing (`fas_engine.py`, teammates' model)
* Architecture `SpatialFrequencyFAS`: two ResNet-18 encoders (ImageNet init). Spatial input: RGB crop
  224×224, ImageNet normalisation. Frequency input: per-channel 2-D FFT log-magnitude, shifted,
  min-max normalised, 224×224. 512 + 512 → FC 256 → BatchNorm → ReLU → Dropout 0.4 → FC 2.
  22,616,450 parameters (11.18 M per encoder, 0.26 M head). Checkpoint ≈ 90 MB.
* Face crop: MediaPipe landmarks bounding box + 20 % margin (`mediapipe_face.detect_and_crop_face`),
  identical in training and inference.
* Decision: median REAL probability of 10 calibration frames ≥ threshold (and neutral challenge
  frames, §4.2). Policy file `models/policy.json`: `enforce` (default) or `advisory` (score shown and
  logged, not blocking). **Currently `advisory` — switch back to enforce.**
* Training recipe (`training/train_fas_v2.py`): subject/person-wise split (no person in two splits);
  layer3 + layer4 of both encoders and the head fine-tuned; AdamW, one-cycle LR (1e-4 backbone,
  1e-3 head), label smoothing 0.1, batch 16, 2,000 samples/epoch, webcam samples weighted 3×;
  augmentation before both branches and for both classes: random crop 78–100 %, flip,
  brightness/contrast, white balance, downscale 35–80 % (distance), blur, gamma 1.2–1.8 (backlight),
  sensor noise, JPEG 35–95. Threshold = equal-error point on webcam validation clips; best epoch by
  validation ACER.

| Version | Data | Threshold | Notes |
|---|---|---|---|
| v1 original | head only on frozen ImageNet features, all 416 LCC real images, no split | 0.50 | memorised LCC; accepted phone replays |
| v2 | LCC-FASD, subject split, fine-tuned | 0.50 (EER gave 0.965, unstable) | "blurry = spoof" bias; rejected backlit real faces |
| v3 | + Rwitankar webcam videos; **Nilay held out** | 0.235 | evaluation model for the unseen-person test |
| v4 | + all webcam captures | 0.165 | deployed 8–11 Oct; fooled by a phone held close (10 Oct) |
| **v5 (deployed)** | + 10 Oct phone attack (spoof) + 10 Oct real sign-in | **0.185** | trained 11 Oct 20:44; `models/fas_v2.pth` is a copy of `fas_v5.pth` |

Backups kept: `models/fas_v2_lcc_only.pth`, `fas_v3.pth`, `fas_v4.pth`, `fas_v5.pth` (+ calibration
JSONs). Reports before v5 in `reports/backup_before_v5/`.

### 4.4 Explainable AI
* **Grad-CAM** on `layer4` (7×7) of both encoders, from the exact tensors classified (gradients via
  tensor hooks). The original code targeted the average-pool layer (1×1 → flat heatmap) and fed an
  unnormalised crop with a zero frequency tensor — both fixed.
* **Branch attribution**: gradient × activation on the fused 1024-D vector for (logit_real − logit_spoof),
  summed per branch ("+ REAL / − SPOOF").
* **Radial frequency profile**: azimuthally averaged log power spectrum (Hann window, 128×128), vs mean
  of live training faces.
* **High-frequency energy**: share of spectral power above 0.4 × Nyquist, vs live mean ± std.
* **Fractal dimension**: differential box counting (Sarkar & Chaudhuri 1994) on the inner 70 % of the
  crop, 128×128 grey, box sizes 2–32; vs live mean ± std.
* **Liveness timeline**: eye closure, smile, Δyaw, Δpitch per frame with phases shaded.
* **Reasons**: generated from the numbers (failed check, dominant branch, HF z-score, match score,
  continuity). Everything runs locally; no LLM/API (the unused Gemini wrapper was archived 11 Oct).

### 4.5 Face recognition (`face_engine.py`)
* InsightFace `buffalo_l`: RetinaFace detector `det_10g.onnx` (16.9 MB, det size 320, 5 landmarks) →
  similarity alignment to 112×112 → ArcFace ResNet-50 `w600k_r50.onnx` (174 MB, WebFace600K) →
  512-D L2-normalised embedding. Login averages 5 frames. ONNX Runtime CPU.
* Original teammate code resized an unaligned MediaPipe crop to 112×112 (no alignment) — replaced.
* Match: cosine in the protected domain ≥ 0.40.

### 4.6 Cancelable template (`biometric_template.py`)
* Per-user 256-bit key → HMAC-SHA256 → logistic map x₀ ∈ (0.01, 0.99), r ∈ [3.99, 3.9999], 500 burn-in
  iterations. Sequence 1 → permutation of the 512 dimensions; sequence 2 → 512×256 matrix,
  orthonormalised by QR, giving W (256×512) with orthonormal rows. Template = normalise(W · e[perm]) (256-D float32). Key generation 57 ms
  (cached per key).
* Properties measured: protected vs raw cosine correlation 0.994 (mean abs diff 0.029); same face under
  two keys cosine ≈ −0.02 to −0.05 (unlinkable); 512 → 256 is many-to-one (not uniquely invertible).
* Storage: template (1,024 bytes) in clear; template key and OTP secret Fernet-encrypted
  (AES-128-CBC + HMAC-SHA256) with the master key in `db_key.key` (gitignored).

### 4.7 Random-walk OTP v2 (`walk_otp.py`, `authenticator/walk_otp.js`)
* T = ⌊unix time / 30⌋. seed = HMAC-SHA256(K, T as 8 bytes ‖ SHA256(context)); context = "" (pairing)
  or `TX|ref|amount_cents|payee_lowercase` (transfer).
* Stream = SHA256(seed ‖ i) for i = 0, 1, …; rejection sampling for uniform choices.
* Graph: 64 nodes, ring lattice degree 6, Watts–Strogatz rewiring p = 0.3, built from a public seed
  0xDEADBEEF with the same SHA-256 stream (connected; degrees 3–10).
* Walk: start node + 16 steps (17 nodes); code = RFC 4226 dynamic truncation of
  SHA256("walk-otp-v2|" ‖ path as 2-byte ints) mod 10⁶.
* Verification: current step; previous step only within **10 s** after it changed; next step only if the
  phone is ≤ 10 s ahead (`grace_seconds`); `otp_age` distinguishes "expired" from "wrong".
  Replay: `used_otps` table refuses a time step ≤ the last accepted one per (account, scope).
* v1 defect (found 8 Oct): Mersenne Twister + truncation of raw path bytes → the 4-byte window only
  covered two node IDs → **768 distinct codes from 20,000 random secrets** (brute force ≈ 800 guesses).
  v2: 19,821 distinct / 20,000 (uniform), 4,987 / 5,000.
* Cross-platform: 12 fixed test vectors (graph, path, code) identical in Python and JavaScript; a live
  code computed by Node at the current time is accepted by the server.
* Generation latency ≈ 1 ms.

### 4.8 Phone authenticator (`authenticator/`)
* Static page served by `authenticator_server.py` on port 8600 (all interfaces). Pure-JS SHA-256 and
  HMAC (browsers disable `crypto.subtle` on plain-http LAN pages).
* Pairing QR: `http://<laptop-ip>:8600/#pair=<base32 K>&u=<email>`; K stored in `localStorage`; the
  fragment is removed from the address bar; the fragment is never sent to the server.
* Transfer QR: `#tx=<base64url {id, a, p, u}>`; Approve reveals the code, Deny warns.
* Default view: "Pairing check code", account picker, "Remove this account from this phone".
* Limitation: browser storage is per origin (IP + port) → a network change makes the phone say "no
  key at this address"; handled by re-pairing (app warns when the address differs from the stored
  `paired_host`).

### 4.9 Decision fusion and policies (`ui_components.verify_presence`, `app.py`)
`passed = liveness_passed AND anti_spoofing_ok AND match_ok AND face_found AND continuity_passed`,
where anti_spoofing_ok = (calibration median ≥ thr AND challenge-frame median ≥ thr when measured)
OR advisory policy. Step-up limit $1,000; 3 presence attempts; 3 OTP attempts; email code 10 min /
5 tries; pairing 5 tries; face reuse for re-pairing 180 s.

### 4.10 Data model (`vaulttrust.db`)
* users(email PK, template BLOB, template_key BLOB, otp_secret BLOB, device_paired, balance,
  created_at, paired_host, paired_at)
* transactions(id, ref UNIQUE, sender, receiver, amount, status, created_at, evidence JSON)
  statuses: PENDING, PENDING_STEP_UP, COMPLETED, CANCELLED, BLOCKED_PRESENCE, BLOCKED_OTP, FAILED_FUNDS
* audit(id, email, event, detail JSON, created_at)
* used_otps(email, scope, counter) PK(email, scope, counter)

---

## 5. Data

| Source | Content | Use |
|---|---|---|
| LCC-FASD development subset | 416 real, 2,590 spoof face crops; ~75 subject groups (`idNN`) | training/validation/test (subject split: 52 / 11 / 12 groups; test = 564 frames, 103 real) |
| Rwitankar webcam videos (9 Oct) | 3 real (15 fps, 1280×720), 2 phone replays (30 fps) → 446 crops at 4 fps (213 real / 233 spoof) | training + validation (real_1, phone_1 = calibration clips) |
| Nilay app captures (8–10 Oct) | 10 crops per attempt; labelled: real 161718, 200636, 200707, 200829, 220846; phone 163700, 220946 | training (v4/v5), test (v3) |
| Unlabelled 10 Oct attempts | 213852, 214409, 214440 (frontal, scored 0.10–0.18 by v4), 215646, 215739 | used only as unseen checks; **owner to confirm they were real** |
| Screen recording `recordings/2026-10-10 22-08-25.mp4` | sign-in + swap attack (phone during calibration) | regression test of continuity |

Faces are personal data: `data/`, `recordings/`, `vaulttrust.db`, `db_key.key`, `.env` are gitignored.

---

## 6. Results (all measured)

### 6.1 Anti-spoofing — LCC-FASD test (12 unseen subjects, 564 frames)
| Model | AUC | Notes |
|---|---|---|
| v1 original | 1.000 | memorised (test images were in its training data) |
| v2 spatial + frequency | 0.970 | at 0.5: APCER 21.5 %, BPCER 4.9 %, ACER 13.2 % |
| v2 spatial only | 0.986 | best on LCC |
| v2 frequency only | 0.736 | weak alone |
| HF energy only (logistic) | 0.691 | handcrafted |
| Fractal dimension only (logistic) | 0.523 | ≈ chance → explanation only |
| v3 | 0.832 | webcam-tuned |
| v4 | 0.903 | at its threshold 0.165: LCC APCER ≈ 55–72 % (cross-domain gap) |
| **v5** | **0.944** | |

### 6.2 Anti-spoofing — our webcam (median REAL score per clip/attempt)
| Clip | Truth | v1 | v2 | v3 | v4 | v5 |
|---|---|---|---|---|---|---|
| Rwitankar phone 1 | spoof | 0.68 ✗ | 0.18 ✓ | 0.06 ✓ | 0.06 ✓ | 0.04 ✓ |
| Rwitankar phone 2 | spoof | 0.80 ✗ | 0.22 ✓ | 0.06 ✓ | 0.04 ✓ | 0.02 ✓ |
| Rwitankar real 1 / 2 / 3 | real | ✓✓✓ | ✗✗✓ | ✓✓✓ | ✓✓✓ | 0.85 / 0.95 / 0.97 ✓ |
| Nilay phone photo (8 Oct) | spoof | 0.15 ✓ | 0.07 ✓ | 0.08 ✓ | 0.02 ✓ | 0.09 ✓ |
| Nilay phone held close (10 Oct) | spoof | 0.06 ✓ | 0.09 ✓ | 0.21 ✓ | **0.72 ✗** | **0.03 ✓** |
| Nilay front-lit / backlit ×3 | real | mixed | mostly ✗ | 2 / 4 ✓ | ✓ | ✓ (0.86–0.96) |
| Nilay 21:06 (never trained) | real | 0.08 ✗ | 0.10 ✗ | 0.33 ✓ | 0.94 ✓ | 0.78 ✓ |
| Nilay 21:38 / 21:44 / 21:44 (never trained; presumed real) | real? | — | — | — | 0.16 / 0.16 / 0.15 ✗ | 0.74 / 0.42 / 0.44 ✓ |

v5 trained on most labelled clips (pipeline check, not generalisation). Generalisation evidence:
**v3 on an unseen person** (Nilay, 50 frames, threshold 0.235): AUC 0.925, APCER 10 %, BPCER 25 %,
ACER 17.5 % per frame; per attempt the phone attack was blocked.

### 6.3 Face recognition and template
* Dataset faces (14 LCC subjects, ~42 images), protected domain at 0.40: genuine pairs 98–100 %
  accepted, impostor pairs 0 %.
* Live: Nilay matched himself at 0.47–0.80; impostors in tests ≈ 0.02–0.05.

### 6.4 Liveness on recorded video
* Real videos pass blink challenges (blinks detected in 0.4–1.7 s).
* A phone replay of natural blinking **passes blink-only liveness** (why passive anti-spoofing is needed)
  and **fails a random turn challenge** (timeout).
* Field use (9 Oct logs): every genuine attempt passed both challenges, typically in 1–4 s.
* Swap attack recording: blocked at 70.05 s, the moment the phone is removed.

### 6.5 Latency (laptop CPU, no GPU)
| Step | Time |
|---|---|
| Liveness per frame (landmarks + overlay) | 11 ms (24 ms before optimisation) |
| Anti-spoofing, 10 frames | 478 ms |
| ArcFace per frame (detect + align + embed) | 205 ms at 640×360; 340–370 ms at 640×480 (13 Oct) |
| Explanation (2 Grad-CAMs, attribution, spectrum, FD) | 511 ms |
| Full presence verification | 1.85 s before continuity (640×360 frames, 9 Oct); **4.2 s min / 4.8 s mean with continuity** (640×480, 13 Oct) |
| — of which ArcFace (5 calibration + 3 challenge frames) | 1.72 s + 1.10 s ≈ 2.8 s (main cost; optimisation: fewer frames or pre-cropped faces) |
| — anti-spoofing 10 + 6 frames; explanation | 436 ms + 264 ms; 213 ms |
| Template key schedule | 57 ms |
| OTP generation | ≈ 1 ms |
| First-call costs (now pre-warmed at startup) | ArcFace 3.65 s, anti-spoofing 0.46 s, MediaPipe 0.07 s |

---

## 7. Defects and attacks found, and fixes (chronological)

| Date | Finding | Fix |
|---|---|---|
| 8 Oct | Grad-CAM targeted avg-pool (flat 1×1 map), wrong inputs | layer4 hooks on exact tensors |
| 8 Oct | v1 anti-spoofing memorised LCC; low confidence on webcam | retraining pipeline, subject split, fine-tuning |
| 8 Oct | Anti-spoofing scored the frame captured mid-challenge, with overlay text | 10 clean calibration frames, median |
| 8 Oct | Face recognition never ran after signup; login was email-only | ArcFace at login and step-up |
| 8 Oct | OTP shown on the same screen; JS and Python codes differed; **768-code space** | phone authenticator, OTP v2, test vectors |
| 8 Oct | Liveness: smile metric inverted, pitch uncalibrated, single challenge | blendshapes + pose matrix, baseline-relative, 2 challenges |
| 8 Oct | Lock deadlock in camera thread (no overlay) | re-entrant lock |
| 8 Oct | Verification repeated 2–4× per attempt (auto-refresh reruns) | background thread job |
| 8 Oct | Intermittent native crash on camera teardown | single MediaPipe lock; faulthandler log (no recurrence) |
| 8 Oct | "Blurry = spoof" bias exposed by the explanation (backlit real faces rejected) | webcam data + quality augmentation (v3/v4) |
| 9 Oct | Expired OTP accepted for 30 s after change | 10 s grace + "expired" message |
| 9 Oct | No way to switch account | switch/back buttons |
| 9 Oct | Phone "not paired" after network change; no re-pair | re-pair flow, paired_host warning, phone page explanations |
| 9 Oct | QR image sometimes missing (media race) | inline data-URI QR |
| 9 Oct | Browser back left the site | `st.navigation` URLs |
| 9 Oct | Deleted account crashed the dashboard | redirect home |
| 9 Oct | Misleading "71 % attacks accepted" (LCC numbers under webcam threshold) | webcam view default; LCC view labelled |
| 10 Oct | Camera laggy | fragment polling, 15 fps, banner-only overlay, 2 cores free, warm-up |
| 10 Oct | **Swap attack succeeded**: phone during calibration, live person for challenges (v4 scored the phone 0.72) | continuity (§4.2) + v5 retraining |
| 11 Oct | Unused Gemini wrapper; real key in `.env` (never committed) | archived; owner advised to revoke |

---

## 8. Threat model (summary)
| Threat | Defence | Tested |
|---|---|---|
| Stolen password / hijacked session | step-up needs live face + phone at transfer time | flows |
| Printed / on-screen photo | liveness (cannot blink/turn/smile) + anti-spoofing | ✓ photo on phone: rejected |
| Replay video | random distinct challenges + anti-spoofing | ✓ blink-only passes L, random turn fails L, F blocks |
| Different live person | ArcFace template match | ✓ similarity ≈ 0.02 |
| Swap (photo then person) | continuity + challenge-frame identity/anti-spoofing | ✓ recorded attack blocked |
| Code for a modified transfer | dynamic linking | ✓ $0.01 change → different code |
| Code replay / brute force | used_otps, 3 attempts, 10⁶ uniform space | ✓ |
| Template database leak | cancelable template, re-keying | ✓ unlinkability |
| Not covered | deepfake/virtual-camera injection, 3-D masks, TLS, secure key storage on phone, login lockout | future work |

---

## 9. Testing
105 automated tests, all passing (11 Oct, 7.5 min):
* `semprojOTP/otp_system/tests/test_walk_otp.py` (31): OTP core, FastAPI server (enroll, verify,
  replay, rate limit), graph determinism.
* `semprojOTP/otp_system/tests/test_vectors.py` (6 + parametrised): Python↔JS vectors, grace window.
* `tests/test_pipeline.py` (15 + parametrised): liveness state machine, real landmarker in a thread,
  continuity (jump, rescale, gap, dropout tolerance, natural movement, calibration restart, frame
  sampling), verification genuine/impostor/swap.
* `tests/test_e2e.py` (39 + parametrised): OTP, authenticator server, face/template, anti-spoofing,
  liveness on real video, database, recorded swap attack, 19 AppTest workflows (sign-up, sign-in,
  transfers, 5 attacks, advisory policy, security log, navigation, re-pairing, expiry, pending
  transfers).
* `tests/test_liveness.py`, `tests/test_explainability.py` (legacy modules).

Run: `python -m pytest tests semprojOTP/otp_system/tests -q -p no:warnings` (tests use a temporary
database and never save captures).

---

## 10. Operations
* Run: `python -m streamlit run app.py` → http://localhost:8501; phone page on port 8600.
* Environment: `VT_SAVE_CAPTURES=0` (stop saving login frames), `VT_DB_PATH` (alternate DB),
  `AUTH_HOST` / `AUTH_PORT` (phone page address), `WALK_OTP_STORE_PATH` (FastAPI store).
* Retrain: label captures (`tools/label_captures.py --person NAME real=… phone=…`), then
  `python -u training/train_fas_v2.py --epochs 3 --out models/fas_vN.pth`; compare per clip; copy to
  `models/fas_v2.pth` + `models/fas_calibration.json`; restart.
* Software: Python 3.14.3, Streamlit 1.64.0, streamlit-webrtc 0.78.1, aiortc 1.15.0, PyAV 17.1.0,
  MediaPipe 0.10.35, PyTorch 2.14.1, torchvision 0.29.1, InsightFace 2.0, ONNX Runtime 1.30.0,
  OpenCV 5.0, NumPy 2.4.2, scikit-learn 1.8.0, Plotly 6.6.0, cryptography 50.0.0, qrcode 8.2,
  pytest 9.1.1, Node 22.14, FastAPI 0.128.8.
* Hardware: Windows 11 laptop, CPU only, built-in webcam; Android phone on the same hotspot.

---

## 11. Limitations and future work
* Webcam data from only 2 people and mainly phone-replay attacks; need 10+ people, prints, tablets,
  monitors, masks; leave-one-person-out evaluation.
* Webcam-tuned threshold is permissive on LCC attack types (cross-domain gap).
* Frequency branch unproven on our data; fractal dimension near chance.
* Camera round trip through Python (lag, slow first start) → in-browser MediaPipe JS.
* Phone key tied to laptop IP; no HTTPS; key in browser storage; master key on disk.
* Review-1 items only partly delivered: fractal features in the template, fractal-derived OTP seed.
* Delegated access (team's third idea) not built.

## 12. Housekeeping state (13 Oct)
* `models/policy.json` = advisory → switch to enforce before demos.
* All work since commit `09e3da6` (6 Oct) is **uncommitted** on branch `ui-overhaul`.
* `.env` holds an unused Gemini API key (never committed) — delete/revoke.
* Project guide (web): https://claude.ai/artifact/7mtbzSZN5c6ZRD3KWCy8mt
