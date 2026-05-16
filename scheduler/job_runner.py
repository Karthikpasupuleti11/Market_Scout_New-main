"""
Market Intelligence Scout — Scheduled Job Runner

Executes in a background thread when APScheduler fires a job.
"""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def run_scheduled_job(job_id: int, company_name: str, email: str, db_factory, graph):
    """
    1. Mark job as 'running'
    2. Invoke the LangGraph pipeline
    3. Save the report to DB
    4. Send email (HTML + PDF)
    5. Mark job as 'done'

    On any exception: mark job as 'failed' with error message.
    """
    from database import crud
    from scheduler.email_service import send_report_email

    db = db_factory()
    try:
        # ── 1. Mark running ──────────────────────────────────────────
        crud.update_job_status(db, job_id, status="running")
        logger.info("SCHEDULER — Job %d started | company=%s | email=%s",
                    job_id, company_name, email)

        # ── 2. Run pipeline ──────────────────────────────────────────
        result = asyncio.run(graph.ainvoke({"company_name": company_name}))
        report = result.get("synthesis_report", {})

        if not report:
            raise RuntimeError("Pipeline produced no synthesis report.")

        # ── 3. Save to DB ────────────────────────────────────────────
        saved_report = crud.save_report(db, company_name, report)

        # ── 4. Send email ────────────────────────────────────────────
        send_report_email(report, company_name, email)

        # ── 5. Mark done ─────────────────────────────────────────────
        crud.update_job_status(db, job_id,
                               status="done",
                               report_id=saved_report.id)
        logger.info("SCHEDULER — Job %d completed | report_id=%d", job_id, saved_report.id)

    except Exception as exc:
        error_msg = str(exc)[:500]
        logger.error("SCHEDULER — Job %d FAILED: %s", job_id, error_msg, exc_info=True)
        try:
            crud.update_job_status(db, job_id, status="failed", error_msg=error_msg)
        except Exception:
            pass
    finally:
        db.close()
