"""Celery task package — discovered via `app.celery_app` include."""

from tasks.pipeline_tasks import (  # noqa: F401
    cleanup_expired_results,
    recover_stale_jobs,
    run_market_pipeline,
    run_scheduled_report,
)
