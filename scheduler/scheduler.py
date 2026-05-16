"""
Market Intelligence Scout — APScheduler Setup

APScheduler's only job is to FIRE the trigger at the right time. The actual
pipeline runs in a Celery worker (`tasks.pipeline_tasks.run_scheduled_report`),
so:

  - API restarts no longer abort long-running scheduled jobs
  - Multiple API replicas can co-exist (scheduler dispatch is idempotent on
    job_id; the heavy work happens once on the worker)
  - Scheduled work shares the same retry / time-limit / metric machinery as
    user-triggered runs
"""

from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def init_scheduler() -> BackgroundScheduler:
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.start()
    logger.info("SCHEDULER — APScheduler started (dispatch-only mode)")
    return _scheduler


def get_scheduler() -> BackgroundScheduler:
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialised — call init_scheduler() first.")
    return _scheduler


def _enqueue_scheduled_report(job_id: int, company_name: str, email: str,
                              date_window_days: int) -> None:
    """Called by APScheduler when the trigger fires.

    Pushes a Celery task; returns immediately. The actual pipeline runs on
    the `scheduled` queue worker.
    """
    from tasks.pipeline_tasks import run_scheduled_report

    async_result = run_scheduled_report.apply_async(
        kwargs={
            "job_id": job_id,
            "company_name": company_name,
            "email": email,
            "date_window_days": date_window_days,
        },
        queue="scheduled",
        routing_key="scheduled.run",
    )
    logger.info("SCHEDULER — dispatched job %d → celery task %s",
                job_id, async_result.id)


def schedule_job(job_id: int, run_at: datetime, company_name: str, email: str,
                 date_window_days: int = 7) -> None:
    """Register a one-shot job that fires at `run_at` (UTC datetime) and
    dispatches the work to Celery."""
    sched = get_scheduler()
    sched.add_job(
        _enqueue_scheduled_report,
        trigger=DateTrigger(run_date=run_at, timezone="UTC"),
        id=f"job_{job_id}",
        kwargs={
            "job_id": job_id,
            "company_name": company_name,
            "email": email,
            "date_window_days": date_window_days,
        },
        misfire_grace_time=600,
        replace_existing=True,
    )
    logger.info("SCHEDULER — Job %d armed for %s UTC | %s → %s",
                job_id, run_at.isoformat(), company_name, email)


def cancel_job(job_id: int) -> bool:
    sched = get_scheduler()
    job = sched.get_job(f"job_{job_id}")
    if job:
        sched.remove_job(f"job_{job_id}")
        logger.info("SCHEDULER — Job %d cancelled", job_id)
        return True
    return False


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("SCHEDULER — Shut down")
