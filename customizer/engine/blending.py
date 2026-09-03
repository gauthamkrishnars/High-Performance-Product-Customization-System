"""
Photorealistic Blending and Surface Composite Engine.
Applies print industry transfer formulas (Multiply, Overlay, Soft Light, Photometric Modulation)
allowing natural fabric lighting, shadows, and micro-weaves to show through the graphic print.
"""

import numpy as np
import cv2


def blend_multiply(base_bgr, graphic_bgr):
    """(Base * Graphic) / 255.0"""
    return (base_bgr.astype(np.float32) * graphic_bgr.astype(np.float32) / 255.0)


def blend_overlay(base_bgr, graphic_bgr):
    """Photometric Overlay: Preserves dark shadows and bright highlights"""
    base = base_bgr.astype(np.float32) / 255.0
    graphic = graphic_bgr.astype(np.float32) / 255.0
    
    low = 2.0 * base * graphic
    high = 1.0 - 2.0 * (1.0 - base) * (1.0 - graphic)
    
    result = np.where(base < 0.5, low, high) * 255.0
    return np.clip(result, 0.0, 255.0)


def blend_soft_light(base_bgr, graphic_bgr):
    """Soft Light: Subtle contrast and gentle diffuse lighting infusion"""
    base = base_bgr.astype(np.float32) / 255.0
    graphic = graphic_bgr.astype(np.float32) / 255.0
    
    result = (1.0 - 2.0 * graphic) * (base ** 2) + 2.0 * graphic * base
    return np.clip(result * 255.0, 0.0, 255.0)


def composite_photorealistic_print(
    base_bgr, 
    displaced_rgba, 
    surface_shading, 
    blend_mode='MULTIPLY', 
    texture_depth=1.35, 
    ink_opacity=0.98
):
    """
    Unified composite pipeline:
    1. Applies photometric fold shadow / highlight modulation to the graphic.
    2. Executes blending mode (Multiply, Overlay, Soft Light).
    3. Blends modulated ink over base fabric using alpha channel with anti-aliasing.
    
    :param base_bgr: Base product photo (H, W, 3) in BGR uint8
    :param displaced_rgba: Conformed design graphic (H, W, 4) in BGRA uint8
    :param surface_shading: Micro and macro shading map (H, W) float32 centered at 1.0
    :param blend_mode: MULTIPLY | OVERLAY | SOFT_LIGHT | NORMAL
    :param texture_depth: Contrast of underlying wrinkles showing through ink
    :param ink_opacity: Overall opacity factor (0.0 to 1.0)
    :return: Final photorealistic mockup (H, W, 3) in BGR uint8
    """
    h, w = base_bgr.shape[:2]
    
    graphic_bgr = displaced_rgba[:, :, :3].astype(np.float32)
    alpha = (displaced_rgba[:, :, 3].astype(np.float32) / 255.0) * ink_opacity
    
    # 1. Surface Shading Modulation
    # Scale shading intensity according to texture_depth
    modulated_shading = 1.0 + (surface_shading - 1.0) * texture_depth
    modulated_shading_3ch = np.dstack([modulated_shading] * 3)
    
    # Inks are naturally shadowed by dark folds and highlighted by illuminated ridges
    shaded_graphic_bgr = np.clip(graphic_bgr * modulated_shading_3ch, 0.0, 255.0)
    
    # 2. Mode Blending
    base_f32 = base_bgr.astype(np.float32)
    
    if blend_mode == 'MULTIPLY':
        blended_bgr = blend_multiply(base_f32, shaded_graphic_bgr)
    elif blend_mode == 'OVERLAY':
        blended_bgr = blend_overlay(base_f32, shaded_graphic_bgr)
    elif blend_mode == 'SOFT_LIGHT':
        blended_bgr = blend_soft_light(base_f32, shaded_graphic_bgr)
    else:  # NORMAL
        # Even with normal ink deposit, we apply 30% shadow bleed to prevent plastic look
        ambient_shadow = np.clip(shaded_graphic_bgr * (0.7 + 0.3 * modulated_shading_3ch), 0.0, 255.0)
        blended_bgr = ambient_shadow
    
    # 3. Alpha Composite with Base
    # Output = Alpha * Blended + (1 - Alpha) * Base
    alpha_3ch = np.dstack([alpha] * 3)
    output_f32 = (alpha_3ch * blended_bgr) + ((1.0 - alpha_3ch) * base_f32)
    
    return np.clip(output_f32, 0.0, 255.0).astype(np.uint8)
