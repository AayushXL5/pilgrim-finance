import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

if os.environ.get('REDIS_URL'):
    from celery import Celery

    app = Celery('pilgrim_finance')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()
else:
    # Redis is not configured — create a minimal no-op Celery app so that
    # imports of `celery_app` and `@shared_task` decorators don't crash the
    # Django process.  Tasks will never be dispatched to a worker; callers
    # that need async behaviour should check for REDIS_URL themselves.
    from celery import Celery

    app = Celery('pilgrim_finance')
    # Deliberately leave the broker/backend unconfigured so no connection is
    # attempted at import time.  The in-memory transport is safe for this.
    app.conf.update(
        broker_url='memory://',
        result_backend='cache+memory://',
    )
