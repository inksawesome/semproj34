# Literature Notes — verified facts only

Every number here was read from the primary paper (PDF text extracted locally) unless marked otherwise.
Used for Chapter 2 (literature survey) and Chapter 7 (comparative study) of the final report.

## Face anti-spoofing (passive)

### Yu et al., 2020 — CDCN / CDCN++ (CVPR 2020) — arXiv:2003.04092
Yu, Z., Zhao, C., Wang, Z., Qin, Y., Su, Z., Li, X., Zhou, F., & Zhao, G. (2020). Searching central difference
convolutional networks for face anti-spoofing. In *Proceedings of the IEEE/CVF Conference on Computer Vision and
Pattern Recognition (CVPR)* (pp. 5295–5305).
* Central difference convolution aggregates intensity and gradient; CDCN++ adds NAS backbone + multiscale attention.
* OULU-NPU intra-testing ACER (%) (Table 4), APCER/BPCER/ACER:
  | Protocol | Method | APCER | BPCER | ACER |
  |---|---|---|---|---|
  | 1 | GRADIANT | 1.3 | 12.5 | 6.9 |
  | 1 | STASN | 1.2 | 2.5 | 1.9 |
  | 1 | Auxiliary (Liu et al. 2018) | 1.6 | 1.6 | 1.6 |
  | 1 | FaceDs (Jourabloo et al. 2018) | 1.2 | 1.7 | 1.5 |
  | 1 | FAS-TD (Wang et al. 2018) | 2.5 | 0.0 | 1.3 |
  | 1 | DeepPixBiS (George & Marcel 2019) | 0.8 | 0.0 | 0.4 |
  | 1 | CDCN | 0.4 | 1.7 | 1.0 |
  | 1 | CDCN++ | 0.4 | 0.0 | 0.2 |
  | 2 | DeepPixBiS / FaceDs / Auxiliary / GRADIANT / STASN / FAS-TD / CDCN / CDCN++ | | | 6.0 / 4.3 / 2.7 / 2.5 / 2.2 / 1.9 / 1.5 / 1.3 |
  | 3 | DeepPixBiS / FAS-TD / GRADIANT / FaceDs / Auxiliary / STASN / CDCN / CDCN++ | | | 11.1±9.4 / 5.9±1.0 / 3.8±2.4 / 3.6±1.6 / 2.9±1.5 / 2.8±1.6 / 2.3±1.4 / 1.8±0.7 |
  | 4 | DeepPixBiS / GRADIANT / Auxiliary / FAS-TD / STASN / FaceDs / CDCN / CDCN++ | | | 25.0±12.7 / 10.0±5.0 / 9.5±6.0 / 9.2±3.4 / 7.5±4.7 / 5.6±5.7 / 6.9±2.9 / 5.0±2.9 |
* Cross-dataset HTER (%) (Table 7), train CASIA-MFSD → test Replay-Attack / train Replay → test CASIA:
  Motion-Mag 50.1/47.0; LBP-TOP 49.7/60.6; STASN 31.5/30.9; Auxiliary 27.6/28.4; FAS-TD 17.5/24.0;
  LBP 47.0/39.6; Spectral cubes 34.4/50.0; Color Texture 30.3/37.7; FaceDs 28.5/41.1; CDCN 15.5/32.6;
  CDCN++ 6.5/29.8.
* Cross-type (SiW-M, 13 attacks): CDCN++ average ACER 12.7 %, EER 11.9 %.

### Jia et al., 2020 — SSDG (CVPR 2020) — arXiv:2004.14043
Jia, Y., Zhang, J., Shan, S., & Chen, X. (2020). Single-side domain generalization for face anti-spoofing. In
*Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 8484–8493).
* Leave-one-dataset-out (O = OULU-NPU, C = CASIA-FASD, I = Replay-Attack, M = MSU-MFSD), Table 5,
  HTER % / AUC %:
  | Method | O&C&I→M | O&M&I→C | O&C&M→I | I&C&M→O |
  |---|---|---|---|---|
  | MS-LBP | 29.76 / 78.50 | 54.28 / 44.98 | 50.30 / 51.64 | 50.29 / 49.31 |
  | Binary CNN | 29.25 / 82.87 | 34.88 / 71.94 | 34.47 / 65.88 | 29.61 / 77.54 |
  | IDA | 66.67 / 27.86 | 55.17 / 39.05 | 28.35 / 78.25 | 54.20 / 44.59 |
  | Color Texture | 28.09 / 78.47 | 30.58 / 76.89 | 40.40 / 62.78 | 63.59 / 32.71 |
  | LBP-TOP | 36.90 / 70.80 | 42.60 / 61.05 | 49.45 / 49.54 | 53.15 / 44.09 |
  | Auxiliary (Depth) | 22.72 / 85.88 | 33.52 / 73.15 | 29.14 / 71.69 | 30.17 / 77.61 |
  | MADDG | 17.69 / 88.06 | 24.50 / 84.51 | 22.19 / 84.99 | 27.89 / 80.02 |
  | SSDG-M | 16.67 / 90.47 | 23.11 / 85.45 | 18.21 / 94.61 | 25.17 / 81.83 |
  | SSDG-R | 7.38 / 97.17 | 10.44 / 95.94 | 11.71 / 96.59 | 15.61 / 91.54 |

### References cited through CDCN (bibliographic details from CDCN's reference list)
* George, A., & Marcel, S. (2019). Deep pixel-wise binary supervision for face presentation attack detection.
  *International Conference on Biometrics (ICB)*.
* Jourabloo, A., Liu, Y., & Liu, X. (2018). Face de-spoofing: Anti-spoofing via noise modeling. *ECCV*, 290–306.
* Liu, Y., Jourabloo, A., & Liu, X. (2018). Learning deep models for face anti-spoofing: Binary or auxiliary
  supervision. *CVPR*, 389–398.
* Wang, Z., Zhao, C., Qin, Y., Zhou, Q., & Lei, Z. (2018). Exploiting temporal and depth information for
  multi-frame face anti-spoofing. arXiv:1811.05118.
* Yang, X., Luo, W., Bao, L., Gao, Y., Gong, D., Zheng, S., Li, Z., & Liu, W. (2019). Face anti-spoofing: Model
  matters, so does data. *CVPR*.
* Boulkenafet, Z., Komulainen, J., & Hadid, A. (2016). Face spoofing detection using colour texture analysis.
  *IEEE Transactions on Information Forensics and Security, 11*(8), 1818–1830.
* Boulkenafet, Z., Komulainen, J., & Hadid, A. (2015). Face anti-spoofing based on color texture analysis.
  *IEEE ICIP*, 2636–2640.

## Face recognition

### Deng et al., 2019 — ArcFace (CVPR 2019) — arXiv:1801.07698
Deng, J., Guo, J., Xue, N., & Zafeiriou, S. (2019). ArcFace: Additive angular margin loss for deep face
recognition. In *Proceedings of the IEEE/CVF CVPR* (pp. 4690–4699).
* Verification (%), LResNet100E-IR @ MS1M (Table 7 of arXiv v1): Softmax 99.70 LFW / 91.4 CFP-FP / 95.56 AgeDB-30;
  SphereFace 99.76 / 93.7 / 97.56; CosineFace (m=0.35) 99.80 / 94.4 / 97.91; ArcFace (m=0.4) 99.80 / 94.5 / 98.0;
  **ArcFace (m=0.5) 99.83 / 94.04 / 98.08**.
* VaultTrust uses InsightFace buffalo_l `w600k_r50` (ResNet-50 trained on WebFace600K) — not the same model as the
  paper's ResNet-100/MS1M; cite paper numbers as the method's reference performance only.

## Dataset used in this project
### Timoshenko et al., 2019 — LCC-FASD
Timoshenko, D., Simonchik, K., Shutov, V., Zhelezneva, P., & Grishkin, V. (2019). Large crowdcollected facial
anti-spoofing dataset. In *2019 Computer Science and Information Technologies (CSIT)* (pp. 123–126). IEEE.
https://doi.org/10.1109/CSITechnol.2019.8895208
* Crowd-collected from public videos; a secondary source describes 1,942 real and 16,885 spoof images in the full
  release (we used the development subset: 416 real / 2,590 spoof crops).
* Reference results on LCC_FASD from the open-source "light-weight-face-anti-spoofing" repository (kprokofi,
  GitHub; not peer reviewed; training protocol not stated):
  | Model | AUC | EER % | APCER % | BPCER % | ACER % | Params (M) | GFLOPs |
  |---|---|---|---|---|---|---|---|
  | MobileNetV3-large | 0.921 | 16.13 | 17.26 | 15.40 | 16.33 | 3.02 | 0.15 |
  | AENet | 0.868 | 20.91 | 12.52 | 32.70 | 22.61 | 11.22 | 3.64 |
  | MobileNetV3-large ×0.75 | 0.892 | 19.42 | 28.34 | 12.18 | 20.26 | 1.86 | 0.10 |
  | MobileNetV3-small | 0.889 | 18.70 | 14.79 | 24.60 | 19.69 | 1.00 | 0.04 |
  | MobileNetV3-small ×0.75 | 0.879 | 21.07 | 22.77 | 19.30 | 21.04 | 0.60 | 0.03 |
  Same repo on CelebA-Spoof: MobileNetV3-large AUC 0.998, EER 2.26 %, ACER 3.8 %; AENet AUC 0.999, EER 1.12 %.

## Frequency-domain and handcrafted anti-spoofing
* Li, J., Wang, Y., Tan, T., & Jain, A. K. (2004). Live face detection based on the analysis of Fourier spectra.
  In *Biometric Technology for Human Identification* (Proc. SPIE 5404, pp. 296–303). https://doi.org/10.1117/12.541955
  — high-frequency energy ratio of the face; defeated by large, sharp photos (later surveys).
* Boulkenafet et al. 2015/2016 colour texture (above). LBP / LBP-TOP / spectral cubes / IDA rows in SSDG & CDCN tables.

## Active liveness
* Pan, G., Sun, L., Wu, Z., & Lao, S. (2007). Eyeblink-based anti-spoofing in face recognition from a generic
  webcamera. In *IEEE 11th International Conference on Computer Vision (ICCV)* (pp. 1–8).
  https://doi.org/10.1109/ICCV.2007.4409068 — spontaneous blinks via conditional random fields; photo attacks.
* Kollreider, K., Fronthaler, H., Faraj, M. I., & Bigun, J. (2007). Real-time face detection and motion analysis
  with application in "liveness" assessment. *IEEE Transactions on Information Forensics and Security, 2*(3),
  548–558. https://doi.org/10.1109/TIFS.2007.902037 — lip movement / digit reading.
* Soukupová, T., & Čech, J. (2016). Real-time eye blink detection using facial landmarks. In *21st Computer Vision
  Winter Workshop (CVWW)*, Rimske Toplice, Slovenia. — eye aspect ratio (6 landmarks), SVM/HMM.
* Kartynnik, Y., Ablavatski, A., Grishchenko, I., & Grundmann, M. (2019). Real-time facial surface geometry from
  monocular video on mobile GPUs. arXiv:1907.06724 (CVPR 2019 Workshop on CV for AR/VR). — 468-point mesh,
  100–1000+ FPS on mobile GPUs. (MediaPipe FaceLandmarker adds iris points → 478, plus 52 blendshapes.)

## Explainability in presentation attack detection
* Sequeira, A. F., Gonçalves, T., Silva, W., Pinto, J. R., & Cardoso, J. S. (2021). An exploratory study of
  interpretability for face presentation attack detection. *IET Biometrics, 10*(4), 441–455.
  https://doi.org/10.1049/bme2.12045 — CNN PAD evaluated with APCER/BPCER/EER + Grad-CAM.
* Pan, S., Hoque, S., & Deravi, F. (2022). An attention-guided framework for explainable biometric presentation
  attack detection. *Sensors, 22*(9), 3365. (Grad-CAM saliency + verbal explanations.) [details: PMC9102540]
* Selvaraju, R. R., Cogswell, M., Das, A., Vedantam, R., Parikh, D., & Batra, D. (2017). Grad-CAM: Visual
  explanations from deep networks via gradient-based localization. *ICCV*, 618–626.
* Survey: Yu, Z., Qin, Y., Li, X., Zhao, C., Lei, Z., & Zhao, G. (2023). Deep learning for face anti-spoofing: A
  survey. *IEEE TPAMI, 45*(5), 5609–5631. https://doi.org/10.1109/TPAMI.2022.3215850

## Template protection
* Teoh (Jin), A. B. J., Ngo, D. C. L., & Goh, A. (2004). Biohashing: Two factor authentication featuring
  fingerprint data and tokenised random number. *Pattern Recognition, 37*(11), 2245–2255. — claimed zero EER.
* Kong, A., Cheung, K.-H., Zhang, D., Kamel, M., & You, J. (2006). An analysis of BioHashing and its variants.
  *Pattern Recognition, 39*(7), 1359–1368. https://doi.org/10.1016/j.patcog.2005.10.025 — bibliographic details
  checked 18 Oct 2026 (author's page + indexes); zero-EER claim rests on a hidden assumption (token never stolen).
* Teoh, A. B. J., & Ngo, D. C. L. (2005). FaceHashing (Pattern Recognition Letters). Critiques (Kong et al.;
  "An analysis of BioHashing and its variants", Pattern Recognition) show the zero-EER claim relies on the token
  never being stolen; with a stolen token performance is no better than the raw biometric. → VaultTrust reports
  accuracy with the key known to the matcher (stolen-token scenario) and states irreversibility depends on key secrecy.
* Ratha, N. K., Connell, J. H., & Bolle, R. M. (2001). Enhancing security and privacy in biometrics-based
  authentication systems. *IBM Systems Journal, 40*(3), 614–634. — cancelable biometrics concept.
* ISO/IEC 24745:2022 Information security, cybersecurity and privacy protection — Biometric information
  protection: irreversibility, unlinkability, renewability/revocability (paraphrased; full text not accessed).

## Fractal / chaos
* Sarkar, N., & Chaudhuri, B. B. (1994). An efficient differential box-counting approach to compute fractal
  dimension of image. *IEEE Transactions on Systems, Man, and Cybernetics, 24*(1), 115–120.
  https://doi.org/10.1109/21.259692
* Logistic map: May, R. M. (1976). Simple mathematical models with very complicated dynamics. *Nature, 261*,
  459–467. (well-known; not re-checked)
* Watts, D. J., & Strogatz, S. H. (1998). Collective dynamics of 'small-world' networks. *Nature, 393*, 440–442.
  (well-known; not re-checked)

## OTP, authentication standards and regulation
* RFC 4226 HOTP (M'Raihi et al., 2005); RFC 6238 TOTP (M'Raihi, Machani, Pei, & Rydell, 2011).
* Commission Delegated Regulation (EU) 2018/389 (RTS on strong customer authentication), Article 5 "dynamic
  linking": payer made aware of amount and payee; authentication code specific to amount and payee; any change
  invalidates the code. Recital 4: OTPs acceptable.
* ISO/IEC 30107-3:2017 presentation attack detection — testing and reporting (APCER, BPCER).
* NIST SP 800-63B Digital Identity Guidelines (authentication and lifecycle management).
* India: Digital Personal Data Protection Act, 2023.

## Foundations (well-known; cite as standard references)
He et al. 2016 ResNet (CVPR, 770–778); Cooley & Tukey 1965 FFT (Math. Comp. 19, 297–301); Deng et al. 2020
RetinaFace (CVPR); Johnson & Lindenstrauss 1984 (Contemp. Math. 26, 189–206); Kingma & Ba 2015 Adam;
Loshchilov & Hutter 2019 AdamW (ICLR).

## Added for the IEEE Access related work (checked 21 Oct 2026)
Source of each check in brackets. Claims used in the paper are limited to what is stated here.

### OTP generation
* Lamport, L. (1981). Password authentication with insecure communication. *Communications of the ACM, 24*(11),
  770–772. — hash-chain one-time passwords from a one-way function (basis of S/KEY). [CACM listing, MSR PDF]
* Naik, R., & Singh, U. (2021). Secured 6-digit OTP generation using B-exponential chaotic map. *International
  Journal of Advanced Computer Science and Applications, 12*(12), 786–794. — 6-digit OTP from a B-exponential
  chaotic map; authors claim "120 times higher security" than 4-digit OTPs. [paper PDF, title page + page numbers]
* Aramice, G. A., Issa, R. S., Mustafa, Z. G., & Abdulkareem, H. G. (2026). Enhancement of multi-level mutual
  authentication systems using high-entropy chaotic key generation. *International Journal of Safety and Security
  Engineering, 16*(4), 849–857. https://doi.org/10.18280/ijsse.160412 — logistic map seeded from an RFID tag UID,
  control parameter from the phone-number suffix; 5,000 Monte Carlo cycles near-uniform; SAC/BIC near ideal (IoT
  mutual authentication). [IIETA article page]
* No prior OTP based on a random walk over a public graph was found (web searches 21 Oct 2026; closest: patents,
  automaton-based OTP, graphical "Passblot").

### Face authentication for payments / liveness protocols
* Li, Y., Li, Y., Yan, Q., Kong, H., & Deng, R. H. (2015). Seeing your face is not enough: An inertial sensor-based
  liveness detection for face authentication. *Proc. ACM CCS 2015*, 1558–1569. https://doi.org/10.1145/2810103.2813612
  [dblp + SMU repository, via search]
* Tang, D., Zhou, Z., Zhang, Y., & Zhang, K. (2018). Face Flashing: A secure liveness detection protocol based on
  light reflections. *NDSS 2018* (arXiv:1801.01949). — random screen flashes, reflected light, timing check;
  overall accuracy 98.8 %, worst case 97.3 %. [arXiv abstract; NDSS slides / CUHK news for venue]
* Xu, Y., Price, T., Frahm, J.-M., & Monrose, F. (2016). Virtual U: Defeating face liveness detection by building
  virtual models from your public photos. *25th USENIX Security Symposium*. — 3-D models from a handful of social-media
  photos, animated in VR, undermine "several face authentication solutions" incl. motion-based and liveness
  detectors (abstract gives no counts; pages not verified). [USENIX presentation page]
* Srivatsan, K., Naseer, M., & Nandakumar, K. (2023). FLIP: Cross-domain face anti-spoofing with language guidance.
  *ICCV 2023*, 19685–19696. https://doi.org/10.1109/ICCV51070.2023.01803 — CLIP-initialised ViTs + language-aligned
  features improve cross-domain FAS. [mlanthology BibTeX; one repository lists pages 19628–19639]
* Hussain B., M. I., & Rafi, M. (2023). Online financial transactions in India: A study of its significance, frauds
  and security models to counter frauds. *International Journal of Intelligent Engineering and Systems, 16*(3),
  455–469. https://doi.org/10.22266/ijies2023.0630.36 — 3-level scheme (password, OTP, face recognition or OTP at
  level 3); Viola–Jones + PCA face recognition, 98.20 % on VTU-BEC-DB; 200 participants; no liveness, template
  protection or transaction binding mentioned. [paper PDF, full text searched]
* CEN/TS 18099:2024, *Biometric data injection attack detection* (CEN/TC 224). Presentation attacks excluded (ISO/IEC
  30107). [standards stores]
