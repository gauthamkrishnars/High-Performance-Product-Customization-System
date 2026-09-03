import os
import time
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='customizer.tasks.process_mockup_job')
def process_mockup_job(self, job_id):
    """
    Celery background worker task for high-resolution photorealistic rendering.
    Processes perspective warp, displacement mapping, and photometric blending.
    """
    from .models import MockupJob
    from .engine import render_custom_mockup

    try:
        job = MockupJob.objects.get(job_id=job_id)
    except MockupJob.DoesNotExist:
        logger.error(f"MockupJob {job_id} not found.")
        return {'success': False, 'error': f"Job {job_id} does not exist"}

    start_time = time.perf_counter()
    
    try:
        # Step 1: Initializing Job
        job.status = 'PROCESSING'
        job.progress = 15
        job.status_message = 'Loading product surface geometry'
        job.save(update_fields=['status', 'progress', 'status_message', 'updated_at'])

        angle = job.product_angle
        custom_area = getattr(angle, 'customization_area', None)
        
        if not custom_area:
            raise ValueError(f"CustomizationArea setup missing for product angle: {angle.name}")

        base_img_path = angle.base_image.path
        if not os.path.exists(base_img_path):
            raise FileNotFoundError(f"Base image file missing on disk: {base_img_path}")

        if not job.design or not job.design.image:
            raise ValueError("No user design attached to this mockup job.")

        design_img_path = job.design.image.path
        if not os.path.exists(design_img_path):
            raise FileNotFoundError(f"Design image file missing on disk: {design_img_path}")

        # Step 2: Perspective Alignment
        job.progress = 40
        job.status_message = 'Calculating perspective homography transformation'
        job.save(update_fields=['progress', 'status_message', 'updated_at'])

        quad_points = custom_area.get_quad_points()
        
        # Prepare output destination
        output_filename = f"render_{job.job_id}.jpg"
        rel_output_path = os.path.join('rendered_mockups', output_filename)
        abs_output_path = os.path.join(settings.MEDIA_ROOT, rel_output_path)

        # Step 3: Displacement and Conformation
        job.progress = 70
        job.status_message = 'Synthesizing fabric fold displacement and lighting modulation'
        job.save(update_fields=['progress', 'status_message', 'updated_at'])

        render_res = render_custom_mockup(
            base_image_path=base_img_path,
            design_image_path=design_img_path,
            quad_points=quad_points,
            output_path=abs_output_path,
            scale=job.scale,
            rotation=job.rotation,
            offset_x=job.offset_x,
            offset_y=job.offset_y,
            blend_mode=job.blend_mode,
            displacement_intensity=job.displacement_intensity,
            texture_depth=custom_area.texture_depth,
            max_resolution=settings.MOCKUP_MAX_OUTPUT_RESOLUTION[0]
        )

        if not render_res['success']:
            raise RuntimeError(render_res['error'])

        # Step 4: Finalizing Output
        elapsed = time.perf_counter() - start_time
        job.result_image = rel_output_path
        job.status = 'COMPLETED'
        job.progress = 100
        job.status_message = f"Render complete ({render_res['execution_time_ms']} ms)"
        job.execution_time_seconds = round(elapsed, 3)
        job.save(update_fields=['result_image', 'status', 'progress', 'status_message', 'execution_time_seconds', 'updated_at'])

        logger.info(f"MockupJob {job_id} successfully finished in {elapsed:.2f}s")
        return {
            'success': True,
            'job_id': str(job.job_id),
            'result_url': job.result_image.url,
            'execution_time': elapsed
        }

    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        job.status = 'FAILED'
        job.progress = 100
        job.status_message = 'Rendering failed'
        job.error_log = str(exc)
        job.execution_time_seconds = round(elapsed, 3)
        job.save(update_fields=['status', 'progress', 'status_message', 'error_log', 'execution_time_seconds', 'updated_at'])
        
        logger.error(f"MockupJob {job_id} failed: {exc}", exc_info=True)
        return {
            'success': False,
            'job_id': str(job.job_id),
            'error': str(exc)
        }


def dispatch_mockup_job(job_id):
    """
    Smart job dispatcher:
    Attempts to enqueue to Celery Redis cluster.
    If Redis/Celery worker is offline or unavailable, automatically falls back
    to immediate local thread execution so the user never encounters broken jobs.
    """
    try:
        # Check if Redis connection is responsive
        from customizer_project.celery import app as celery_app
        async_result = process_mockup_job.delay(str(job_id))
        return {'dispatched_to': 'celery', 'task_id': async_result.id}
    except Exception as e:
        logger.warning(f"Celery queue unavailable ({e}), executing in immediate synchronous worker.")
        # Fallback to local execution
        res = process_mockup_job(str(job_id))
        return {'dispatched_to': 'synchronous', 'result': res}
