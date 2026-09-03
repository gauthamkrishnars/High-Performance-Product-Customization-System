"""
ASGI config for customizer_project project.
"""

import os
import shutil
from pathlib import Path
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customizer_project.settings')

# Vercel Serverless Bootstrapper
IS_VERCEL = bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))

if IS_VERCEL:
    base_dir = Path(__file__).resolve().parent.parent
    
    # 1. Prepare /tmp/media
    tmp_media = Path('/tmp/media')
    tmp_media.mkdir(parents=True, exist_ok=True)
    
    bundled_media = base_dir / 'media'
    if bundled_media.exists():
        for sub in ['base_products', 'sample_artworks', 'rendered_mockups', 'user_designs']:
            src_sub = bundled_media / sub
            dst_sub = tmp_media / sub
            dst_sub.mkdir(parents=True, exist_ok=True)
            if src_sub.exists():
                for item in src_sub.glob('*.*'):
                    target = dst_sub / item.name
                    if not target.exists():
                        try:
                            shutil.copyfile(item, target)
                        except Exception:
                            pass

    # 2. Prepare /tmp/db.sqlite3 if no external PostgreSQL is defined
    has_postgres = any(
        os.environ.get(k) and ('postgres://' in os.environ.get(k) or 'postgresql://' in os.environ.get(k))
        for k in ['DATABASE_URL', 'POSTGRES_URL', 'POSTGRES_PRISMA_URL', 'DATABASE1_URL']
    )
    
    if not has_postgres:
        tmp_db = Path('/tmp/db.sqlite3')
        template_db = base_dir / 'db_template.sqlite3'
        
        if not tmp_db.exists() or tmp_db.stat().st_size == 0:
            if template_db.exists() and template_db.stat().st_size > 0:
                try:
                    shutil.copyfile(template_db, tmp_db)
                except Exception as e:
                    print("Failed to copy template database to /tmp:", e)

application = get_asgi_application()
app = application
