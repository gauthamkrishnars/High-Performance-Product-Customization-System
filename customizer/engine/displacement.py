"""
Automatic Displacement Mapping Engine.
Analyzes fabric texture, folds, and surface curvature from base product photography
and conforms graphics to the natural wrinkles of the material.
"""

import numpy as np
import cv2


def extract_surface_displacement_field(base_bgr, intensity=16.0, blur_sigma=7.0):
    """
    Computes a 2D vector displacement field (map_x, map_y) and surface texture shading
    from the natural brightness gradients of the base product.
    
    :param base_bgr: NumPy array (H, W, 3) representing the base product
    :param intensity: Maximum pixel displacement factor for fabric conformation
    :param blur_sigma: Gaussian kernel smoothing factor to balance macro folds vs micro weave
    :return: (map_x, map_y, normalized_shading)
    """
    h, w = base_bgr.shape[:2]
    
    # Convert to CIELAB and extract L (Perceptual Lightness)
    lab = cv2.cvtColor(base_bgr, cv2.COLOR_BGR2LAB)
    lightness = lab[:, :, 0].astype(np.float32)
    
    # Extract macro folds by subtracting low-frequency illumination (High-pass filter)
    macro_illumination = cv2.GaussianBlur(lightness, (0, 0), sigmaX=35, sigmaY=35)
    high_pass_folds = lightness - macro_illumination
    
    # Smooth the fold details to prevent noisy digital tearing while preserving drape lines
    smoothed_folds = cv2.GaussianBlur(high_pass_folds, (0, 0), sigmaX=blur_sigma, sigmaY=blur_sigma)
    
    # Calculate directional surface normals using Sobel gradient filters (ksize=5 for smooth derivatives)
    grad_x = cv2.Sobel(smoothed_folds, cv2.CV_32F, 1, 0, ksize=5)
    grad_y = cv2.Sobel(smoothed_folds, cv2.CV_32F, 0, 1, ksize=5)
    
    # Normalize gradients relative to local standard deviation
    std_val = np.std(grad_x) + 1e-6
    norm_grad_x = (grad_x / std_val) * (intensity * 0.45)
    norm_grad_y = (grad_y / std_val) * (intensity * 0.45)
    
    # Construct base coordinate grid
    x_coords, y_coords = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    
    # Displace coordinates along surface gradient normals
    # Positive gradient (rising fold slope) shifts pixels toward the viewer
    map_x = x_coords + norm_grad_x
    map_y = y_coords + norm_grad_y
    
    # Generate photometrically calibrated surface texture shading (centered at 1.0)
    # Highlights > 1.0, Shadows < 1.0
    normalized_shading = 1.0 + (high_pass_folds / 128.0) * 0.85
    normalized_shading = np.clip(normalized_shading, 0.4, 1.6)
    
    return map_x, map_y, normalized_shading


def apply_displacement_to_graphic(warped_rgba, map_x, map_y):
    """
    Distorts the perspective-warped graphic according to the fabric displacement field
    using bicubic interpolation for smooth, realistic deformation along folds.
    """
    # Remap RGBA channels
    displaced_rgba = cv2.remap(
        warped_rgba,
        map_x,
        map_y,
        interpolation=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0)
    )
    return displaced_rgba
