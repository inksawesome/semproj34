import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
import os
import cv2
import time
import random
from glob import glob

from spatial_frequency_model import SpatialFrequencyFAS
from frequency_transform import extract_fft_spectrum

class FASDataset(Dataset):
    def __init__(self, root_dir, max_samples_per_class=None):
        """
        Expects a directory structure:
        root_dir/
            real/
            spoof/
        """
        self.image_paths = []
        self.labels = []
        
        # Load all paths
        real_dir = os.path.join(root_dir, 'real')
        spoof_dir = os.path.join(root_dir, 'spoof')
        
        real_paths = []
        if os.path.exists(real_dir):
            for ext in ('*.jpg', '*.png', '*.jpeg'):
                real_paths.extend(glob(os.path.join(real_dir, ext)))
                
        spoof_paths = []
        if os.path.exists(spoof_dir):
            for ext in ('*.jpg', '*.png', '*.jpeg'):
                spoof_paths.extend(glob(os.path.join(spoof_dir, ext)))

        # Balance the dataset
        if max_samples_per_class is None:
            # Auto-balance to the size of the minority class
            max_samples_per_class = min(len(real_paths), len(spoof_paths))
            print(f"Auto-balancing classes to {max_samples_per_class} images each.")

        # Shuffle and trim
        random.shuffle(real_paths)
        random.shuffle(spoof_paths)
        
        real_paths = real_paths[:max_samples_per_class]
        spoof_paths = spoof_paths[:max_samples_per_class]

        self.image_paths.extend(real_paths)
        self.labels.extend([1] * len(real_paths))
        
        self.image_paths.extend(spoof_paths)
        self.labels.extend([0] * len(spoof_paths))
                
        self.spatial_transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        label = self.labels[idx]
        
        img = cv2.imread(img_path)
        if img is None:
            spatial = torch.zeros((3, 224, 224))
            freq = torch.zeros((3, 224, 224))
            return spatial, freq, torch.tensor(label, dtype=torch.long)
            
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        spatial_tensor = self.spatial_transform(img_rgb)
        freq_tensor = extract_fft_spectrum(img_rgb, target_size=(224, 224)).squeeze(0)
        
        return spatial_tensor, freq_tensor, torch.tensor(label, dtype=torch.long)

def train_fas_model(data_dir="LCC_FASD_development", epochs=5, batch_size=8):
    print(f"Scanning '{data_dir}' for training images...")
    
    if not os.path.exists(data_dir):
        print(f"Error: Directory '{data_dir}' not found.")
        return
        
    dataset = FASDataset(data_dir)
    if len(dataset) == 0:
        print(f"Error: No images found in {data_dir}/real or {data_dir}/spoof.")
        return
        
    print(f"Total balanced dataset size: {len(dataset)} images. Initializing Transfer Learning...")
    
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SpatialFrequencyFAS(pretrained=True)
    model.to(DEVICE)
    
    # Freeze ResNet backbones to only train the fusion/classifier head
    for param in model.spatial_encoder.parameters():
        param.requires_grad = False
    for param in model.freq_encoder.parameters():
        param.requires_grad = False
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.classifier.parameters(), lr=0.001)
    
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    print("\nStarting Training Loop...")
    model.train()
    
    for epoch in range(epochs):
        epoch_loss = 0.0
        start_time = time.time()
        
        for batch_idx, (spatial, freq, labels) in enumerate(dataloader):
            spatial, freq, labels = spatial.to(DEVICE), freq.to(DEVICE), labels.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(spatial, freq)
            loss = criterion(outputs, labels)
            
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            
        avg_loss = epoch_loss / len(dataloader)
        print(f"Epoch [{epoch+1}/{epochs}] - Loss: {avg_loss:.4f} - Time: {time.time()-start_time:.2f}s")
        
    save_path = "fas_spatial_freq.pth"
    torch.save(model.state_dict(), save_path)
    print(f"\nTraining Complete! Fine-tuned weights saved to {save_path}")

if __name__ == "__main__":
    train_fas_model(data_dir="LCC_FASD_development")
