"""
Perspective Transformation Engine.
Computes perspective homography matrices and maps 2D design art onto 3D angled surfaces.
"""

import math
import numpy as np
import cv2
from PIL import Image


def compute_perspective_transform(design_rgba, target_quad, canvas_width, canvas_height):
    """
    Warp a design image into a 4-point quadrilateral on a target canvas.
    
    :param design_rgba: NumPy array (H, W, 4) in BGRA format
    :param target_quad: List of 4 points [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
                        in pixel space of target canvas
    :param canvas_width: Output canvas width
    :param canvas_height: Output canvas height
    :return: (warped_rgba, warp_mask)
    """
    dh, dw = design_rgba.shape[:2]
    
    # Source corners (top-left, top-right, bottom-right, bottom-left)
    src_pts = np.array([
        [0, 0],
        [dw - 1, 0],
        [dw - 1, dh - 1],
        [0, dh - 1]
    ], dtype=np.float32)
    
    dst_pts = np.array(target_quad, dtype=np.float32)
    
    # Calculate 3x3 homography matrix
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    
    # Warp with high-order Lanczos interpolation for razor-sharp typography and vector-like lines
    warped_rgba = cv2.warpPerspective(
        design_rgba,
        matrix,
        (canvas_width, canvas_height),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0)
    )
    
    # Extract clean binary mask of transformed polygon
    alpha_channel = warped_rgba[:, :, 3]
    _, warp_mask = cv2.threshold(alpha_channel, 1, 255, cv2.THRESH_BINARY)
    
    return warped_rgba, warp_mask


def transform_design_geometry(design_rgba, scale=1.0, rotation_deg=0.0, offset_x_pct=0.0, offset_y_pct=0.0, quad_points=None, base_w=1000, base_h=1000):
    """
    Adjusts target quadrilateral according to user scale, rotation, and translation offsets,
    then warps design into base canvas coordinates.
    """
    # Convert normalized quad percentages (0-100) to actual pixel coordinates
    pts = np.array(quad_points, dtype=np.float32)
    px_pts = pts.copy()
    px_pts[:, 0] = (px_pts[:, 0] / 100.0) * base_w
    px_pts[:, 1] = (px_pts[:, 1] / 100.0) * base_h
    
    # Compute center of target polygon
    center = np.mean(px_pts, axis=0)
    
    # Apply user translation offset (normalized to print area size)
    area_w = np.max(px_pts[:, 0]) - np.min(px_pts[:, 0])
    area_h = np.max(px_pts[:, 1]) - np.min(px_pts[:, 1])
    dx = (offset_x_pct / 100.0) * area_w
    dy = (offset_y_pct / 100.0) * area_h
    
    # Transform each corner: Center -> Scale -> Rotate -> Translate -> Offset
    rad = math.radians(rotation_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    
    transformed_quad = []
    for pt in px_pts:
        # Translate to origin
        ox = pt[0] - center[0]
        oy = pt[1] - center[1]
        
        # Apply scale
        sx = ox * scale
        sy = oy * scale
        
        # Apply rotation
        rx = sx * cos_a - sy * sin_a
        ry = sx * sin_a + sy * cos_a
        
        # Translate back to center plus user offset
        final_x = rx + center[0] + dx
        final_y = ry + center[1] + dy
        transformed_quad.append([final_x, final_y])
        
    return compute_perspective_transform(design_rgba, transformed_quad, base_w, base_h)
