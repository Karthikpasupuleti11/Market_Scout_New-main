"""
Trivial Celery task that immediately returns a cached report.

This exists so the frontend polling mechanism receives a cached payload
in the exact same task-result format as a live pipeline run.
"""

from app.celery_app import celery


@celery.task(bind=True)
def serve_cached_report_task(self, report_data: dict):
    """Return the cached report as a Celery task result.
    
    The frontend polls GET /task-status/{task_id} and expects
    a SUCCESS status with a result payload — this satisfies that
    contract without re-running the pipeline.
    """
    return report_data
