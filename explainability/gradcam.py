import torch
import torch.nn.functional as F
import numpy as np
import cv2

class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        
        self.hook_handles = []
        self.hook_handles.append(self.target_layer.register_forward_hook(self.save_activation))
        self.hook_handles.append(self.target_layer.register_full_backward_hook(self.save_gradient))
        
    def save_activation(self, module, input, output):
        self.activations = output
        
    def save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0]
        
    def generate_heatmap(self, input_tensor, *args, target_class=None):
        """
        Generates Grad-CAM heatmap for the input tensor.
        input_tensor: [1, C, H, W] tensor
        Returns: normalized heatmap numpy array (H, W) between 0 and 1
        """
        model_output = self.model(input_tensor, *args)
        
        if target_class is None:
            target_class = torch.argmax(model_output, dim=1).item()
            
        self.model.zero_grad()
        
        target = model_output[0, target_class]
        target.backward(retain_graph=True)
        
        gradients = self.gradients.detach().cpu().numpy()[0]
        activations = self.activations.detach().cpu().numpy()[0]
        
        weights = np.mean(gradients, axis=(1, 2))
        
        heatmap = np.zeros(activations.shape[1:], dtype=np.float32)
        for i, w in enumerate(weights):
            heatmap += w * activations[i]
            
        heatmap = np.maximum(heatmap, 0)
        
        if np.max(heatmap) > 0:
            heatmap = heatmap / np.max(heatmap)
            
        input_shape = input_tensor.shape[2:]
        heatmap = cv2.resize(heatmap, (input_shape[1], input_shape[0]))
        
        return heatmap

def overlay_heatmap(image, heatmap, alpha=0.5, colormap=cv2.COLORMAP_JET):
    """
    Overlays heatmap on original image.
    image: numpy array (H, W, 3)
    heatmap: numpy array (H, W) float 0-1
    """
    heatmap_colored = cv2.applyColorMap(np.uint8(255 * heatmap), colormap)
    if image.dtype != np.uint8:
        image = np.uint8(image)
    overlayed = cv2.addWeighted(image, 1 - alpha, heatmap_colored, alpha, 0)
    return overlayed
