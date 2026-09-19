import cv2
import numpy as np
import torch
import torch.nn as nn
from explainability.gradcam import GradCAM, overlay_heatmap
from explainability.frequency_explanation import visualize_frequency_spectrum
from explainability.explanation import generate_explanation

# Dummy model for demonstration purposes
class DummyResNet(nn.Module):
    def __init__(self):
        super(DummyResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 16, 7, padding=3)
        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(32, 2)
        
    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = torch.relu(self.conv2(x))
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

def main():
    print("Initializing Explainability Demo...")
    
    # 1. Create a dummy image (e.g. noise to simulate moire, with some pattern)
    image = np.zeros((224, 224, 3), dtype=np.uint8)
    image[:, :] = (100, 100, 100)
    # Add a bright square (simulating a face)
    cv2.rectangle(image, (60, 60), (160, 160), (200, 150, 150), -1)
    # Add some high frequency noise (simulating screen artifacts)
    noise = np.random.randint(0, 50, (224, 224, 3), dtype=np.uint8)
    image = cv2.add(image, noise)
    
    cv2.imwrite("dummy_input.jpg", image)
    
    # 2. Setup Dummy Model and GradCAM
    model = DummyResNet()
    target_layer = model.conv2
    gradcam = GradCAM(model, target_layer)
    
    # 3. Generate Spatial Heatmap
    # Convert image to tensor: [1, 3, 224, 224]
    input_tensor = torch.tensor(image, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0) / 255.0
    input_tensor.requires_grad_(True) # Important for GradCAM if inputs don't inherently require grad
    
    raw_heatmap = gradcam.generate_heatmap(input_tensor, target_class=0)
    heatmap_overlay = overlay_heatmap(image, raw_heatmap)
    
    cv2.imwrite("spatial_heatmap.jpg", heatmap_overlay)
    
    # 4. Generate Frequency Spectrum
    spectrum = visualize_frequency_spectrum(image)
    cv2.imwrite("frequency_spectrum.jpg", spectrum)
    
    # 5. Generate Final Explanation (simulate a SPOOF case)
    result = generate_explanation(
        spatial_score=0.2, 
        freq_score=0.3, 
        active_pass=False,
        image=image,
        heatmap=heatmap_overlay,
        spectrum=spectrum
    )
    
    print("\n--- Final Explanation Output ---")
    print(f"Verdict: {result['verdict']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"Evidence: {result['evidence']}")
    print("--------------------------------")
    
    print("\nDemo complete! Check 'dummy_input.jpg', 'spatial_heatmap.jpg', and 'frequency_spectrum.jpg'.")

if __name__ == "__main__":
    main()
