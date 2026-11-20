# Final Report and Slides — Plan (13 Oct 2026)

Deliverables, in order: (1) `docs/PROJECT_RECORD.md` ✅ done; (2) evaluation suite (`evaluation/`);
(3) literature research; (4) final report `.docx` (≥ 70 pages chapter 1 → references); (5) 25-slide
deck (after the report). Source of facts: `docs/PROJECT_RECORD.md`.

## Open decisions (ask the user; defaults in brackets)
1. Title [registered title + subtitle: "Design of an Authentication System Using Fractal Geometry with
   Graph-Based Random-Walk OTP Generation — VaultTrust: Explainable Face Anti-Spoofing with
   Transaction-Bound OTP for Step-Up Authentication"]
2. Report type [one team report, "we", all three names]
3. Evaluation data [existing data only; optional 30-min team test session later]
4. Details [guide Mohanraj G, Assistant Professor Senior Grade 2; HoD Dr. Arivuselvan K; Dean Dr. Daphne
   Lopez; IT Project Coordinator Dr. Suganya P; SCORE Project Coordinator Dr. Karthikeyan P; period
   06.07.2026–03.11.2026; submitted November 2026]

## Template rules (`C:\Users\nilay\Downloads\Project-1 Report final.docx`)
* A4; margins left 1.5″, right/top/bottom 1″. Times New Roman 12, justified, 1.5 line spacing.
* Chapter heading 14 pt, CAPS, bold ("CHAPTER 1" / "INTRODUCTION"); sub-headings 12 pt, no caps.
* First paragraph of each chapter not indented; following paragraphs indented one tab.
* Bullets: Word bullet library symbols (✓ or ●), not numbering; numbering only for types/ordered lists.
* Figures centred, caption **below**: "Fig. 2.4 Title In Title Case", TNR 10 pt. Tables: caption **above**:
  "Table 6.1 Title", TNR 10 pt. Equations numbered "(5.2)", cited "Eqn. 5.2".
* Page numbers: roman from cover to Symbols and Notations (cover number hidden; visible from ii);
  arabic from Chapter 1 to References; none in Appendices.
* References in APA format. Appendices: sample code, screenshots, manuals.
* Front matter: Cover (VIT logo = template `word/media/image9.png`), inner title page, Declaration,
  Certificate (guide signature, internal/external examiner, HoD), Acknowledgement, Executive Summary
  (≤ 200 words), Contents, List of Figures, List of Tables, List of Abbreviations, Symbols and Notations.
* Fixed chapters: 1 Introduction (Objective, Motivation, Background), 2 Project Description and Goals,
  3 Technical Specification, 8 Summary, 9 References; chapters 4–7 may be adapted.
* Build approach: python-docx on a copy of the template (keeps styles); Word 16 COM to update
  TOC/lists of figures/tables and to export PDF for visual checks. (No pandoc/LibreOffice/Poppler here.)

## Chapter outline
1. Introduction — objective, motivation, background, problem definition, scope, organisation
2. Project Description and Goals — description, literature survey (≥ 20 works, comparison table),
   research gaps, goals/measurable objectives, contributions
3. Technical Specification — hardware/software, requirements (functional/non-functional), datasets,
   models, background concepts (CNN/ResNet, FFT, Grad-CAM, ArcFace, MediaPipe, cancelable biometrics,
   HMAC/TOTP, random walks, evaluation metrics)
4. Design Approach and Details — architecture, module design, UML (use case, sequence, activity, class),
   data design, codes and standards (ISO/IEC 30107-3, ISO/IEC 24745, RFC 4226/6238, PSD2 RTS,
   NIST SP 800-63B, India DPDP Act 2023), threat model, constraints/alternatives/trade-offs
5. Schedule, Tasks and Milestones — Gantt, team task split, milestones
6. Project Demonstration — implementation walkthrough with screenshots (extract from
   `recordings/2026-10-10 22-08-25.mp4`), attack demonstrations
7. Results and Discussion — metrics, unit-wise and combination study, latency, comparative study,
   discussion, limitations, cost analysis
8. Summary — conclusion, future work
9. References (APA) · Appendix A code samples · Appendix B user manual / test inventory

## Evaluation suite design (`evaluation/`)
Components: **A** = ArcFace face match, **L** = active liveness (with continuity), **F** = passive
spatial-frequency anti-spoofing ("FFT" component; also report spatial-only and frequency-only).
Combinations: A, L, F, A+L, A+F, L+F, A+L+F (decision = AND of members).
* Attempt categories (ground truth): genuine live (accept); impostor live; photo/print; replay video;
  swap (photo then live person).
* Sources: LCC-FASD test subjects; Rwitankar videos (windows); Nilay labelled captures; screen
  recording; simulated static/tilted photo sequences from spoof frames (state clearly as simulated).
* Metrics: accuracy, precision, recall, F1, APCER (per attack), BPCER, ACER, FAR/FRR, AUC/EER,
  confusion matrices, latency per component and per combination.
* Component-level studies: ArcFace verification (TAR/FAR/EER, raw vs protected template);
  anti-spoofing ablation (retrain spatial-only/frequency-only/fused with the v5 recipe, saving each
  model); liveness on video (genuine pass rate, replay with blink-only vs random challenges, static
  photo, swap).
* OTP: code uniformity (chi-square), collisions, brute-force odds, avalanche, latency, Python↔JS;
  template: TAR/FAR raw vs protected, unlinkability, revocation.
* Figures: grouped bar chart of the 7 combinations, per-attack APCER bars, latency pie/stacked bar,
  ROC curves, confusion matrices, score distributions, Grad-CAM examples, architecture and UML
  diagrams, Gantt chart, UI screenshots.

## Literature research
Verified published numbers (no figures from memory): face anti-spoofing (CDCN, FAS-SGTD, SSDG,
DeepPixBiS, LCC-FASD baselines, CelebA-Spoof), active liveness / challenge-response, ArcFace and face
recognition benchmarks (LFW, IJB), cancelable biometrics (BioHashing, random projection), OTP
(HOTP/TOTP RFCs, chaotic/graph PRNGs), multi-factor and step-up authentication (PSD2 SCA).
Comparison tables: method, dataset, metric, result, and how VaultTrust differs.
