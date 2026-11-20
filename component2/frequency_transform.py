import cv2
import numpy as np
import torch

def extract_fft_spectrum(face_rgb: np.ndarray, target_size=(224, 224)) -> torch.Tensor:
    """
    Computes 2D-FFT log magnitude spectrum from an RGB face crop.
    Outputs a normalized Tensor shaped (1, 3, H, W).
    """
    face_resized = cv2.resize(face_rgb, target_size)
    channels = []
    
    for c in range(3):
        f = np.fft.fft2(face_resized[:, :, c])
        fshift = np.fft.fftshift(f)
        magnitude = 20 * np.log(np.abs(fshift) + 1e-8)
        norm_mag = (magnitude - np.min(magnitude)) / (np.max(magnitude) - np.min(magnitude) + 1e-8)
        channels.append(norm_mag)
        
    spectrum = np.stack(channels, axis=0).astype(np.float32)
    return torch.from_numpy(spectrum).unsqueeze(0)