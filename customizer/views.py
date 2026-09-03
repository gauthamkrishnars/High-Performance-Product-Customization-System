import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.conf import settings
from PIL import Image

from .models import Product, ProductAngle, CustomizationArea, UserDesign, PresetArtwork, MockupJob
from .tasks import dispatch_mockup_job


class StudioView(View):
    """
    Main Interactive Customizer Studio interface.
    Loads product catalog, angles, print zones, and sample artwork gallery.
    """
    def get(self, request):
        products = Product.objects.filter(is_active=True).prefetch_related('angles__customization_area')
        
        # Select active product from query or default to first
        product_slug = request.GET.get('product')
        if product_slug:
            selected_product = products.filter(slug=product_slug).first() or products.first()
        else:
            selected_product = products.first()
            
        selected_angle = None
        if selected_product:
            angle_id = request.GET.get('angle')
            if angle_id:
                selected_angle = selected_product.angles.filter(id=angle_id).first()
            if not selected_angle:
                selected_angle = selected_product.default_angle

        presets = PresetArtwork.objects.filter(is_active=True)

        context = {
            'products': products,
            'selected_product': selected_product,
            'selected_angle': selected_angle,
            'presets': presets,
            'recent_jobs': MockupJob.objects.filter(status='COMPLETED')[:6],
        }
        return render(request, 'customizer/studio.html', context)


class CatalogView(View):
    """Product catalog overview showcasing printable apparel and goods."""
    def get(self, request):
        products = Product.objects.filter(is_active=True).prefetch_related('angles')
        return render(request, 'customizer/catalog.html', {'products': products})


class JobDetailView(View):
    """Dedicated high-resolution inspection and download page for rendered mockups."""
    def get(self, request, job_id):
        job = get_object_or_404(MockupJob, job_id=job_id)
        return render(request, 'customizer/job_detail.html', {'job': job})


@csrf_exempt
def upload_design_api(request):
    """API endpoint for drag-and-drop user artwork uploads."""
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST method allowed.")

    file = request.FILES.get('design_file')
    if not file:
        return JsonResponse({'success': False, 'error': 'No file uploaded.'}, status=400)

    # Validate image format and dimensions
    try:
        pil_img = Image.open(file)
        w, h = pil_img.size
        
        # Verify supported format
        if pil_img.format not in ['PNG', 'JPEG', 'JPG', 'WEBP', 'TIFF']:
            return JsonResponse({'success': False, 'error': f'Unsupported format: {pil_img.format}'}, status=400)

    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Invalid image data: {str(e)}'}, status=400)

    # Ensure session key exists for anonymous grouping
    if not request.session.session_key:
        request.session.create()

    user_design = UserDesign.objects.create(
        title=request.POST.get('title', file.name.split('.')[0]),
        image=file,
        width=w,
        height=h,
        file_size_bytes=file.size,
        session_key=request.session.session_key
    )

    return JsonResponse({
        'success': True,
        'design_id': user_design.id,
        'title': user_design.title,
        'url': user_design.image.url,
        'width': w,
        'height': h
    })


@csrf_exempt
def select_preset_api(request):
    """API endpoint to select a preset sample artwork."""
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST method allowed.")
        
    try:
        data = json.loads(request.body.decode('utf-8'))
        preset_id = data.get('preset_id')
        preset = get_object_or_404(PresetArtwork, id=preset_id)
        
        if not request.session.session_key:
            request.session.create()
            
        # Create a user design reference from preset
        pil_img = Image.open(preset.image.path)
        w, h = pil_img.size
        
        user_design = UserDesign.objects.create(
            title=preset.title,
            image=preset.image,
            width=w,
            height=h,
            file_size_bytes=preset.image.size,
            session_key=request.session.session_key
        )
        
        return JsonResponse({
            'success': True,
            'design_id': user_design.id,
            'title': user_design.title,
            'url': user_design.image.url,
            'width': w,
            'height': h
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
def render_mockup_api(request):
    """
    Submits a high-performance rendering job to the Celery pipeline.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST method allowed.")

    try:
        data = json.loads(request.body.decode('utf-8'))
        angle_id = data.get('angle_id')
        design_id = data.get('design_id')
        
        angle = get_object_or_404(ProductAngle, id=angle_id)
        design = get_object_or_404(UserDesign, id=design_id)
        
        # Parse transformation parameters
        scale = float(data.get('scale', 1.0))
        rotation = float(data.get('rotation', 0.0))
        offset_x = float(data.get('offset_x', 0.0))
        offset_y = float(data.get('offset_y', 0.0))
        blend_mode = data.get('blend_mode', 'MULTIPLY')
        displacement_intensity = float(data.get('displacement_intensity', 16.0))

        # Create MockupJob record
        job = MockupJob.objects.create(
            product_angle=angle,
            design=design,
            scale=scale,
            rotation=rotation,
            offset_x=offset_x,
            offset_y=offset_y,
            blend_mode=blend_mode,
            displacement_intensity=displacement_intensity,
            status='QUEUED',
            progress=5,
            status_message='Queued in rendering pipeline'
        )

        # Dispatch to Celery background worker or resilient synchronous fallback
        dispatch_info = dispatch_mockup_job(job.job_id)

        # Refresh job state in case it executed synchronously
        job.refresh_from_db()

        return JsonResponse({
            'success': True,
            'job_id': str(job.job_id),
            'status': job.status,
            'progress': job.progress,
            'status_message': job.status_message,
            'result_url': job.result_image.url if job.result_image else None,
            'dispatch': dispatch_info.get('dispatched_to')
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def job_status_api(request, job_id):
    """
    Polls the real-time status of a rendering job.
    """
    job = get_object_or_404(MockupJob, job_id=job_id)
    return JsonResponse({
        'job_id': str(job.job_id),
        'status': job.status,
        'progress': job.progress,
        'status_message': job.status_message,
        'result_url': job.result_image.url if job.result_image else None,
        'execution_time': job.execution_time_seconds,
        'error': job.error_log if job.status == 'FAILED' else None,
    })


def product_angles_api(request, product_id):
    """
    Returns angles, print zones, and quad perspective points for a product.
    """
    product = get_object_or_404(Product, id=product_id)
    angles_data = []
    
    for angle in product.angles.all():
        area = getattr(angle, 'customization_area', None)
        angles_data.append({
            'id': angle.id,
            'name': angle.name,
            'angle_type': angle.angle_type,
            'image_url': angle.base_image.url,
            'is_default': angle.is_default,
            'custom_area': {
                'name': area.name if area else 'Default Zone',
                'max_width_mm': area.max_width_mm if area else 350.0,
                'max_height_mm': area.max_height_mm if area else 450.0,
                'bounding_box': {
                    'left': area.bounding_left_pct if area else 25.0,
                    'top': area.bounding_top_pct if area else 25.0,
                    'width': area.bounding_width_pct if area else 50.0,
                    'height': area.bounding_height_pct if area else 50.0,
                },
                'quad_points': area.get_quad_points() if area else [
                    [25.0, 25.0], [75.0, 25.0], [75.0, 75.0], [25.0, 75.0]
                ],
                'blend_mode': area.blend_mode if area else 'MULTIPLY',
                'displacement_strength': area.displacement_strength if area else 16.0,
            } if area else None
        })
        
    return JsonResponse({
        'product': {
            'id': product.id,
            'name': product.name,
            'base_color': product.base_color,
            'color_name': product.color_name,
            'material': product.material,
            'price': str(product.price),
        },
        'angles': angles_data
    })
