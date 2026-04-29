"""Background tasks — requires celery + redis (optional)."""

try:
    from celery import shared_task
    from finance.reconciliation import run_reconciliation

    @shared_task(bind=True, name='finance.tasks.async_reconciliation')
    def async_reconciliation(self):
        return run_reconciliation()
except ImportError:
    pass
