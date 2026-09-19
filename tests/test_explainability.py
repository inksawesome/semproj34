import numpy as np
import torch
import torch.nn as nn
from explainability.gradcam import GradCAM, overlay_heatmap
from explainability.frequency_explanation import visualize_frequency_spectrum
from explainability.explanation import generate_explanation

class DummyModel(nn.Module):
    def __init__(self):
        super(DummyModel, self).__init__()
        self.conv = nn.Conv2d(3, 16, 3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(16, 2)
        
    def forward(self, x):
        x = self.conv(x)
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

def test_gradcam():
    model = DummyModel()
    # Hook into the conv layer
    gradcam = GradCAM(model, model.conv)
    
    # Dummy input image
    input_tensor = torch.randn(1, 3, 224, 224)
    
    heatmap = gradcam.generate_heatmap(input_tensor)
    
    # Heatmap should be a 2D numpy array resized to the input dims
    assert isinstance(heatmap, np.ndarray)
    assert heatmap.shape == (224, 224)
    assert np.max(heatmap) <= 1.0 and np.min(heatmap) >= 0.0

def test_overlay_heatmap():
    image = np.zeros((224, 224, 3), dtype=np.uint8)
    heatmap = np.ones((224, 224), dtype=np.float32)
    
    overlayed = overlay_heatmap(image, heatmap)
    assert overlayed.shape == (224, 224, 3)
    assert overlayed.dtype == np.uint8

def test_frequency_spectrum():
    image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    spectrum = visualize_frequency_spectrum(image)
    
    assert spectrum.shape == (224, 224, 3)
    assert spectrum.dtype == np.uint8

def test_generate_explanation():
    result = generate_explanation(
        spatial_score=0.9, 
        freq_score=0.8, 
        active_pass=True,
        heatmap="dummy_heatmap",
        spectrum="dummy_spectrum"
    )
    
    assert result["verdict"] == "REAL"
    assert result["evidence"]["active_challenge_passed"] is True
    assert "dummy_heatmap" == result["spatial_heatmap_img"]
    
    result_spoof = generate_explanation(
        spatial_score=0.2, 
        freq_score=0.9, 
        active_pass=False
    )
    
    assert result_spoof["verdict"] == "SPOOF"
    assert "Failed active challenge" in result_spoof["reasoning"]
