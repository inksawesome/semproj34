# Implementation Plan: Face Anti-Spoofing (Components 3 & 4)

## Goal Description
The objective is to implement **Component 3 (Active Liveness Detection)** and **Component 4 (Explainable AI)** for the Face Anti-Spoofing system. 
In alignment with the project brief's staged development strategy (specifically phases 3 and 4), this plan breaks down the tasks into granular implementation phases.

## Phase-Wise Implementation Breakdown

### Phase 3: Active Liveness (Component 3)
*Focus: Implement interactive challenges to thwart static replays and deepfakes.*
- **Phase 3.1: Core Verifier Logic**
  - Implement EAR logic for blink detection.
  - Implement MAR logic for smile detection.
  - Implement Head Pose calculation (Yaw/Pitch) for head movement.
- **Phase 3.2: Challenge & Sequence Verification**
  - Create the random challenge generator.
  - Implement the temporal sequence verifier (evaluating a buffer of frames to confirm the action).
  - Test with MediaPipe landmarks.

### Phase 4: Explainability (Component 4)
*Focus: Expose decision-making evidence for transparency.*
- **Phase 4.1: Spatial Explainability**
  - Implement Grad-CAM hooks targeting the final convolutional layer of the spatial model (ResNet-18).
  - Generate normalized heatmaps.
- **Phase 4.2: Frequency Explainability**
  - Implement 2D FFT extraction from input images.
  - Generate colorized magnitude spectrums to visualize high-frequency anomalies.
- **Phase 4.3: Decision Fusion & UI Output**
  - Create the Explanation Aggregator to combine passive spatial/frequency scores with the active liveness result.
  - Format the final output dict (verdict, confidence, reasoning) for the Gradio UI.

## User Review Required
> [!IMPORTANT]
> **Library Choices**: I am proposing the use of `mediapipe` for facial landmark extraction (essential for blink, smile, and head pose detection). Please confirm if this aligns with the rest of the team's tech stack.
> **Integration Interfaces**: Since you will be integrating this with Components 1 & 2 later, please review the proposed function signatures in the Proposed Changes section to ensure they match what the team expects.

## Open Questions
> [!WARNING]
> 1. Do we have a specific UI framework (e.g., PyQt, Flask, Gradio) in mind for displaying the Final Explainable Output and the Active Challenge prompts? 
> 2. For the Grad-CAM implementation, do we know yet which specific model architecture (ResNet-18 vs. EfficientNet-B0) the spatial branch will use? (Grad-CAM needs to hook into the final convolutional layer, which varies by model).

## Proposed Changes

---

### Liveness Component (Component 3)
We will create the challenge generator and the specific verification modules under the `liveness/` directory.

#### [NEW] `liveness/challenge.py`
```python
import random

class ChallengeGenerator:
    def __init__(self):
        self.challenges = ["TURN_LEFT", "TURN_RIGHT", "BLINK", "SMILE", "LOOK_UP"]
    
    def get_random_challenge(self) -> str:
        return random.choice(self.challenges)
```

#### [NEW] `liveness/blink.py`
```python
def calculate_ear(eye_landmarks):
    # Computes Eye Aspect Ratio (EAR) using standard formulas
    pass

def verify_blink(landmark_sequence) -> tuple[bool, float]:
    # Returns (Passed, Confidence) based on EAR drop and recovery
    pass
```

#### [NEW] `liveness/head_pose.py`
```python
def estimate_head_pose(landmarks) -> tuple[float, float, float]:
    # Returns (Yaw, Pitch, Roll)
    pass

def verify_head_movement(landmark_sequence, challenge_type) -> tuple[bool, float]:
    # Verifies if yaw/pitch changes match the challenge (TURN_LEFT/RIGHT/LOOK_UP)
    pass
```

#### [NEW] `liveness/smile.py`
```python
def calculate_mar(mouth_landmarks):
    # Computes Mouth Aspect Ratio (MAR)
    pass

def verify_smile(landmark_sequence) -> tuple[bool, float]:
    # Returns (Passed, Confidence) based on MAR expansion
    pass
```

---

### Explainability Component (Component 4)
We will implement the evidence generation and aggregation modules under the `explainability/` directory.

#### [NEW] `explainability/gradcam.py`
```python
class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        # Setup forward and backward hooks
        
    def generate_heatmap(self, input_tensor, target_class=None):
        # Generates and returns the heatmap overlay
        pass
```

#### [NEW] `explainability/frequency_explanation.py`
```python
def visualize_frequency_spectrum(image):
    # Computes 2D FFT and returns a normalized magnitude spectrum image
    pass
```

#### [NEW] `explainability/explanation.py`
```python
def generate_explanation(spatial_score, freq_score, active_pass, image, heatmap, spectrum):
    """
    Aggregates all signals into a final readable output.
    Returns a dictionary containing:
    - Result (REAL/SPOOF)
    - Confidence
    - Evidence checks
    - Textual Reasoning
    """
    pass
```

---

## Verification Plan

### Automated Tests
1. **Liveness Tests**: 
   - `python -m pytest tests/test_liveness.py` (Will test EAR calculations with mock landmarks, and verify challenge generator randomness).
2. **Explainability Tests**: 
   - `python -m pytest tests/test_explainability.py` (Will test Grad-CAM heatmap generation dimensions and FFT spectrum extraction).

### Manual Verification
1. Run a sample script `python -m liveness.demo_active_liveness` (to be created) which opens the webcam, prompts a challenge, and prints PASS/FAIL to the console.
2. Run `python -m explainability.demo_xai` with a sample dummy image to verify that the Grad-CAM heatmap and FFT spectrum images are generated and saved correctly.
3. Review the formatting of the JSON/Dict output from `generate_explanation()` to ensure it contains all required evidence fields for the UI.
