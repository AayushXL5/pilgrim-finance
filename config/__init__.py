import os

if os.environ.get('REDIS_URL'):
    from .celery import app as celery_app
    __all__ = ['celery_app']
else:
    __all__ = []
