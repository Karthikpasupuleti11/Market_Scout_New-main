import asyncio
import logging

from app.celery_app import celery
from graph.builder import build_graph
from database.session import SessionLocal
from database import crud

logger = logging.getLogger(__name__)

graph = build_graph()


@celery.task(bind=True)
def run_scheduled_pipeline(self, job_id: int, company_name: str, email: str):
    from scheduler.email_service import send_report_email

    db = SessionLocal()
    try:
        crud.update_job_status(db, job_id, status="running")
        logger.info("SCHEDULED TASK — Job %d started | company=%s | email=%s",
                    job_id, company_name, email)

        result = asyncio.run(graph.ainvoke({"company_name": company_name}))
        report = result.get("synthesis_report", {})

        if not report:
            raise RuntimeError("Pipeline produced no synthesis report.")

        features = report.get("features", [])
        if not features:
            raise RuntimeError(f"No features extracted for '{company_name}'. Report not saved.")

        saved_report = crud.save_report(db, company_name, report)
        send_report_email(report, company_name, email)

        crud.update_job_status(db, job_id, status="done", report_id=saved_report.id)
        logger.info("SCHEDULED TASK — Job %d completed | report_id=%d", job_id, saved_report.id)

        return {"job_id": job_id, "report_id": saved_report.id, "status": "done"}

    except Exception as exc:
        error_msg = str(exc)[:500]
        logger.error("SCHEDULED TASK — Job %d FAILED: %s", job_id, error_msg, exc_info=True)
        try:
            crud.update_job_status(db, job_id, status="failed", error_msg=error_msg)
        except Exception:
            pass
        raise
    finally:
        db.close()
