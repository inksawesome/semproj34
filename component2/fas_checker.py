import os
import cv2
import numpy as np
import torch
from torchvision import transforms
from frequency_transform import extract_fft_spectrum
from spatial_frequency_model import SpatialFrequencyFAS

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load model structure ready for future trained weights
model = SpatialFrequencyFAS(pretrained=False)
model_path = "fas_spatial_freq.pth"
if os.path.exists(model_path):
    try:
        model.load_state_dict(torch.load(model_path, map_location=DEVICE))
    except Exception:
        pass
model.to(DEVICE)
model.eval()

def analyze_facial_liveness(face_crop: np.ndarray) -> float:
    """
    Analyzes physical biometric cues on the central face region:
    - Isolates inner face (avoids shirt/hair/background artifacts)
    - Distinguishes 3D face gradient depth from flat paper / digital screen grids
    - Frequency decay curve via 2D-FFT
    """
    h, w, _ = face_crop.shape
    if h < 40 or w < 40:
        return 0.0

    # 1. Crop to central 60% of face (excludes clothing, background, and hair)
    y1, y2 = int(h * 0.20), int(h * 0.80)
    x1, x2 = int(w * 0.20), int(w * 0.80)
    inner_face = face_crop[y1:y2, x1:x2]
    
    gray = cv2.cvtColor(inner_face, cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, (160, 160))

    # ----------------------------------------------------
    # 2. 2D Fast Fourier Transform (FFT) Frequency Decay
    # ----------------------------------------------------
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    mag = np.abs(fshift)

    rows, cols = gray.shape
    crow, ccol = rows // 2, cols // 2
    total_energy = np.sum(mag) + 1e-8

    # Low frequency ring (facial contour / large shapes)
    mask_low = np.zeros((rows, cols), np.uint8)
    cv2.circle(mask_low, (ccol, crow), 15, 1, -1)
    low_ratio = float(np.sum(mag * mask_low) / total_energy)

    # High frequency ring (screen moiré, printed dots, paper grain)
    mask_high = np.ones((rows, cols), np.uint8)
    cv2.circle(mask_high, (ccol, crow), 45, 0, -1)
    high_ratio = float(np.sum(mag * mask_high) / total_energy)

    # ----------------------------------------------------
    # 3. Micro-Texture Depth & Edge Contrast
    # ----------------------------------------------------
    # Real 3D faces exhibit smooth multi-directional gradients.
    # Replays through a camera have exaggerated edges or synthetic flat planes.
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    edge_gradient = np.mean(np.sqrt(sobelx**2 + sobely**2))

    # ----------------------------------------------------
    # 4. Color Dispersion in Skin Tone
    # ----------------------------------------------------
    ycrcb = cv2.cvtColor(inner_face, cv2.COLOR_RGB2YCrCb)
    cr_std = float(np.std(ycrcb[:, :, 1]))
    cb_std = float(np.std(ycrcb[:, :, 2]))
    skin_dispersion = (cr_std + cb_std) / 2.0

    # ----------------------------------------------------
    # Scoring Calibration
    # ----------------------------------------------------
    score = 0.82

    # High frequency anomaly:
    # Phone displays and photo prints produce either excessive high frequencies
    # (> 0.16) due to pixel grids/halftone dots, or unnaturally low (< 0.02) from blur
    if high_ratio > 0.16:
        score -= 0.35
    elif high_ratio < 0.02:
        score -= 0.25

    # Screen / paper attack color flattening penalty
    if skin_dispersion < 4.0:
        score -= 0.30
    elif skin_dispersion < 5.5:
        score -= 0.15

    # Gradient edge anomaly
    if edge_gradient < 4.0:
        # Heavily washed out / blurry photo
        score -= 0.20
    elif edge_gradient > 45.0:
        # Unnatural screen rastering / sharp paper border
        score -= 0.25

    return max(0.0, min(score, 1.0))

def check_liveness(face_crop: np.ndarray, threshold=0.50):
    """
    Evaluates face crop for spoof attacks.
    Returns: (is_real: bool, real_prob: float)
    """
    if face_crop is None or face_crop.size == 0:
        return False, 0.0

    real_prob = analyze_facial_liveness(face_crop)
    is_real = real_prob >= threshold
    return is_real, real_prob