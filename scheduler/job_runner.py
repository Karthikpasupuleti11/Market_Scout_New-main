"""
Deprecated — pipeline execution for scheduled jobs now lives in the Celery
task `tasks.pipeline_tasks.run_scheduled_report`. APScheduler dispatches to
Celery via `scheduler.scheduler._enqueue_scheduled_report`.

This module is kept only so external callers that still import
`run_scheduled_job` get a clear redirect instead of an ImportError.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run_scheduled_job(*args, **kwargs):
    """Back-compat shim — dispatch to Celery instead of running inline."""
    from tasks.pipeline_tasks import run_scheduled_report

    logger.warning(
        "SCHEDULER — run_scheduled_job() is deprecated; dispatching to Celery"
    )
    return run_scheduled_report.apply_async(
        kwargs={
            "job_id": kwargs.get("job_id"),
            "company_name": kwargs.get("company_name"),
            "email": kwargs.get("email"),
            "date_window_days": kwargs.get("date_window_days", 7),
        },
        queue="scheduled",
        routing_key="scheduled.run",
    )
