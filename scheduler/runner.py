"""
Standalone APScheduler process.

Loads all pending ScheduledJob rows from the DB, arms APScheduler triggers
for them, and stays alive. When a trigger fires it dispatches a Celery task —
no pipeline work happens in this process.

Run as: `python -m scheduler.runner`
"""

from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _rearm_pending_jobs(sched_module) -> int:
    """Walk DB for any pending jobs not yet armed and arm APScheduler triggers.

    Idempotent — `replace_existing=True` on schedule_job means re-arming an
    already-armed job is a no-op.
    """
    from database.scheduled_job_model import ScheduledJob
    from database.session import SessionLocal

    db = SessionLocal()
    armed = 0
    try:
        now = datetime.now(timezone.utc)
        pending = (
            db.query(ScheduledJob)
            .filter(
                ScheduledJob.status == "pending",
                ScheduledJob.scheduled_at >= now,
            )
            .all()
        )
        sched = sched_module.get_scheduler()
        pending_ids = {job.id for job in pending}
        for job in pending:
            if sched.get_job(f"job_{job.id}") is not None:
                continue
            sched_module.schedule_job(
                job_id=job.id,
                run_at=job.scheduled_at,
                company_name=job.company_name,
                email=job.email,
            )
            armed += 1
        if armed:
            logger.info("RUNNER — armed %d new pending job(s)", armed)

        # Garbage-collect APScheduler triggers whose DB rows are gone/cancelled
        removed = 0
        for j in list(sched.get_jobs()):
            if not j.id.startswith("job_"):
                continue
            try:
                jid = int(j.id.split("_", 1)[1])
            except (IndexError, ValueError):
                continue
            if jid not in pending_ids:
                sched.remove_job(j.id)
                removed += 1
        if removed:
            logger.info("RUNNER — pruned %d stale trigger(s)", removed)
        return armed
    finally:
        db.close()


def main() -> None:
    from database.models import Base
    from database.session import engine
    from scheduler import scheduler as sched_module

    Base.metadata.create_all(bind=engine)

    sched_module.init_scheduler()
    _rearm_pending_jobs(sched_module)

    stop = {"flag": False}

    def _shutdown(signum, frame):
        logger.info("RUNNER — received signal %s, shutting down", signum)
        stop["flag"] = True

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("RUNNER — APScheduler standalone running. Ctrl+C to exit.")
    POLL_INTERVAL = 10  # seconds — pick up new jobs created via the API
    last_poll = 0.0
    try:
        while not stop["flag"]:
            now_ts = time.time()
            if now_ts - last_poll >= POLL_INTERVAL:
                try:
                    _rearm_pending_jobs(sched_module)
                except Exception as exc:
                    logger.warning("RUNNER — rearm sweep failed: %s", exc)
                last_poll = now_ts
            time.sleep(1)
    finally:
        sched_module.shutdown_scheduler()
        logger.info("RUNNER — stopped")


if __name__ == "__main__":
    main()
