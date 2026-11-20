# VaultTrust — Handoff (16 Oct 2026)

Read this first in a new session. It says what exists, where it is, what is finished, what is open,
and the rules to follow. Deeper detail: `docs/PROJECT_RECORD.md` (every number, defect and decision up
to 13 Oct), `docs/REPORT_PLAN.md` (report template rules), `docs/LITERATURE_NOTES.md` (verified sources).

---

## 1. The project in one paragraph

**VaultTrust** is the BITE497J Project I (VIT Vellore, SCORE, Dept. of IT, Fall 2026–27) of
Magizharasan K (23BIT0319), Nilay Kant Shahi (23BIT0334, the user) and Rwitankar Giri (23BIT0335);
guide Prof. Mohanraj G, Assistant Professor Senior Grade 2. Registered title: *Design of an
Authentication System Using Fractal Geometry with Graph-Based Random-Walk OTP Generation*. It is a
Streamlit mock bank: any transfer of **$1,000 or more** needs, at that moment, the account holder's
**live, genuine, matching face** and a **code from the paired phone bound to that amount and payee**.
The face check combines **A** (ArcFace on a cancelable template), **L** (active liveness: 2 random
challenges + face continuity) and **F** (dual-branch spatial + FFT ResNet-18 anti-spoofing); decision =
A AND L AND F (plus continuity). Every decision is explained (Grad-CAM, branch attribution, spectrum,
high-frequency energy, fractal dimension, liveness timeline, reasons).

## 2. Status

| Item | State | Where |
|---|---|---|
| Working system | **Complete** (user considers the project done) | repo root, `app.py` |
| Automated tests | 105, all passing (last full run 11 Oct) | `tests/`, `semprojOTP/otp_system/tests/` |
| Project record | Done (13 Oct) | `docs/PROJECT_RECORD.md` |
| Evaluation suite + results | Done (13 Oct) | `evaluation/`, `reports/eval/*.json`, `reports/eval/figures/` |
| Final report (.docx/.pdf) | Done, 97 pages; Ch.1–References = 72 pages (≥ 70 required) | `docs/report/VaultTrust_Final_Report.docx` / `.pdf` |
| Signed report | The user produced a signed PDF | `docs/report/VaultTrust_Final_Reportsigned.pdf` |
| 25-slide deck | Done, with speaker notes | `docs/slides/VaultTrust_Final_Review.pptx` / `.pdf` |
| Review | A review took place on 14 Oct; outcome not recorded here — ask the user | — |

**Important:** the user edited `VaultTrust_Final_Report.docx` by hand on 14 Oct (after it was generated)
and made a signed PDF. **Running `docs/report/build_report.py` overwrites that .docx.** If the report must
be regenerated, build to a different file name or ask the user first, then re-apply their edits.

## 3. Open items (ask / remind the user)

1. **`models/policy.json` is `{"fas_mode": "advisory"}`** — anti-spoofing logs but does not block. It must be
   `"enforce"` for any demo (Model Lab toggle or edit the file). This is the user's setting: remind, don't change unasked.
2. **Revoke the Gemini API key** in `.env` (unused, never committed; the wrapper was archived to `_archive/`).
3. **Friends' test results** — the user tested with friends but no numbers were recorded. If wanted in the report,
   ask for: number of people, attempts, passes/rejections with reasons, attacks tried → add to report §7.4
   (field trial) and slide 18.
4. **Latency was measured on battery** (8.1 s total, ArcFace 723 ms/frame). The report quotes the 13 Oct mains-power
   numbers (4.2 s min / 4.8 s mean, ArcFace 340–370 ms/frame) beside it. To refresh: plug in, close other apps,
   `python evaluation/eval_latency.py`, then rebuild (see §8 warning).
5. **Missing analyses (user decided not to train further, 13 Oct — do not retrain):** no frequency-only model and no
   leave-one-person-out model with Rwitankar held out. The report states both gaps.
6. **Nothing is committed** since `09e3da6` (6 Oct) on branch `ui-overhaul` (~56 changed/untracked paths). Commit only
   if the user asks; never commit `data/`, `recordings/`, `logs/`, `*.db`, `db_key.key`, `.env`, `_archive/`.
7. Old question, still unanswered: were the 10 Oct captures 21:38:52 / 21:44:09 / 21:44:40 real faces? (If yes they
   could be labelled real for a future retrain.)

## 4. Rules for whoever continues

* **Privacy:** faces are personal data. `data/`, `recordings/`, `vaulttrust.db`, `db_key.key`, `.env`, `logs/` are
  gitignored and must never be published or committed. Report/slide figures with faces use LCC-FASD images or are
  pixelated; e-mails are blurred (`docs/report/screenshots.py`).
* **Tests** use a temporary DB, mock e-mail, `VT_SAVE_CAPTURES=0`; keep it that way.
* **Do not change models, thresholds or policy** without the user asking. Deployed model = v5.
* **Numbers in documents come from `reports/eval/*.json`** — never type a result by hand; never quote a literature
  number that is not in `docs/LITERATURE_NOTES.md` (verified from the papers).
* Write the report in "we" (team voice); avoid gendered pronouns for the guide.
* Python env: Python 3.14 at `D:\Python`. Install extra tools (PyMuPDF, defusedxml, node packages) into the
  session scratchpad, not into the project or the global environment.

## 5. Run it

```bash
python -m streamlit run app.py                 # http://localhost:8501 ; phone page on port 8600
python -m pytest tests semprojOTP/otp_system/tests -q -p no:warnings   # 105 tests, ~7.5 min
```
Laptop and phone on the same Wi-Fi/hotspot. If the phone says "not paired" (laptop IP changed), use
*Re-pair my phone*. Env vars: `VT_SAVE_CAPTURES=0`, `VT_DB_PATH`, `AUTH_HOST`/`AUTH_PORT`, `WALK_OTP_STORE_PATH`.
Models warm up in a background thread at start (ArcFace first call ≈ 3.7 s).

## 6. System facts (for answers and edits)

* **Liveness (L)** `liveness_engine.py`: MediaPipe Face Landmarker (478 landmarks, 52 blendshapes, pose matrix) on a
  480-px copy; calibration = 20 frontal frames (|yaw|<15°, |pitch|<20°), 10 clean frames kept, baseline = medians;
  2 distinct random challenges of 5, 9 s each — blink twice (closure > max(0.45, rest+0.3) then < max(0.25, rest+0.1)),
  turn L/R (Δyaw > 18°, mirrored), look up (Δpitch > 12°), smile (> max(0.45, rest+0.25)).
* **Continuity:** processor fails/restarts on a gap > 0.7 s, centre jump > 0.5 face widths, scale change > 1.5×, or a
  2nd face; samples every 3rd challenge frame (max 24). Server (`ui_components._check_continuity`): ArcFace of 3
  challenge frames vs calibration ≥ 0.35, and ≥ 3 neutral challenge frames must pass anti-spoofing.
* **Anti-spoofing (F)** `fas_engine.py`, `spatial_frequency_model.py`: two ResNet-18 (RGB 224² + per-channel FFT
  log-magnitude), concat 1024 → FC256 → BN → ReLU → Dropout 0.4 → FC2; 22.6 M params; crop = MediaPipe box + 20 %;
  decision = median P(real) of 10 frames ≥ threshold; deployed **v5, threshold 0.185** (`models/fas_v2.pth` is a copy
  of `models/fas_v5.pth`).
* **Face (A)** `face_engine.py`: InsightFace buffalo_l (RetinaFace det_10g + ArcFace R50 w600k), mean of 5 frames,
  match threshold 0.40 in the protected domain.
* **Cancelable template** `biometric_template.py`: per-user 256-bit key → HMAC-SHA256 → logistic map (x₀, r ∈
  [3.99, 3.9999], 500 burn-in) → permutation + QR-orthonormalised 256×512 projection; 1,024-byte template; Fernet
  for the key and the OTP secret at rest. (This logistic map is where "fractal geometry" lives, plus the fractal
  dimension shown as an explanation feature.)
* **Random-walk OTP v2** `semprojOTP/otp_system/walk_otp.py` + `authenticator/walk_otp.js`: seed =
  HMAC-SHA256(K, T₈ ‖ SHA-256(ctx)), ctx = `TX|ref|amount_cents|payee`; SHA-256 counter-mode stream with rejection
  sampling; 64-node ring lattice (degree 6) rewired p = 0.3 (public seed 0xDEADBEEF); start + 16 steps; code = RFC 4226
  truncation of SHA-256("walk-otp-v2|" ‖ path); 30-s steps, 10-s grace, replay table, 3 tries. v1 bug: only 768
  distinct codes.
* **Limits:** step-up $1,000; 3 presence attempts; 3 OTP attempts; e-mail code 10 min / 5 tries; re-pair face reuse 180 s.

## 7. How the anti-spoofing model was trained (the only model we trained)

`training/train_fas_v2.py`: subject-wise split (LCC-FASD idNN groups 52/11/12; webcam by person; first clip per
(person, attack) → validation); fine-tune layer3 + layer4 of both encoders + head from ImageNet weights; AdamW,
one-cycle LR (1e-4 backbone, 1e-3 head); cross-entropy with label smoothing 0.1; batch 16, 2,000 samples/epoch,
3 epochs, best epoch by validation ACER; webcam samples weighted 3×; augmentation on both classes before both
branches (crop 78–100 %, flip, brightness/contrast, white balance, downscale 35–80 %, blur, gamma 1.2–1.8, noise,
JPEG 35–95); threshold = equal-error point on webcam validation clips. Versions: v1 memorised LCC (no split) → v2
"blurry = spoof" bias → v3 + Rwitankar videos → v4 + all captures (fooled by a phone held close, 0.72) → **v5** +
that attack (0.03). ArcFace, RetinaFace and MediaPipe are pretrained, not retrained.

## 8. Key results (from `reports/eval/*.json`)

| Result | Value |
|---|---|
| ArcFace, protected template | EER 0.25 %, FAR 0 in 13,962 impostor pairs, FRR 0.96 % per 5-frame attempt |
| ArcFace alone vs photos/replays of the right person | **99.6 % accepted** (982/986) |
| Template | raw-vs-protected r = 0.969; same face two keys −0.002; revoked 0/133 |
| Liveness | replay passes blink-only 12/12, random pairs 0/240; photos (still or tilted) 0/45; field trial 78 % first-try pass (54 attempts) |
| Swap (A+L+F, spliced) | 37.5 % before continuity fix → 0 % after; recorded attack blocked at 70.05 s |
| Anti-spoofing, held-out (Nilay unseen) | LCC AUC fused 0.950 / spatial 0.884; unseen webcam person AUC fused 0.751 / spatial 0.902; per attempt: phones blocked, 40 % genuine rejected |
| Combinations (1,000 attempts, 50 % genuine) | A acc 60.2 %; A+L acc 86.6 %, F1 0.845 (best); A+L+F acc 82.0 %, precision 100 %, recall 64.1 %, no attack type accepted; A+F blocks 52 % of re-imaged faces if L is bypassed |
| OTP | 19,781 distinct / 20,000 (TOTP 19,790; v1 768); χ² p = 0.14; 0/5,000 same code after a 1-cent change |
| Latency | mains (13 Oct) 4.2–4.8 s per verification; battery (13 Oct) 8.1 s; 11–18 ms per camera frame |

Caveat to keep stating: only 17 held-out genuine attempts and 2 webcam people → wide uncertainty.

## 9. Regenerating the report and slides

**Evaluation** (writes `reports/eval/`): `python evaluation/eval_face.py`, `eval_fas.py`, `eval_liveness.py`,
`eval_system.py` (after the other three), `eval_otp.py`, `eval_latency.py` (idle CPU, mains power). Held-out models in
`models/eval/` (`fas_ablation.pth` fused, `fas_ablation_spatial.pth`). Caches in `reports/eval/cache/`.

**Report** (`docs/report/`, python-docx; **overwrites the hand-edited .docx — see §2**):
```bash
python docs/report/diagrams.py        # architecture/UML/Gantt → docs/report/figures
python docs/report/figures_extra.py   # FFT, Grad-CAM, spectrum, liveness timeline
python docs/report/screenshots.py     # needs recordings/ (gitignored); pixelates faces, blurs e-mails
python docs/report/build_report.py    # → VaultTrust_Final_Report.docx
powershell -ExecutionPolicy Bypass -File docs\tools\docx2pdf.ps1 -In <abs path .docx> -Out <abs path .pdf> -UpdateFields
```
The `-UpdateFields` step (Word COM) fills the contents, list of figures/tables and page numbers — required.
Structure: `ch_front.py` (cover … symbols), `ch1_2.py`, `ch3.py`, `ch4.py`, `ch5_6.py`, `ch7.py` (all numbers from
JSON), `ch8_9.py` (summary, APA references, appendices); engine `docx_engine.py` (markup: `**bold**`, `*italic*`,
`***both***`, `` `code` ``, `x_{sub}`, `x^{sup}`; tables, OMML equations, figure/table captions, roman → arabic → no
page numbers). Template rules (VIT): A4, margins L 1.5″ others 1″, TNR 12, 1.5 spacing, justified; chapter heading
14 pt caps bold; figure caption below "Fig. 2.4 Title", table caption above "Table 6.1 Title", TNR 10; ≥ 70 pages
Ch.1–References; APA references.

**Slides** (`docs/slides/build_deck.js`, pptxgenjs; reads the same JSON + figures):
```bash
cd <scratchpad> && npm init -y && npm install pptxgenjs react-icons react react-dom sharp
NODE_PATH=<scratchpad>/node_modules PPTX_SKILL=<pptx skill dir> node docs/slides/build_deck.js
powershell -ExecutionPolicy Bypass -File docs\tools\pptx2pdf.ps1 -In <abs .pptx> -Out <abs .pdf>
```
`PPTX_SKILL` = the pptx skill folder (provides `scripts/apply_theme.js`). Theme: ink `14212B`, teal `0F7C8C`, amber
`E39B2D`; Cambria headings, Calibri body. For small changes, editing the .pptx in PowerPoint is simpler.

**Visual check:** `docs/tools/render_pdf.py` (needs PyMuPDF, install into the scratchpad) tiles PDF pages into a sheet.

## 10. Repository map

```
app.py, ui_components.py, liveness_engine.py, fas_engine.py, face_engine.py, biometric_template.py, database.py,
model_lab.py, mediapipe_face.py, spatial_frequency_model.py, frequency_transform.py, authenticator_server.py
authenticator/            phone page (index.html, walk_otp.js)
semprojOTP/otp_system/    OTP core + Review-1 FastAPI server + tests
training/train_fas_v2.py  retraining / ablation;  tools/  labelling, recalibration, reports
models/                   fas_v2.pth (= v5, deployed), fas_v3/v4/v5 + calibration JSONs, policy.json, eval/
evaluation/               eval_*.py (results for Ch.7)
reports/                  summary.json, metrics.json (older), eval/ (current JSON + figures)
docs/                     PROJECT_RECORD.md, REPORT_PLAN.md, LITERATURE_NOTES.md, report/, slides/, tools/
data/, recordings/, logs/ (gitignored, personal data)   LCC_FASD_development/ (dataset)
DEMO.md, architecture.md, README.md
```

## 11. Review cheat sheet (short answers)

* **Pitch:** step-up authentication — a transfer ≥ $1,000 needs the live face *and* the phone, and the phone's code
  only works for that amount and payee.
* **Why three components?** A stops impostors but accepts 99.6 % of photos of the right person; L stops photos and
  replays but not impostors; F is defence in depth for videos that can answer prompts (A+F blocks 52 % of re-imaged
  faces if L were bypassed).
* **Fractal geometry?** In the logistic-map key schedule of the cancelable template and the fractal-dimension
  explanation feature; as a spoof detector it is at chance (AUC ≈ 0.5), so it never decides — an honest deviation
  from Review 1.
* **Why not plain TOTP?** It is HMAC-seeded, so as uniform as TOTP, and additionally bound to the transaction.
* **Swap-attack story:** found by attacking our own system on 10 Oct (phone during calibration, live person for the
  challenges); fixed with continuity on 11 Oct; the recording is now a regression test.
* **Weak point (say it first):** anti-spoofing generalises poorly to unseen people (2-person webcam data); future work =
  10+ people, spatial-first / domain-generalising training, in-browser liveness, injection-attack detection.
* **Who did what:** Magizharasan and Rwitankar — spatial-frequency anti-spoofing model, webcam data; Nilay — liveness,
  explainability, random-walk OTP, integration; all three — evaluation and report.

## 12. Suggested first message for a new session

> Read HANDOFF.md and docs/PROJECT_RECORD.md in D:\sem7\semprojComponent34. Then: <your next instruction>.
