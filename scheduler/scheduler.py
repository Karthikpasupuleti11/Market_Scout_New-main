"""
Market Intelligence Scout — APScheduler Setup
"""

import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def init_scheduler() -> BackgroundScheduler:
    """Create and start the APScheduler BackgroundScheduler."""
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.start()
    logger.info("SCHEDULER — APScheduler started")
    return _scheduler


def get_scheduler() -> BackgroundScheduler:
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialised — call init_scheduler() first.")
    return _scheduler


def schedule_job(job_id: int, run_at: datetime,
                 company_name: str, email: str) -> None:
    """
    Register a one-shot APScheduler trigger that enqueues a Celery task at `run_at` (UTC).

    Uses send_task by name so we never import scheduled_tasks (and Gmail) here.
    """
    from app.celery_app import celery

    task_name = "tasks.scheduled_tasks.run_scheduled_pipeline"

    def _enqueue():
        celery.send_task(task_name, args=[job_id, company_name, email])
        logger.info("SCHEDULER — Job %d enqueued to Celery | company=%s", job_id, company_name)

    sched = get_scheduler()
    sched.add_job(
        _enqueue,
        trigger=DateTrigger(run_date=run_at, timezone="UTC"),
        id=f"job_{job_id}",
        misfire_grace_time=300,
        replace_existing=True,
    )
    logger.info("SCHEDULER — Job %d scheduled for %s UTC | %s → %s",
                job_id, run_at.isoformat(), company_name, email)


def cancel_job(job_id: int) -> bool:
    """Remove a pending job from the scheduler. Returns True if found."""
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
