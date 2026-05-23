import asyncio
import logging

from app.celery_app import celery
from graph.builder import build_graph
from database.session import SessionLocal
from database import crud
from scheduler.email_service import send_report_email

logger = logging.getLogger(__name__)

graph = build_graph()


@celery.task(bind=True)
def run_scheduled_pipeline(self, job_id: int, company_name: str, email: str):
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
            # Graceful outcome — pipeline ran fine, just no recent signals found
            logger.info("SCHEDULED TASK — Job %d completed with no features for '%s' "
                        "(likely no recent news within the time window)", job_id, company_name)
            no_data_msg = (
                f"Analysis completed for '{company_name}', but no recent technical signals "
                f"were found within the configured time window. "
                f"This is normal — try again later or widen the recency window."
            )
            crud.update_job_status(db, job_id, status="no_data", error_msg=no_data_msg)
            # Still send an email so the user knows it ran
            try:
                send_report_email(
                    {"executive_summary": no_data_msg, "features": [], "all_sources": []},
                    company_name,
                    email,
                )
            except Exception:
                logger.warning("SCHEDULED TASK — Could not send no-data email for Job %d", job_id)
            return {"job_id": job_id, "report_id": None, "status": "no_data"}

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
