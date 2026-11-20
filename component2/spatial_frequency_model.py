import torch
import torch.nn as nn
import torchvision.models as models

class SpatialFrequencyFAS(nn.Module):
    def __init__(self, pretrained=True):
        super(SpatialFrequencyFAS, self).__init__()
        
        # Spatial Branch (RGB Face)
        spatial_net = models.resnet18(weights=models.ResNet18_Weights.DEFAULT if pretrained else None)
        self.spatial_encoder = nn.Sequential(*list(spatial_net.children())[:-1])  # Output: (B, 512, 1, 1)
        
        # Frequency Branch (FFT Spectrum)
        freq_net = models.resnet18(weights=models.ResNet18_Weights.DEFAULT if pretrained else None)
        self.freq_encoder = nn.Sequential(*list(freq_net.children())[:-1])        # Output: (B, 512, 1, 1)
        
        # Feature Fusion & Classifier
        self.classifier = nn.Sequential(
            nn.Linear(512 + 512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(256, 2)  # Index 0: Spoof, Index 1: Real
        )

    def forward(self, x_spatial, x_freq):
        f_s = torch.flatten(self.spatial_encoder(x_spatial), 1)  # (B, 512)
        f_f = torch.flatten(self.freq_encoder(x_freq), 1)        # (B, 512)
        
        fused = torch.cat((f_s, f_f), dim=1)                    # (B, 1024)
        out = self.classifier(fused)
        return out