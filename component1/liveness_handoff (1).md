# Liveness Component — Team Handoff

## Purpose

This document is for the teammate integrating the liveness component into the main Face Anti-Spoofing project.

The original project/implementation brief already defines the overall architecture:

1. Spatial + Frequency-Domain Analysis
2. Passive + Active Liveness Detection
3. Explainable AI (XAI)

The liveness work described here is my component. The teammate should integrate it with the spatial/frequency FAS component and the final XAI/decision-fusion layer.

The brief places liveness after the passive FAS stage and before decision fusion:

```text
Camera
  ↓
Face Detection
  ↓
Face Preprocessing
  ↓
Spatial + Frequency Analysis
  ↓
Feature Fusion
  ↓
Passive FAS Score
  ↓
Active Liveness
  ↓
Decision Fusion
  ↓
REAL / SPOOF
  ↓
Face Recognition if REAL
```

---

# 1. Files I Should Send

Because the teammate already has the **original project**, I do NOT need to send the entire original project again.

## Required file

### `liveness.py`

This is the main file containing my liveness implementation.

Send the updated version of:

```text
liveness.py
```

It contains the liveness-specific logic and should replace the corresponding original liveness module when integrating.

---

# 2. Dependency Information

The liveness implementation uses the project's existing computer-vision dependencies, particularly MediaPipe/OpenCV-related functionality.

The important environment/dependency change for the intended continuous-camera implementation is:

```text
streamlit-webrtc
```

If the teammate is already maintaining the project's `requirements.txt`, they can add this dependency to their existing file instead of receiving a separate requirements file.

Therefore, I do not need to send a complete replacement `requirements.txt` unless my local requirements file contains additional changes.

---

# 3. Do I Need to Send `app.py`?

### No — not automatically.

The teammate already has the original project and is responsible for integrating the components.

Only send a modified `app.py` if I have actually changed the application's integration code.

The liveness module itself is the important handoff.

The original use of:

```python
st.camera_input()
```

captures individual images. That is not sufficient for the intended temporal liveness sequence.

For the final system, the teammate should integrate the liveness component with a continuous camera/video-frame pipeline.

The intended flow is:

```text
Continuous Camera Frames
        ↓
Face Detection / Preprocessing
        ↓
Passive FAS
        ↓
Liveness Sequence
        ↓
Decision Fusion
```

---

# 4. What `liveness.py` Provides

The updated liveness module contains several layers of checks.

## A. Image / face validation

The module checks things such as:

- brightness
- sharpness
- exactly one detected face
- face size/area
- facial landmark availability

These are supporting checks, not a complete anti-spoofing classifier.

---

## B. Eye Aspect Ratio (EAR)

The module calculates Eye Aspect Ratio from facial landmarks.

This is used for blink detection.

The intended temporal pattern is:

```text
Eyes Open
     ↓
Eyes Closed / Closing
     ↓
Eyes Open Again
```

The important point is that the system should observe the transition rather than simply inspect whether one final image contains closed eyes.

---

## C. Head movement

Facial landmark/nose movement is used as a lightweight head-movement signal.

The intended sequence is:

```text
CENTER
   ↓
TURNING
   ↓
TARGET DIRECTION
```

For example:

```text
Instruction: Turn left

Initial:   CENTER
During:    TURNING
Final:     LEFT
```

---

## D. Neutral baseline

Before evaluating an active challenge, the module can validate a baseline frame.

The baseline is intended to represent a normal starting state rather than accepting an arbitrary final pose as the starting point.

---

## E. Sequence-based challenge verification

The module includes sequence-based logic intended for multiple consecutive frames.

Conceptually:

```text
Frame 1
Frame 2
Frame 3
...
Frame N
   ↓
Temporal analysis
   ↓
Challenge PASS / FAIL
```

This is the important part for addressing the weakness of checking two unrelated still photographs.

---

# 5. Important Integration Requirement

The sequence-based liveness code only becomes meaningful if the teammate feeds it **consecutive frames from the camera**.

Do NOT integrate it like this:

```text
Photo A
   ↓
liveness check

Photo B
   ↓
liveness check
```

That can allow an attacker to provide different photographs showing different poses.

The intended integration is:

```text
Live camera
    ↓
Frame 1
    ↓
Frame 2
    ↓
Frame 3
    ↓
Frame 4
    ↓
...
    ↓
Temporal liveness verification
```

The implementation brief itself specifies that active liveness should capture a short video and verify the requested action.

---

# 6. How My Component Fits With the Teammate's Component

My liveness module should NOT replace the spatial/frequency FAS model.

Instead:

```text
             CAMERA
                ↓
         FACE PREPROCESSING
                ↓
      ┌─────────────────────┐
      │   PASSIVE FAS       │
      │                     │
      │ Spatial CNN         │
      │       +             │
      │ FFT Frequency       │
      └──────────┬──────────┘
                 ↓
          Passive FAS Score
                 +
                 ↓
      ┌─────────────────────┐
      │   ACTIVE LIVENESS   │
      │                     │
      │ Random Challenge    │
      │ Blink / Head Turn   │
      └──────────┬──────────┘
                 ↓
          DECISION FUSION
                 ↓
            REAL / SPOOF
```

The implementation brief specifically proposes combining passive/FAS and active-liveness signals through decision fusion.

---

# 7. Expected Interface for Integration

The teammate should treat liveness as a separate module that produces a result which can be consumed by the final decision-fusion layer.

Conceptually:

```python
liveness_result = run_liveness(...)
```

The result should provide enough information for the integration layer to determine:

```text
PASS / FAIL
```

and preferably supporting evidence/confidence.

The final decision should then combine this with the passive FAS result.

Example concept:

```text
passive_fas_result = REAL/SPOOF + score
active_liveness_result = PASS/FAIL + confidence

                ↓

          Decision Fusion

                ↓

          FINAL REAL/SPOOF
```

The exact fusion formula is part of the overall integration and should be decided after the spatial/frequency component is available.

---

# 8. What Should NOT Be Claimed

The liveness component alone should NOT be described as a guaranteed photo/deepfake detector.

For example, it should not be claimed that:

```text
"Blink detection guarantees that the user is real."
```

or:

```text
"Head movement guarantees that the input is live."
```

The implementation brief explicitly states that active liveness is an additional security signal because sophisticated replay/deepfake attacks may reproduce actions.

The complete system is intended to obtain stronger protection by combining:

```text
Spatial
+
Frequency
+
Passive Liveness
+
Active Liveness
+
Decision Fusion
```

---

# 9. Testing the Liveness Component

Before integration, the teammate and I should test at least:

### Test 1 — Genuine user

```text
Real person
+
requested blink/head movement
→ PASS
```

### Test 2 — Static photograph

```text
Single photograph
→ should fail temporal challenge
```

### Test 3 — Different static photographs

```text
Photo A: normal
Photo B: head turned
→ should not be treated as a genuine continuous movement sequence
```

### Test 4 — Pre-recorded video

```text
Replay video
→ test separately
```

A replayed video can potentially reproduce temporal actions, which is why the spatial/frequency FAS component is also required.

---

# 10. Files/Changes Summary

| Item | Send to teammate? | Reason |
|---|---|---|
| `liveness.py` | YES | Main component implementation |
| `requirements.txt` | Usually NO | Teammate can add `streamlit-webrtc` to their existing requirements |
| `app.py` | Only if modified | Integration should be handled with the main project |
| `mediapipe_face.py` | NO, unless modified | Already exists in the original project |
| `arcface_model.py` | NO | Existing face-recognition component |
| `.env` | NO | Contains local/private configuration |
| `.env.example` | Only if changed | Configuration template only |
| Original ZIP | NO | Teammate already has the original project |
| This handoff `.md` | YES | Explains exactly what the liveness component does and how to integrate it |

---

# 11. Minimal Handoff Package

Since the teammate already has the original project, the cleanest handoff is:

```text
Liveness_Handoff/
│
├── liveness.py
└── liveness_handoff.md
```

Optionally:

```text
└── requirements_additions.txt
```

containing:

```text
streamlit-webrtc
```

if the teammate wants the dependency separately.

---

# 12. Final Integration Responsibility

### My responsibility

Provide:

```text
liveness.py
```

with:

- EAR-based blink detection
- landmark-based head movement
- baseline validation
- sequence-based challenge logic
- supporting face/image checks

### Teammate's integration responsibility

Integrate it with:

```text
Spatial CNN
      +
FFT Frequency Branch
      ↓
Passive FAS
      +
Active Liveness
      ↓
Decision Fusion
      ↓
XAI
      ↓
Face Recognition
```

The original implementation brief defines the overall architecture as a system where spatial/frequency analysis produces the passive FAS score, active liveness provides another security signal, and the signals are fused before the REAL/SPOOF decision.

---

## Bottom Line

**The main file I need to hand over is `liveness.py`.**

Because the teammate already has the original project and the original implementation brief, sending the entire project again would create unnecessary duplication.

The most useful handoff is:

```text
liveness.py
      +
liveness_handoff.md
      +
(optional) streamlit-webrtc dependency note
```

The teammate can then integrate this component into their spatial/frequency FAS implementation and the final decision-fusion pipeline.
