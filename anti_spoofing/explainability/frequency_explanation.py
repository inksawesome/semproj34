import numpy as np
import cv2

def visualize_frequency_spectrum(image):
    """
    Computes 2D FFT and returns a normalized magnitude spectrum image.
    image: grayscale or BGR image
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
    f = np.fft.fft2(image)
    fshift = np.fft.fftshift(f)
    
    # Adding 1 to avoid log(0)
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1)
    
    # Normalize to 0-255 for visualization
    magnitude_spectrum = cv2.normalize(magnitude_spectrum, None, 0, 255, cv2.NORM_MINMAX)
    magnitude_spectrum = np.uint8(magnitude_spectrum)
    
    # Highlight high frequencies using a colormap
    colored_spectrum = cv2.applyColorMap(magnitude_spectrum, cv2.COLORMAP_JET)
    return colored_spectrum
