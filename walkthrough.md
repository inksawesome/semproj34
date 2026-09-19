# Walkthrough: Components 3 & 4 Implementation

## Changes Made
I have implemented the base modules for **Component 3 (Active Liveness)** and **Component 4 (Explainable AI)** under the `anti_spoofing/` directory.

### Liveness Module
- `anti_spoofing/liveness/challenge.py`: A `ChallengeGenerator` that provides random prompts (e.g., TURN_LEFT, BLINK, SMILE) for the user to follow.
- `anti_spoofing/liveness/blink.py`: Uses Eye Aspect Ratio (EAR) to detect and verify blinks across a sequence of frames.
- `anti_spoofing/liveness/head_pose.py`: Verifies left/right/up head movements by estimating Yaw and Pitch (designed to work alongside `mediapipe` landmarks).
- `anti_spoofing/liveness/smile.py`: Uses Mouth Aspect Ratio (MAR) to verify a smile action.

### Explainability Module
- `anti_spoofing/explainability/gradcam.py`: A hook-based implementation of Grad-CAM that attaches to the final convolutional layer of a PyTorch model (like ResNet-18) and extracts a spatial heatmap.
- `anti_spoofing/explainability/frequency_explanation.py`: Computes the 2D FFT of the input image and generates a JET-colorized magnitude spectrum to visualize frequency artifacts.
- `anti_spoofing/explainability/explanation.py`: Aggregates the signals from the passive model and active liveness modules to generate a final, readable dictionary output comprising the result, confidence, evidence array, and reasoned conclusion.

## Next Steps for Integration
1. **Model Selection**: You mentioned using ResNet-18. When setting up the `GradCAM` object, you will pass your model and the target layer (typically `model.layer4[-1]`).
2. **Landmark Extraction**: You can use `mediapipe.solutions.face_mesh` to extract the 3D landmark coordinates to feed into the liveness verify functions.
3. **UI implementation**: As discussed, you can use Gradio (or an alternative of your choice) to build the UI wrapper that calls `challenge.py` to prompt the user and `explanation.py` to display the final result.

The core logic is now in place and ready to be connected to the team's broader pipeline!
