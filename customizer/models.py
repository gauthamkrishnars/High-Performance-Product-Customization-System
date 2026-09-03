import uuid
import json
from django.db import models
from django.utils.text import slugify


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('apparel', 'Apparel & Streetwear'),
        ('headwear', 'Headwear & Caps'),
        ('accessories', 'Bags & Accessories'),
        ('drinkware', 'Ceramics & Drinkware'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='apparel')
    description = models.TextField(blank=True)
    base_color = models.CharField(max_length=50, default='#1E2022')
    color_name = models.CharField(max_length=50, default='Vintage Washed Black')
    material = models.CharField(max_length=100, default='100% Ring-Spun Cotton (240 GSM)')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=38.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def default_angle(self):
        return self.angles.filter(is_default=True).first() or self.angles.first()


class ProductAngle(models.Model):
    ANGLE_CHOICES = [
        ('front', 'Front Perspective'),
        ('back', 'Back Perspective'),
        ('side', 'Side / Sleeve Perspective'),
        ('folded', 'Folded Studio Flatlay'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='angles')
    angle_type = models.CharField(max_length=30, choices=ANGLE_CHOICES, default='front')
    name = models.CharField(max_length=100, help_text='e.g., Front Chest View')
    base_image = models.ImageField(upload_to='base_products/')
    displacement_map = models.ImageField(upload_to='base_products/displacement/', blank=True, null=True)
    is_default = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.product.name} ({self.get_angle_type_display()})"


class CustomizationArea(models.Model):
    BLEND_CHOICES = [
        ('MULTIPLY', 'Photometric Multiply (Natural Shadow Pass)'),
        ('OVERLAY', 'Photometric Overlay (Contrast Preservation)'),
        ('SOFT_LIGHT', 'Soft Light (Subtle Texture Infusion)'),
        ('NORMAL', 'Standard Alpha Composite'),
    ]

    angle = models.OneToOneField(ProductAngle, on_delete=models.CASCADE, related_name='customization_area')
    name = models.CharField(max_length=100, default='Primary Print Zone')
    
    # Real physical specifications
    max_width_mm = models.FloatField(default=350.0, help_text='Print bed width in millimeters')
    max_height_mm = models.FloatField(default=450.0, help_text='Print bed height in millimeters')
    
    # 2D Bounding box as percentages of base image (0.0 to 100.0)
    bounding_left_pct = models.FloatField(default=30.0)
    bounding_top_pct = models.FloatField(default=26.0)
    bounding_width_pct = models.FloatField(default=40.0)
    bounding_height_pct = models.FloatField(default=48.0)
    
    # 4-Point Perspective Quadrilateral in normalized space [ [x1,y1], [x2,y2], [x3,y3], [x4,y4] ]
    # Order: Top-Left, Top-Right, Bottom-Right, Bottom-Left (0.0 to 100.0)
    quad_points_json = models.TextField(
        default='[[30.0, 26.0], [70.0, 26.0], [70.0, 74.0], [30.0, 74.0]]',
        help_text='JSON array of 4 perspective corner points (top-left, top-right, bottom-right, bottom-left)'
    )
    
    displacement_strength = models.FloatField(default=16.0, help_text='Fold and wrinkle deformation intensity')
    texture_depth = models.FloatField(default=1.3, help_text='Shadow and highlight texture contrast multiplier')
    blend_mode = models.CharField(max_length=20, choices=BLEND_CHOICES, default='MULTIPLY')

    def get_quad_points(self):
        try:
            return json.loads(self.quad_points_json)
        except Exception:
            return [
                [self.bounding_left_pct, self.bounding_top_pct],
                [self.bounding_left_pct + self.bounding_width_pct, self.bounding_top_pct],
                [self.bounding_left_pct + self.bounding_width_pct, self.bounding_top_pct + self.bounding_height_pct],
                [self.bounding_left_pct, self.bounding_top_pct + self.bounding_height_pct]
            ]

    def __str__(self):
        return f"{self.name} for {self.angle}"


class UserDesign(models.Model):
    title = models.CharField(max_length=200, default='Custom Artwork')
    image = models.ImageField(upload_to='user_designs/')
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    file_size_bytes = models.PositiveIntegerField(default=0)
    session_key = models.CharField(max_length=100, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class PresetArtwork(models.Model):
    CATEGORY_CHOICES = [
        ('streetwear', 'Streetwear & Typographic'),
        ('minimal', 'Minimalist & Monoline'),
        ('editorial', 'Editorial & Abstract'),
        ('vintage', 'Vintage Emblem & Badge'),
    ]

    title = models.CharField(max_length=150)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='streetwear')
    image = models.ImageField(upload_to='sample_artworks/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'title']

    def __str__(self):
        return self.title


class MockupJob(models.Model):
    STATUS_CHOICES = [
        ('QUEUED', 'Queued in Worker Pipeline'),
        ('PROCESSING', 'Processing OpenCV Conformation'),
        ('COMPLETED', 'Render Complete'),
        ('FAILED', 'Rendering Failed'),
    ]

    job_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    product_angle = models.ForeignKey(ProductAngle, on_delete=models.CASCADE, related_name='mockup_jobs')
    design = models.ForeignKey(UserDesign, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Transformation parameters
    scale = models.FloatField(default=1.0)
    rotation = models.FloatField(default=0.0)
    offset_x = models.FloatField(default=0.0)  # Offset in percentage of print zone
    offset_y = models.FloatField(default=0.0)
    blend_mode = models.CharField(max_length=20, default='MULTIPLY')
    displacement_intensity = models.FloatField(default=16.0)
    
    # Status & execution tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='QUEUED')
    progress = models.PositiveIntegerField(default=0)
    status_message = models.CharField(max_length=255, default='Job initialized')
    result_image = models.ImageField(upload_to='rendered_mockups/', blank=True, null=True)
    execution_time_seconds = models.FloatField(default=0.0)
    error_log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"MockupJob {self.job_id} ({self.status} - {self.progress}%)"
