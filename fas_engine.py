"""
Passive anti-spoofing (Components 1+2) and its explanation (Component 4).

* Scores several clean frames from the liveness calibration phase and takes
  the median - one blurry frame can no longer decide the outcome.
* Loads the retrained model (models/fas_v2.pth) and its calibrated
  threshold if present, else falls back to the original fas_spatial_freq.pth.
* explain() produces the evidence actually used by the model:
    - Grad-CAM on the last conv block of BOTH branches (layer4, 7x7),
      computed on the exact tensors that were classified;
    - branch attribution: gradient x activation on the fused 1024-D vector,
      i.e. how much the spatial vs frequency features pushed towards REAL;
    - radial frequency profile and high-frequency energy vs genuine faces;
    - fractal dimension of skin texture vs genuine faces.
"""

import json
import os
import threading

import cv2
import numpy as np
import torch
from torchvision import transforms

from explainability.fractal import fractal_dimension
from explainability.frequency_explanation import (high_frequency_ratio, radial_profile,
                                                  visualize_frequency_spectrum)
from frequency_transform import extract_fft_spectrum
from mediapipe_face import detect_and_crop_face
from spatial_frequency_model import SpatialFrequencyFAS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_V2 = os.path.join(BASE_DIR, "models", "fas_v2.pth")
MODEL_V1 = os.path.join(BASE_DIR, "fas_spatial_freq.pth")
CALIBRATION = os.path.join(BASE_DIR, "models", "fas_calibration.json")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# Keep two cores free so the live camera thread is not starved during a verification.
torch.set_num_threads(max(1, (os.cpu_count() or 4) - 2))

_spatial_tf = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

_model = None
_info = None
_lock = threading.Lock()


def _load():
    global _model, _info
    with _lock:
        if _model is None:
            model = SpatialFrequencyFAS(pretrained=False)
            path = MODEL_V2 if os.path.exists(MODEL_V2) else MODEL_V1
            model.load_state_dict(torch.load(path, map_location=DEVICE))
            model.to(DEVICE).eval()
            info = {"model_path": os.path.basename(path), "threshold": 0.5}
            if os.path.exists(CALIBRATION):
                with open(CALIBRATION) as f:
                    info.update(json.load(f))
            _model, _info = model, info
    return _model, _info


OPERATING_POINT = os.path.join(BASE_DIR, "models", "operating_point.json")


def _threshold(info) -> float:
    """Calibrated threshold, unless an operator chose another operating point in the Model Lab."""
    if os.path.exists(OPERATING_POINT):
        with open(OPERATING_POINT) as f:
            return float(json.load(f)["threshold"])
    return float(info["threshold"])


def set_operating_point(threshold: float | None):
    if threshold is None:
        if os.path.exists(OPERATING_POINT):
            os.remove(OPERATING_POINT)
        return
    os.makedirs(os.path.dirname(OPERATING_POINT), exist_ok=True)
    with open(OPERATING_POINT, "w") as f:
        json.dump({"threshold": round(float(threshold), 3)}, f)


POLICY = os.path.join(BASE_DIR, "models", "policy.json")


def fas_enforced() -> bool:
    """Decision policy: 'enforce' (default) blocks on a low anti-spoofing score; 'advisory' only reports it."""
    if os.path.exists(POLICY):
        with open(POLICY) as f:
            return json.load(f).get("fas_mode", "enforce") == "enforce"
    return True


def set_fas_enforced(enforced: bool):
    os.makedirs(os.path.dirname(POLICY), exist_ok=True)
    with open(POLICY, "w") as f:
        json.dump({"fas_mode": "enforce" if enforced else "advisory"}, f)


def model_info() -> dict:
    info = dict(_load()[1])
    info["calibrated_threshold"] = info["threshold"]
    info["threshold"] = _threshold(info)
    return info


def preprocess(face_rgb: np.ndarray):
    xs = _spatial_tf(face_rgb).unsqueeze(0)
    xf = extract_fft_spectrum(face_rgb, target_size=(224, 224))
    return xs.to(DEVICE), xf.to(DEVICE)


def crop(frame_rgb: np.ndarray):
    face, _ = detect_and_crop_face(frame_rgb)
    return face


def score_crops(crops):
    """REAL probability for each face crop (single batched forward pass)."""
    model, _ = _load()
    if not crops:
        return np.array([])
    batch = [preprocess(c) for c in crops]
    xs = torch.cat([b[0] for b in batch])
    xf = torch.cat([b[1] for b in batch])
    with torch.no_grad():
        probs = torch.softmax(model(xs, xf), dim=1)[:, 1]
    return probs.cpu().numpy()


def assess_frames(frames_rgb):
    """
    Passive decision over several frames.
    Returns dict(real_prob, per_frame, is_real, threshold, best_crop).
    """
    info = model_info()
    crops = [c for c in (crop(f) for f in frames_rgb) if c is not None and c.size > 0]
    if not crops:
        return {"real_prob": 0.0, "per_frame": [], "is_real": False,
                "threshold": info["threshold"], "best_crop": None, "error": "No face found in frames"}
    probs = score_crops(crops)
    median = float(np.median(probs))
    best = crops[int(np.argmin(np.abs(probs - median)))]
    return {"real_prob": median, "per_frame": [float(p) for p in probs],
            "is_real": median >= info["threshold"], "threshold": info["threshold"], "best_crop": best}


# ------------------------------------------------------------------ explanation

def _overlay(face_rgb, cam, alpha=0.45):
    face = cv2.resize(face_rgb, (224, 224))
    heat = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
    heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
    return cv2.addWeighted(face, 1 - alpha, heat, alpha, 0)


def _cam(acts, grads):
    weights = grads.mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((weights * acts).sum(dim=1))[0].detach().cpu().numpy()
    cam = cv2.resize(cam, (224, 224), interpolation=cv2.INTER_CUBIC)
    return cam / cam.max() if cam.max() > 0 else cam


def explain(face_rgb: np.ndarray) -> dict:
    model, _ = _load()
    info = model_info()
    xs, xf = preprocess(face_rgb)

    store = {}
    layer_s, layer_f = model.spatial_encoder[-2], model.freq_encoder[-2]   # ResNet layer4 (7x7)
    def keep(name):
        def hook(module, inputs, out):
            store["a" + name] = out
            out.register_hook(lambda g: store.__setitem__("g" + name, g))
        return hook

    hooks = [layer_s.register_forward_hook(keep("s")), layer_f.register_forward_hook(keep("f"))]
    try:
        with torch.enable_grad():
            f_s = torch.flatten(model.spatial_encoder(xs), 1)
            f_f = torch.flatten(model.freq_encoder(xf), 1)
            fused = torch.cat((f_s, f_f), dim=1)
            fused.retain_grad()
            logits = model.classifier(fused)
            prob_real = torch.softmax(logits, dim=1)[0, 1].item()
            predicted = int(prob_real >= info["threshold"])
            model.zero_grad()
            logits[0, predicted].backward(retain_graph=True)
            cam_s = _cam(store["as"], store["gs"])
            cam_f = _cam(store["af"], store["gf"])

            # branch attribution towards REAL: d(logit_real - logit_spoof) x activation
            model.zero_grad()
            fused.grad = None
            (logits[0, 1] - logits[0, 0]).backward()
            contrib = (fused.grad * fused)[0].detach().cpu().numpy()
    finally:
        for h in hooks:
            h.remove()

    spectrum = visualize_frequency_spectrum(face_rgb)
    freqs, profile = radial_profile(face_rgb)
    return {
        "prob_real": prob_real,
        "predicted": "REAL" if predicted else "SPOOF",
        "gradcam_spatial": _overlay(face_rgb, cam_s),
        "gradcam_freq": cv2.addWeighted(spectrum, 0.55,
                                        cv2.cvtColor(cv2.applyColorMap(np.uint8(255 * cam_f), cv2.COLORMAP_JET),
                                                     cv2.COLOR_BGR2RGB), 0.45, 0),
        "spectrum": spectrum,
        "spatial_evidence": float(contrib[:512].sum()),
        "freq_evidence": float(contrib[512:].sum()),
        "profile_freqs": freqs.tolist(),
        "profile": profile.tolist(),
        "profile_ref": info.get("profile_ref"),
        "hf_ratio": high_frequency_ratio(face_rgb),
        "hf_ref": info.get("hf_ref"),
        "fractal_dim": fractal_dimension(face_rgb),
        "fd_ref": info.get("fd_ref"),
    }
