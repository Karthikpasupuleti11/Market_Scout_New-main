"""
Market Intelligence Scout — Celery Tasks

Contains the pipeline execution task that runs inside Celery workers.
FastAPI enqueues this task and returns a task_id immediately.
"""

import logging
import time
import json
from datetime import datetime, timezone

from celery import states
from celery_app import celery_app

logger = logging.getLogger(__name__)


def _update_progress(task_ref, node_name: str, status: str, elapsed: float = 0):
    """Push progress metadata into the Celery task state.

    This is read by the FastAPI /task/{id} polling endpoint.
    """
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


@celery_app.task(
    bind=True,
    name="celery_app.tasks.run_pipeline_task",
    max_retries=1,
    default_retry_delay=10,
    acks_late=True,
)
def run_pipeline_task(self, company_name: str, date_window_days: int = 7):
    """Execute the full LangGraph pipeline inside a Celery worker.

    Returns a JSON-serializable dict with the report data.
    """
    task_id = self.request.id
    logger.info("CELERY TASK %s — Starting pipeline for '%s'", task_id, company_name)

    # ── Update state to PROGRESS ──────────────────────────────────
    self.update_state(
        state="PROGRESS",
        meta={
            "stages": {},
            "current_node": "initializing",
            "current_status": "start",
            "company_name": company_name,
        },
    )

    start_time = time.time()

    try:
        # ── Lazy imports to avoid circular imports ────────────────
        # These are imported inside the task function so that the
        # celery_app module can be imported by FastAPI without
        # pulling in the entire pipeline dependency tree at import time.
        from graph.builder import build_graph
        from database.session import SessionLocal
        from database import crud
        from observability.metrics import (
            PIPELINE_RUNS,
            ACTIVE_PIPELINES,
            FEATURES_EXTRACTED,
            FEATURES_VERIFIED,
            CONFIDENCE_SCORE,
            SOURCES_ANALYSED,
        )

        ACTIVE_PIPELINES.inc()

        # ── Build graph (stateless, safe per-task) ────────────────
        graph = build_graph()

        # ── Progress callback wired to Celery state ──────────────
        def progress_callback(node_name: str, status: str, elapsed: float = 0):
            _update_progress(self, node_name, status, elapsed)

        # ── Execute pipeline ──────────────────────────────────────
        result = graph.invoke({
            "company_name": company_name,
            "date_window_days": date_window_days,
            "_progress_callback": progress_callback,
        })

        report = result.get("synthesis_report", {})

        if not report:
            raise RuntimeError("Pipeline produced no report.")

        # ── Record Prometheus metrics ─────────────────────────────
        error_msg = result.get("error") or report.get("metadata", {}).get("error")
        features = report.get("features", [])

        if error_msg and not features:
            PIPELINE_RUNS.labels(status="error").inc()
        else:
            PIPELINE_RUNS.labels(status="completed").inc()

        for f in features:
            cat = f.get("category", "unknown") if isinstance(f, dict) else "unknown"
            FEATURES_EXTRACTED.labels(company=company_name, category=cat).inc()
            score = f.get("confidence_score", 0) if isinstance(f, dict) else 0
            CONFIDENCE_SCORE.observe(score)

        FEATURES_VERIFIED.labels(company=company_name).inc(
            report.get("total_features_verified", 0)
        )
        SOURCES_ANALYSED.observe(report.get("total_sources_analysed", 0))

        # ── Persist to PostgreSQL ─────────────────────────────────
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

        # ── Build serializable response ───────────────────────────
        safe_features = []
        for i, f in enumerate(features):
            if isinstance(f, dict):
                safe_features.append({
                    "rank": f.get("rank", i + 1),
                    "title": f.get("title") or f.get("feature_title") or f.get("feature_summary", ""),
                    "description": f.get("description") or f.get("feature_summary") or f.get("feature_text", ""),
                    "category": f.get("category"),
                    "confidence_score": f.get("confidence_score") or f.get("confidence"),
                    "impact_assessment": f.get("impact_assessment"),
                    "source_url": f.get("source_url") or f.get("primary_url") or f.get("url"),
                    "source_count": f.get("source_count"),
                    "key_metrics": f.get("key_metrics") or f.get("metrics"),
                })

        raw_sources = report.get("all_sources") or []
        safe_sources = [str(s) for s in raw_sources] if isinstance(raw_sources, list) else []

        elapsed_total = round(time.time() - start_time, 2)

        response = {
            "company_name": report.get("company_name", company_name),
            "generated_at": report.get("generated_at", datetime.now(timezone.utc).isoformat()),
            "executive_summary": report.get("executive_summary", "No summary available."),
            "features": safe_features,
            "total_sources_analysed": report.get("total_sources_analysed", 0),
            "total_features_verified": report.get("total_features_verified", 0),
            "all_sources": safe_sources,
            "metadata": report.get("metadata"),
            "elapsed_seconds": elapsed_total,
        }

        logger.info(
            "CELERY TASK %s — Complete: %d features, %d sources, %.1fs",
            task_id, len(safe_features), response["total_sources_analysed"], elapsed_total,
        )

        return response

    except Exception as exc:
        elapsed_total = round(time.time() - start_time, 2)
        logger.error("CELERY TASK %s — Failed after %.1fs: %s", task_id, elapsed_total, exc, exc_info=True)

        try:
            from observability.metrics import PIPELINE_RUNS
            PIPELINE_RUNS.labels(status="error").inc()
        except Exception:
            pass

        # Retry on transient failures (network, rate limits)
        error_str = str(exc)
        is_transient = any(kw in error_str.lower() for kw in ["timeout", "429", "rate limit", "connection"])
        if is_transient and self.request.retries < self.max_retries:
            logger.info("CELERY TASK %s — Retrying (attempt %d)", task_id, self.request.retries + 1)
            raise self.retry(exc=exc)

        # Non-retryable — raise so Celery marks as FAILURE
        raise

    finally:
        try:
            from observability.metrics import ACTIVE_PIPELINES
            ACTIVE_PIPELINES.dec()
        except Exception:
            pass
