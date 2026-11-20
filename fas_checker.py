import os
import cv2
import numpy as np
import torch
from torchvision import transforms
from frequency_transform import extract_fft_spectrum
from spatial_frequency_model import SpatialFrequencyFAS

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Initialize and load model
model = SpatialFrequencyFAS(pretrained=True)
model_path = "fas_spatial_freq.pth"

if os.path.exists(model_path):
    try:
        model.load_state_dict(torch.load(model_path, map_location=DEVICE))
        print("Loaded trained model weights.")
    except Exception as e:
        print(f"Failed to load weights, using randomly initialized classifier: {e}")
else:
    print("No weights found at fas_spatial_freq.pth. Using base model.")

model.to(DEVICE)
model.eval()

# Spatial transform
spatial_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def check_liveness(face_crop: np.ndarray, threshold=0.50):
    """
    Evaluates face crop for spoof attacks using PyTorch SpatialFrequencyFAS.
    Returns: (is_real: bool, real_prob: float)
    """
    if face_crop is None or face_crop.size == 0:
        return False, 0.0

    try:
        # 1. Prepare Spatial Tensor (B, C, H, W)
        x_spatial = spatial_transform(face_crop).unsqueeze(0).to(DEVICE)
        
        # 2. Prepare Frequency Tensor (B, C, H, W)
        x_freq = extract_fft_spectrum(face_crop, target_size=(224, 224)).to(DEVICE)
        
        # 3. Forward Pass
        with torch.no_grad():
            output = model(x_spatial, x_freq)
            # Output is logits for (Spoof, Real)
            probs = torch.softmax(output, dim=1)
            real_prob = probs[0][1].item()
            
        is_real = real_prob >= threshold
        return is_real, real_prob
    except Exception as e:
        print(f"Liveness inference error: {e}")
        # Fallback dummy score for development if tensors crash
        return False, 0.0