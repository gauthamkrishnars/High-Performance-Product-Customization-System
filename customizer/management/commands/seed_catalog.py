import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from django.core.management.base import BaseCommand
from django.conf import settings
from customizer.models import Product, ProductAngle, CustomizationArea, PresetArtwork


def create_fabric_texture_image(width, height, base_color_rgb, style='tee_front'):
    """
    Synthesizes high-resolution base apparel photography with realistic
    fabric thread weaves, ambient lighting gradients, and drape wrinkles.
    """
    img = Image.new('RGB', (width, height), '#EFECE6')
    draw = ImageDraw.Draw(img)

    # 1. Subtle studio backdrop vignette
    np_bg = np.zeros((height, width, 3), dtype=np.float32)
    cy, cx = height * 0.45, width * 0.5
    y_coords, x_coords = np.ogrid[:height, :width]
    dist_from_center = np.sqrt(((x_coords - cx) / (width * 0.5))**2 + ((y_coords - cy) / (height * 0.5))**2)
    vignette = np.clip(1.0 - 0.22 * dist_from_center, 0.72, 1.0)
    
    bg_base = np.array([238, 235, 228], dtype=np.float32)
    np_bg[:, :] = bg_base * vignette[:, :, None]

    # 2. Apparel Silhouette definition
    mask = Image.new('L', (width, height), 0)
    m_draw = ImageDraw.Draw(mask)

    if style == 'tee_front':
        # T-Shirt contour points
        pts = [
            (width * 0.36, height * 0.16),  # Left collar
            (width * 0.50, height * 0.22),  # Center scoop
            (width * 0.64, height * 0.16),  # Right collar
            (width * 0.76, height * 0.20),  # Right shoulder
            (width * 0.88, height * 0.38),  # Right sleeve outer
            (width * 0.77, height * 0.43),  # Right sleeve cuff
            (width * 0.73, height * 0.38),  # Right armpit
            (width * 0.72, height * 0.88),  # Right hem
            (width * 0.28, height * 0.88),  # Left hem
            (width * 0.27, height * 0.38),  # Left armpit
            (width * 0.23, height * 0.43),  # Left sleeve cuff
            (width * 0.12, height * 0.38),  # Left sleeve outer
            (width * 0.24, height * 0.20),  # Left shoulder
        ]
        m_draw.polygon(pts, fill=255)

    elif style == 'tee_back':
        # T-Shirt back contour (shallower collar line)
        pts = [
            (width * 0.36, height * 0.16),
            (width * 0.50, height * 0.18),  # Higher collar back
            (width * 0.64, height * 0.16),
            (width * 0.76, height * 0.20),
            (width * 0.88, height * 0.38),
            (width * 0.77, height * 0.43),
            (width * 0.73, height * 0.38),
            (width * 0.72, height * 0.88),
            (width * 0.28, height * 0.88),
            (width * 0.27, height * 0.38),
            (width * 0.23, height * 0.43),
            (width * 0.12, height * 0.38),
            (width * 0.24, height * 0.20),
        ]
        m_draw.polygon(pts, fill=255)

    elif style == 'tee_side':
        # Angled 3D quarter perspective
        pts = [
            (width * 0.38, height * 0.17),
            (width * 0.54, height * 0.23),
            (width * 0.68, height * 0.19),
            (width * 0.84, height * 0.36),
            (width * 0.76, height * 0.42),
            (width * 0.69, height * 0.37),
            (width * 0.65, height * 0.87),
            (width * 0.33, height * 0.87),
            (width * 0.32, height * 0.39),
            (width * 0.24, height * 0.41),
            (width * 0.20, height * 0.32),
        ]
        m_draw.polygon(pts, fill=255)

    elif style == 'hoodie_front':
        # Hoodie contour with hood and pocket
        pts = [
            (width * 0.36, height * 0.11),  # Hood left
            (width * 0.50, height * 0.08),  # Hood peak
            (width * 0.64, height * 0.11),  # Hood right
            (width * 0.78, height * 0.22),  # Right shoulder
            (width * 0.90, height * 0.42),  # Right cuff
            (width * 0.81, height * 0.46),  # Right cuff inner
            (width * 0.75, height * 0.39),  # Right armpit
            (width * 0.74, height * 0.90),  # Right rib hem
            (width * 0.26, height * 0.90),  # Left rib hem
            (width * 0.25, height * 0.39),  # Left armpit
            (width * 0.19, height * 0.46),  # Left cuff inner
            (width * 0.10, height * 0.42),  # Left cuff
            (width * 0.22, height * 0.22),  # Left shoulder
        ]
        m_draw.polygon(pts, fill=255)

    elif style == 'tote_front':
        # Canvas tote with shoulder straps
        # Body
        m_draw.rectangle([width * 0.26, height * 0.38, width * 0.74, height * 0.90], fill=255)
        # Straps
        m_draw.polygon([(width * 0.35, height * 0.38), (width * 0.39, height * 0.14), (width * 0.42, height * 0.14), (width * 0.38, height * 0.38)], fill=255)
        m_draw.polygon([(width * 0.62, height * 0.38), (width * 0.58, height * 0.14), (width * 0.61, height * 0.14), (width * 0.65, height * 0.38)], fill=255)

    # Blur mask edges for optical anti-aliasing
    mask = mask.filter(ImageFilter.GaussianBlur(1.8))
    np_mask = np.array(mask, dtype=np.float32) / 255.0

    # 3. Synthesize fabric material & micro-weave
    fabric_np = np.zeros((height, width, 3), dtype=np.float32)
    base_color = np.array(base_color_rgb, dtype=np.float32)

    # Add gentle undulating fold shadows
    fold_field = np.zeros((height, width), dtype=np.float32)
    for i in range(4):
        freq_y = (i + 1) * 0.007
        freq_x = (i + 1) * 0.009
        phase = i * 1.5
        fold_field += np.sin(y_coords * freq_y + x_coords * 0.003 + phase) * (18.0 / (i + 1.2))
        fold_field += np.cos(x_coords * freq_x + y_coords * 0.002 + phase) * (12.0 / (i + 1.4))

    # Add micro-grain textile weave noise
    rng = np.random.default_rng(seed=42)
    micro_weave = rng.normal(0.0, 3.5, (height, width)).astype(np.float32)

    # Shading modulation
    lighting = 1.0 + (fold_field + micro_weave) / 255.0
    lighting = np.clip(lighting, 0.68, 1.25)

    fabric_np[:, :] = np.clip(base_color * lighting[:, :, None], 0.0, 255.0)

    # 4. Composite garment onto studio backdrop with soft drop shadow
    shadow_mask = mask.filter(ImageFilter.GaussianBlur(18.0))
    np_shadow = np.array(shadow_mask, dtype=np.float32) / 255.0
    shadow_mult = np.clip(1.0 - 0.28 * np_shadow, 0.0, 1.0)
    np_bg = np_bg * shadow_mult[:, :, None]

    # Combine
    final_np = (np_mask[:, :, None] * fabric_np) + ((1.0 - np_mask[:, :, None]) * np_bg)
    final_img = Image.fromarray(np.clip(final_np, 0, 255).astype(np.uint8))
    
    # Draw subtle seams and collar stitching
    draw_final = ImageDraw.Draw(final_img)
    if 'tee' in style:
        # Ribbed collar ellipse
        collar_color = tuple(int(c * 0.88) for c in base_color_rgb)
        draw_final.arc([width * 0.38, height * 0.15, width * 0.62, height * 0.24], start=0, end=180, fill=collar_color, width=3)
    elif style == 'hoodie_front':
        # Kangaroo pouch pocket
        pouch_color = tuple(int(c * 0.92) for c in base_color_rgb)
        draw_final.polygon([
            (width * 0.35, height * 0.62),
            (width * 0.65, height * 0.62),
            (width * 0.69, height * 0.85),
            (width * 0.31, height * 0.85),
        ], outline=pouch_color, width=2)

    return final_img


def create_sample_artwork(width, height, title, art_type='streetwear'):
    """
    Generates high-resolution sample graphic artworks for instantaneous testing.
    """
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if art_type == 'streetwear':
        # Heavy block typography + cyber grid lines
        draw.rectangle([width * 0.08, height * 0.08, width * 0.92, height * 0.92], outline=(245, 245, 240, 240), width=6)
        draw.line([(width * 0.08, height * 0.5), (width * 0.92, height * 0.5)], fill=(220, 50, 45, 220), width=4)
        
        # Bold graphic rectangles
        draw.rectangle([width * 0.20, height * 0.22, width * 0.80, height * 0.44], fill=(240, 240, 235, 255))
        draw.rectangle([width * 0.25, height * 0.27, width * 0.75, height * 0.39], fill=(18, 20, 24, 255))
        
        # Accent lines
        for y in range(int(height * 0.56), int(height * 0.84), 22):
            draw.line([(width * 0.18, y), (width * 0.82, y)], fill=(240, 240, 235, 180), width=3)

    elif art_type == 'minimal':
        # Geometric architectural circle and monoline balance
        cx, cy = width // 2, height // 2
        r = int(width * 0.35)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(245, 245, 240, 255), width=8)
        draw.ellipse([cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6], fill=(220, 160, 40, 240))
        draw.line([(width * 0.15, cy), (width * 0.85, cy)], fill=(245, 245, 240, 255), width=6)
        draw.line([(cx, height * 0.15), (cx, height * 0.85)], fill=(245, 245, 240, 255), width=6)

    elif art_type == 'vintage':
        # Heritage badge / diamond crest
        pts = [(width * 0.5, height * 0.12), (width * 0.88, height * 0.5), (width * 0.5, height * 0.88), (width * 0.12, height * 0.5)]
        draw.polygon(pts, outline=(240, 230, 210, 255), width=7)
        draw.polygon([(p[0] * 0.85 + width * 0.075, p[1] * 0.85 + height * 0.075) for p in pts], outline=(180, 50, 40, 255), width=4)
        draw.ellipse([width * 0.38, height * 0.38, width * 0.62, height * 0.62], fill=(240, 230, 210, 255))

    elif art_type == 'editorial':
        # Editorial abstract composition
        draw.polygon([(width * 0.2, height * 0.8), (width * 0.5, height * 0.2), (width * 0.8, height * 0.8)], fill=(40, 140, 110, 240))
        draw.arc([width * 0.2, height * 0.2, width * 0.8, height * 0.8], 0, 180, fill=(245, 245, 240, 255), width=8)
        draw.rectangle([width * 0.35, height * 0.45, width * 0.65, height * 0.55], fill=(230, 80, 50, 255))

    return img


class Command(BaseCommand):
    help = 'Seeds realistic base apparel photography, angles, perspective customization areas, and preset artworks'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Initializing High-Performance Catalog & Sample Assets..."))

        base_dir = settings.MEDIA_ROOT
        products_dir = os.path.join(base_dir, 'base_products')
        artworks_dir = os.path.join(base_dir, 'sample_artworks')
        os.makedirs(products_dir, exist_ok=True)
        os.makedirs(artworks_dir, exist_ok=True)

        # 1. Create Catalog Products
        catalog_specs = [
            {
                'name': 'Oversized Heavyweight Cotton Tee',
                'slug': 'oversized-heavyweight-tee',
                'category': 'apparel',
                'color_name': 'Washed Onyx Black',
                'base_color_rgb': (32, 34, 36),
                'material': '100% Combed Ring-Spun Cotton, 260 GSM Heavy Jersey',
                'price': 42.00,
                'description': 'Boxy streetwear silhouette with drop shoulders and reinforced 1-inch collar ribbing. Optimized for oversized DTG and screen printing.',
                'angles': [
                    {
                        'type': 'front',
                        'name': 'Front Chest Perspective',
                        'style': 'tee_front',
                        'is_default': True,
                        'quad': [[33.0, 28.0], [67.0, 28.0], [66.0, 72.0], [34.0, 72.0]],
                        'blend': 'MULTIPLY',
                        'disp': 18.0,
                    },
                    {
                        'type': 'back',
                        'name': 'Back Spine & Shoulders',
                        'style': 'tee_back',
                        'is_default': False,
                        'quad': [[32.0, 24.0], [68.0, 24.0], [67.0, 74.0], [33.0, 74.0]],
                        'blend': 'MULTIPLY',
                        'disp': 16.0,
                    },
                    {
                        'type': 'side',
                        'name': 'Angled Sleeve & Torso',
                        'style': 'tee_side',
                        'is_default': False,
                        'quad': [[38.0, 30.0], [66.0, 27.0], [64.0, 75.0], [37.0, 78.0]],  # Natural 3D skew
                        'blend': 'MULTIPLY',
                        'disp': 22.0,
                    }
                ]
            },
            {
                'name': 'Vintage Washed French Terry Hoodie',
                'slug': 'vintage-washed-terry-hoodie',
                'category': 'apparel',
                'color_name': 'Desert Sand Charcoal',
                'base_color_rgb': (48, 46, 44),
                'material': '450 GSM Heavy French Terry Fleece with Double-Layer Hood',
                'price': 88.00,
                'description': 'Substantial heavyweight pullover with custom pigment wash, ribbed side gussets, and kangaroo pocket contours.',
                'angles': [
                    {
                        'type': 'front',
                        'name': 'Front Center Chest View',
                        'style': 'hoodie_front',
                        'is_default': True,
                        'quad': [[34.0, 27.0], [66.0, 27.0], [65.0, 58.0], [35.0, 58.0]],
                        'blend': 'MULTIPLY',
                        'disp': 20.0,
                    }
                ]
            },
            {
                'name': 'Heavyweight Natural Canvas Tote',
                'slug': 'heavyweight-canvas-tote',
                'category': 'accessories',
                'color_name': 'Unbleached Raw Ecru',
                'base_color_rgb': (228, 222, 210),
                'material': '16 oz Organic Cotton Duck Canvas with Reinforced Handles',
                'price': 28.00,
                'description': 'Rugged daily tote with structured flat bottom gusset. High-texture woven surface with natural slub variations.',
                'angles': [
                    {
                        'type': 'front',
                        'name': 'Front Canvas Surface',
                        'style': 'tote_front',
                        'is_default': True,
                        'quad': [[33.0, 42.0], [67.0, 42.0], [67.0, 84.0], [33.0, 84.0]],
                        'blend': 'MULTIPLY',
                        'disp': 14.0,
                    }
                ]
            }
        ]

        # Seed Products and Angles
        for p_spec in catalog_specs:
            product, created = Product.objects.get_or_create(
                slug=p_spec['slug'],
                defaults={
                    'name': p_spec['name'],
                    'category': p_spec['category'],
                    'color_name': p_spec['color_name'],
                    'material': p_spec['material'],
                    'price': p_spec['price'],
                    'description': p_spec['description'],
                    'base_color': '#%02x%02x%02x' % p_spec['base_color_rgb'],
                }
            )

            for idx, a_spec in enumerate(p_spec['angles']):
                angle_filename = f"{product.slug}_{a_spec['type']}.jpg"
                angle_path = os.path.join(products_dir, angle_filename)
                
                # Synthesize 1200x1200 high-res photography base
                base_img = create_fabric_texture_image(1200, 1200, p_spec['base_color_rgb'], style=a_spec['style'])
                base_img.save(angle_path, quality=95)

                angle, _ = ProductAngle.objects.get_or_create(
                    product=product,
                    angle_type=a_spec['type'],
                    defaults={
                        'name': a_spec['name'],
                        'base_image': f"base_products/{angle_filename}",
                        'is_default': a_spec['is_default'],
                        'sort_order': idx
                    }
                )

                # Set up Customization Area
                import json
                CustomizationArea.objects.update_or_create(
                    angle=angle,
                    defaults={
                        'name': f"{a_spec['name']} Print Area",
                        'max_width_mm': 360.0,
                        'max_height_mm': 460.0,
                        'bounding_left_pct': a_spec['quad'][0][0],
                        'bounding_top_pct': a_spec['quad'][0][1],
                        'bounding_width_pct': a_spec['quad'][1][0] - a_spec['quad'][0][0],
                        'bounding_height_pct': a_spec['quad'][2][1] - a_spec['quad'][1][1],
                        'quad_points_json': json.dumps(a_spec['quad']),
                        'displacement_strength': a_spec['disp'],
                        'blend_mode': a_spec['blend'],
                    }
                )

        self.stdout.write(self.style.SUCCESS("Products, Angles, and Print Areas seeded successfully."))

        # 2. Seed Preset Graphic Artworks
        sample_specs = [
            ('Neo-Tokyo Typographic Specimen', 'streetwear', 'streetwear'),
            ('Bauhaus Minimalist Sphere', 'minimal', 'minimal'),
            ('Heritage Mountain Badge', 'vintage', 'vintage'),
            ('Constructivist Prism', 'editorial', 'editorial'),
        ]

        for title, cat, style_name in sample_specs:
            fname = f"sample_{style_name}.png"
            fpath = os.path.join(artworks_dir, fname)
            art_img = create_sample_artwork(1000, 1000, title, art_type=style_name)
            art_img.save(fpath, format='PNG')

            PresetArtwork.objects.get_or_create(
                title=title,
                defaults={
                    'category': cat,
                    'image': f"sample_artworks/{fname}",
                    'is_active': True,
                }
            )

        self.stdout.write(self.style.SUCCESS("Sample artworks seeded successfully!"))
