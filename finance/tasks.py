"""
Celery Tasks for background CSV processing.
"""
from celery import shared_task
from finance.reconciliation import run_reconciliation


@shared_task(bind=True, name='finance.tasks.async_reconciliation')
def async_reconciliation(self):
    """Run reconciliation as a background task."""
    result = run_reconciliation()
    return result
