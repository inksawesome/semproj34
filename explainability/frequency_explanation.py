import numpy as np
import cv2

def visualize_frequency_spectrum(image):
    """
    Computes 2D FFT and returns a colorized magnitude spectrum image 
    to highlight high-frequency anomalies (e.g. screen moire).
    image: numpy array (H, W, 3) or (H, W)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
        
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1)
    
    magnitude_spectrum = cv2.normalize(magnitude_spectrum, None, 0, 255, cv2.NORM_MINMAX)
    magnitude_spectrum = np.uint8(magnitude_spectrum)
    
    spectrum_colored = cv2.applyColorMap(magnitude_spectrum, cv2.COLORMAP_JET)
    
    return spectrum_colored
