"""
Market Intelligence Scout — Celery pipeline tasks.

Executed by Celery workers; enqueued from FastAPI via ``tasks.pipeline_tasks``.
"""

import logging
import time

from app.celery_app import celery

logger = logging.getLogger(__name__)


def _active_pipelines_gauge():
    """Lazy import so workers can load tasks without eager metrics init."""
    from observability.metrics import ACTIVE_PIPELINES
    return ACTIVE_PIPELINES


def _update_progress(task_ref, node_name: str, status: str, elapsed: float = 0):
    """Push progress metadata into the Celery task state (polled by GET /task/{id})."""
    try:
        current = task_ref.backend.get_task_meta(task_ref.request.id)
        progress = current.get("result", {}) if current.get("status") == "PROGRESS" else {}
        if not isinstance(progress, dict):
            progress = {}

        stages = progress.get("stages", {})
        stages[node_name] = {"status": status, "elapsed": round(elapsed, 2)}

        task_ref.update_state(
            state="PROGRESS",
            meta={
                "stages": stages,
                "current_node": node_name,
                "current_status": status,
            },
        )
    except Exception as exc:
        logger.debug("Progress update failed (non-fatal): %s", exc)


@celery.task(
    bind=True,
    name="tasks.pipeline_tasks.run_pipeline_task",
    max_retries=1,
    default_retry_delay=10,
    acks_late=True,
)
def run_pipeline_task(self, company_name: str, date_window_days: int = 7):
    """Execute the full LangGraph pipeline inside a Celery worker."""
    task_id = self.request.id
    logger.info("CELERY TASK %s — Starting pipeline for '%s'", task_id, company_name)

    gauge = _active_pipelines_gauge()
    gauge.inc()
    try:
        return _run_pipeline_body(self, company_name, date_window_days, task_id)
    finally:
        gauge.dec()


def _run_pipeline_body(task_ref, company_name: str, date_window_days: int, task_id: str):
    """Inner pipeline logic (ACTIVE_PIPELINES tracked by caller)."""
    self = task_ref
    start_time = time.time()

    self.update_state(
        state="PROGRESS",
        meta={
            "stages": {},
            "current_node": "initializing",
            "current_status": "start",
            "company_name": company_name,
        },
    )

    try:
        from graph.builder import build_graph
        from database.session import SessionLocal
        from database import crud

        graph = build_graph()

        def progress_callback(node_name: str, status: str, elapsed: float = 0):
            _update_progress(self, node_name, status, elapsed)

        result = graph.invoke({
            "company_name": company_name,
            "date_window_days": date_window_days,
            "_progress_callback": progress_callback,
        })

        report = result.get("synthesis_report", {})

        if not report:
            raise RuntimeError("Pipeline produced no report.")

        from observability.pipeline_metrics import record_pipeline_completion
        record_pipeline_completion(company_name, report, failed=False)

        db = None
        try:
            db = SessionLocal()
            crud.save_report(db, company_name, report)
            logger.info("CELERY TASK %s — Report saved to PostgreSQL", task_id)
        except Exception as db_exc:
            logger.warning("CELERY TASK %s — DB persistence failed (non-fatal): %s", task_id, db_exc)
        finally:
            if db is not None:
                db.close()

        from cache.report_cache import set_report_in_redis, build_task_response

        set_report_in_redis(company_name, date_window_days, report)

        elapsed_total = round(time.time() - start_time, 2)
        response = build_task_response(
            report, company_name, elapsed_seconds=elapsed_total
        )

        logger.info(
            "CELERY TASK %s — Complete: %d features, %d sources, %.1fs",
            task_id,
            len(response["features"]),
            response["total_sources_analysed"],
            elapsed_total,
        )

        return response

    except Exception as exc:
        elapsed_total = round(time.time() - start_time, 2)
        logger.error("CELERY TASK %s — Failed after %.1fs: %s", task_id, elapsed_total, exc, exc_info=True)

        try:
            from observability.pipeline_metrics import record_pipeline_completion
            record_pipeline_completion(company_name, {}, failed=True)
        except Exception:
            pass

        error_str = str(exc)
        is_transient = any(kw in error_str.lower() for kw in ["timeout", "429", "rate limit", "connection"])
        if is_transient and self.request.retries < self.max_retries:
            logger.info("CELERY TASK %s — Retrying (attempt %d)", task_id, self.request.retries + 1)
            raise self.retry(exc=exc)

        raise


@celery.task(
    name="tasks.pipeline_tasks.serve_cached_report_task",
    acks_late=True,
)
def serve_cached_report_task(
    report_response: dict,
    cache_source: str = "redis",
):
    """Return a pre-built report payload (instant SUCCESS for cache hits)."""
    logger.info("CELERY TASK — Serving cached report (source=%s)", cache_source)
    gauge = _active_pipelines_gauge()
    gauge.inc()
    try:
        out = dict(report_response)
        out.setdefault("from_cache", True)
        out.setdefault("cache_source", cache_source)
        return out
    finally:
        gauge.dec()
