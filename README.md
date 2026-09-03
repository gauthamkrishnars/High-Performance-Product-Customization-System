# High-Performance Product Customization System

A commercial-grade photorealistic product customization platform powered by **Python, Django, OpenCV, NumPy, Pillow, and Celery**.

---

## Architectural Overview

Unlike typical web mockups that overlay flat 2D graphics rigidly onto images, this engine performs mathematical 3D perspective homography, extracts real fabric wrinkles using Sobel directional gradients, deforms graphics via bicubic remap, and blends inks using photometric lighting modulation.

```
Uploaded Graphic (PNG / SVG / JPG)
        │
        ▼
[Perspective Alignment]  ──►  cv2.getPerspectiveTransform & warpPerspective (Lanczos-4)
        │
        ▼
[Displacement Mapping]  ──►  CIELAB Lightness -> High-Pass Filter -> Sobel Vector Field (dx, dy)
        │
        ▼
[Fabric Conformation]   ──►  cv2.remap (Bicubic Non-Linear Distortion along Wrinkles)
        │
        ▼
[Photometric Blending]  ──►  Multiply / Overlay / Soft Light + Ambient Crevice Shadows
        │
        ▼
Final 2400x2400 High-Resolution Output (Celery Worker Queue)
```

---

## Key Features

1. **Sub-Pixel 4-Point Homography**:
   - Maps 2D rectangular art into non-planar 3D quadrilaterals `[top-left, top-right, bottom-right, bottom-left]`.
   - Accommodates natural garment drape, drop-shoulder silhouettes, sleeve angles, and tilted flatlays.

2. **Automatic Surface Texture & Wrinkle Extraction**:
   - Analyzes substrate photography in CIELAB space.
   - Extracts micro-weaves and macro-folds using high-pass filters.
   - Generates directional gradient normals using 5x5 Sobel convolution kernels.

3. **Non-Linear Bicubic Remap**:
   - Deforms graphic pixels along displacement vector fields.
   - Graphics realistically bend over chest contours and fabric folds without pixel tearing.

4. **Photometric Ink Blending Modes**:
   - Multiply, Overlay, and Soft Light algorithms.
   - Fabric highlight ridges illuminate the ink and crevice shadows darken the ink for authentic direct-to-garment (DTG) appearance.

5. **Distributed Asynchronous Concurrency**:
   - Celery + Redis task queue for high-throughput batch rendering.
   - Resilient synchronous worker fallback for standalone local environments.

6. **Interactive 2D Client Studio Canvas**:
   - Drag-to-reposition, mousewheel zoom, rotation, and print boundary indicators.
   - Real-time client preview + instant 2400px server rendering.

---

## Directory Structure

```
High-Performance Product Customization System/
├── manage.py
├── requirements.txt
├── customizer_project/
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py            # Celery distributed task queue configuration
│   ├── settings.py          # Unified settings (Media, Celery, Image Engine)
│   ├── urls.py              # Root URL router
│   └── wsgi.py
├── customizer/
│   ├── __init__.py
│   ├── admin.py             # Admin models with inline print bed configuration
│   ├── apps.py
│   ├── models.py            # Product, ProductAngle, CustomizationArea, MockupJob
│   ├── tasks.py             # Celery background rendering task & resilient dispatcher
│   ├── views.py             # Studio, Catalog, Upload API, Render API, Job Poller
│   ├── urls.py
│   ├── engine/              # Computer Vision Core
│   │   ├── __init__.py
│   │   ├── perspective.py   # 4-point homography & geometric matrix warping
│   │   ├── displacement.py  # Sobel fold extraction & remap vector field
│   │   ├── blending.py      # Photometric Multiply & Overlay composite
│   │   └── pipeline.py      # High-performance pipeline execution
│   └── management/
│       └── commands/
│           └── seed_catalog.py # Seeds base photography, print zones, & presets
├── static/
│   ├── css/
│   │   └── customizer.css   # Modern high-contrast dark theme & sliders
│   └── js/
│       └── studio.js        # Interactive HTML5 canvas, drag/scale, & polling
├── templates/
│   ├── base.html            # Layout, SEO, JSON-LD, and legal modals
│   └── customizer/
│       ├── studio.html      # Interactive customizer workstation
│       ├── catalog.html     # Product and substrate catalog
│       └── job_detail.html  # Standalone high-res mockup inspector
└── media/                   # Base products, sample artworks, and rendered mockups
```

---

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Apply Database Migrations
```bash
python manage.py makemigrations customizer
python manage.py migrate
```

### 3. Seed Base Products & Sample Artworks
```bash
python manage.py seed_catalog
```

### 4. (Optional) Launch Celery Worker for Distributed Concurrency
If using Redis on `localhost:6379`:
```bash
celery -A customizer_project worker --loglevel=info
```
*Note: If Celery or Redis is not active, the system automatically uses its built-in synchronous rendering pipeline.*

### 5. Start Development Server
```bash
python manage.py runserver 127.0.0.1:8000
```

Open `http://127.0.0.1:8000/` in your browser to launch the Customizer Studio.
