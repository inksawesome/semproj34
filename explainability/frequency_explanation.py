import numpy as np
import cv2


def _gray(image):
    if image.ndim == 3:
        return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    return image


def visualize_frequency_spectrum(image):
    """
    Computes 2D FFT and returns a colorized (RGB) log-magnitude spectrum
    to highlight high-frequency anomalies (e.g. screen moire).
    image: RGB numpy array (H, W, 3) or grayscale (H, W)
    """
    gray = cv2.resize(_gray(image), (224, 224))
    fshift = np.fft.fftshift(np.fft.fft2(gray))
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1)
    magnitude_spectrum = cv2.normalize(magnitude_spectrum, None, 0, 255, cv2.NORM_MINMAX)
    spectrum_colored = cv2.applyColorMap(np.uint8(magnitude_spectrum), cv2.COLORMAP_INFERNO)
    return cv2.cvtColor(spectrum_colored, cv2.COLOR_BGR2RGB)


def radial_profile(image, bins: int = 48):
    """
    Azimuthally averaged log power spectrum, from DC (0) to Nyquist (1).
    Re-captured faces show a raised tail (screen grid / moire / print dots)
    or a collapsed tail (blur / compression) compared with live faces.
    """
    gray = cv2.resize(_gray(image), (128, 128)).astype(np.float64)
    gray = (gray - gray.mean()) * np.outer(np.hanning(128), np.hanning(128))
    power = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(gray))) ** 2)
    yy, xx = np.indices(power.shape)
    r = np.hypot(yy - 64, xx - 64) / 64.0
    idx = np.clip((r * bins).astype(int), 0, bins)
    prof = np.bincount(idx.ravel(), power.ravel(), minlength=bins + 1)[:bins] / \
        np.maximum(np.bincount(idx.ravel(), minlength=bins + 1)[:bins], 1)
    return np.linspace(0, 1, bins, endpoint=False), prof


def high_frequency_ratio(image) -> float:
    """Share of spectral energy above 0.4 x Nyquist."""
    gray = cv2.resize(_gray(image), (128, 128)).astype(np.float64)
    gray = (gray - gray.mean()) * np.outer(np.hanning(128), np.hanning(128))
    power = np.abs(np.fft.fftshift(np.fft.fft2(gray))) ** 2
    yy, xx = np.indices(power.shape)
    r = np.hypot(yy - 64, xx - 64) / 64.0
    return float(power[r > 0.4].sum() / (power.sum() + 1e-9))
