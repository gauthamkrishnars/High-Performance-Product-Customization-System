"""
Unified High-Performance Rendering Pipeline.
Connects Perspective Transformation, Displacement Mapping, and Photometric Blending
into an optimized, high-throughput render pipeline.
"""

import time
import os
import cv2
import numpy as np
from PIL import Image

from .perspective import transform_design_geometry
from .displacement import extract_surface_displacement_field, apply_displacement_to_graphic
from .blending import composite_photorealistic_print


def render_custom_mockup(
    base_image_path,
    design_image_path,
    quad_points,
    output_path=None,
    scale=1.0,
    rotation=0.0,
    offset_x=0.0,
    offset_y=0.0,
    blend_mode='MULTIPLY',
    displacement_intensity=16.0,
    texture_depth=1.35,
    max_resolution=2400
):
    """
    Executes the full photorealistic rendering pipeline.
    
    :return: dict with keys: 'success', 'output_path', 'execution_time_ms', 'width', 'height', 'error'
    """
    start_time = time.perf_counter()
    
    try:
        # 1. Load Base Product Image
        if not os.path.exists(base_image_path):
            raise FileNotFoundError(f"Base product image not found at {base_image_path}")
            
        base_bgr = cv2.imread(base_image_path, cv2.IMREAD_COLOR)
        if base_bgr is None:
            raise ValueError(f"OpenCV failed to decode base image: {base_image_path}")
            
        bh, bw = base_bgr.shape[:2]
        
        # Scale down if exceeds max_resolution while preserving aspect ratio
        if max(bh, bw) > max_resolution:
            ratio = max_resolution / float(max(bh, bw))
            new_w, new_h = int(bw * ratio), int(bh * ratio)
            base_bgr = cv2.resize(base_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
            bh, bw = new_h, new_w
            
        # 2. Load and Prepare Design Image
        if not os.path.exists(design_image_path):
            raise FileNotFoundError(f"Design image not found at {design_image_path}")
            
        # Use Pillow first to correctly handle transparency and orientation metadata
        pil_design = Image.open(design_image_path).convert('RGBA')
        design_np = np.array(pil_design)
        
        # Convert RGB to BGR for OpenCV while keeping Alpha
        design_bgra = cv2.cvtColor(design_np, cv2.COLOR_RGBA2BGRA)
        
        # 3. Perspective Alignment to Angled Surface Quad
        warped_rgba, warp_mask = transform_design_geometry(
            design_rgba=design_bgra,
            scale=scale,
            rotation_deg=rotation,
            offset_x_pct=offset_x,
            offset_y_pct=offset_y,
            quad_points=quad_points,
            base_w=bw,
            base_h=bh
        )
        
        # 4. Automated Surface Texture & Displacement Field Extraction
        map_x, map_y, surface_shading = extract_surface_displacement_field(
            base_bgr=base_bgr,
            intensity=displacement_intensity,
            blur_sigma=6.5
        )
        
        # 5. Conforming Graphic to Fabric Wrinkles via Remap
        displaced_rgba = apply_displacement_to_graphic(warped_rgba, map_x, map_y)
        
        # 6. Photorealistic Blending with Fabric Shading
        final_mockup_bgr = composite_photorealistic_print(
            base_bgr=base_bgr,
            displaced_rgba=displaced_rgba,
            surface_shading=surface_shading,
            blend_mode=blend_mode,
            texture_depth=texture_depth
        )
        
        # 7. Export Result
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            # High quality JPEG / PNG export
            ext = os.path.splitext(output_path)[1].lower()
            if ext in ['.jpg', '.jpeg']:
                cv2.imwrite(output_path, final_mockup_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
            else:
                cv2.imwrite(output_path, final_mockup_bgr, [cv2.IMWRITE_PNG_COMPRESSION, 4])
                
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        
        return {
            'success': True,
            'output_path': output_path,
            'execution_time_ms': round(elapsed_ms, 2),
            'width': bw,
            'height': bh,
            'error': None
        }
        
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            'success': False,
            'output_path': None,
            'execution_time_ms': round(elapsed_ms, 2),
            'width': 0,
            'height': 0,
            'error': str(e)
        }
