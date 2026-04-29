# Celery config — only used when running with Redis locally via docker-compose.
# Not loaded during Railway deployment (no REDIS_URL, no celery in requirements).
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    from celery import Celery
    app = Celery('pilgrim_finance')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()
except ImportError:
    app = None
