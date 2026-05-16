"""
Market Intelligence Scout — Celery Tasks

  run_market_pipeline   — user-triggered intelligence pipeline (queue: pipeline)
  run_scheduled_report  — scheduled job: run pipeline + email PDF (queue: scheduled)
  recover_stale_jobs    — periodic: mark long-pending scheduled jobs as failed
  cleanup_expired_results — periodic: prune old Celery result keys

Conventions:
  - Graph is built ONCE per worker process (module-level) and reused.
  - asyncio.run inside the task is fine: prefork pool gives each task a fresh
    sync context; we never share an event loop across tasks.
  - Hard exceptions trigger autoretry with exponential backoff (max 3).
  - Metrics emitted here match the SSE-path metrics in app/main.py so the
    Prometheus dashboards stay consistent whether the user hits /run-agent or
    /run-agent/stream.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from celery.exceptions import SoftTimeLimitExceeded

from app.celery_app import celery
from database import crud
from database.session import SessionLocal
from graph.builder import build_graph
from observability.metrics import (
    ACTIVE_PIPELINES,
    CONFIDENCE_SCORE,
    FEATURES_EXTRACTED,
    FEATURES_VERIFIED,
    PIPELINE_RUNS,
    SOURCES_ANALYSED,
)
from utils.feature_utils import _safe_feature

logger = logging.getLogger(__name__)


# ── Graph singleton (per worker process) ───────────────────────────────
# Workers are recycled every N tasks (worker_max_tasks_per_child) so the
# graph is rebuilt periodically anyway — no manual refresh needed.
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        logger.info("CELERY — building LangGraph (first task in this worker)")
        _graph = build_graph()
    return _graph


# ── Helpers ────────────────────────────────────────────────────────────
def _build_response(report: Dict[str, Any], company_name: str) -> Dict[str, Any]:
    """Mirror the response shape used by /run-agent/stream so frontend code
    is identical regardless of dispatch path."""
    features = report.get("features", []) or []

    safe_features = []
    for i, f in enumerate(features):
        if isinstance(f, dict):
            try:
                safe_features.append(_safe_feature(f, i).model_dump())
            except Exception as exc:
                logger.debug("CELERY — feature %d coerce failed: %s", i, exc)

    raw_sources = report.get("all_sources") or []
    safe_sources = [str(s) for s in raw_sources] if isinstance(raw_sources, list) else []

    return {
        "company_name": report.get("company_name", company_name),
        "generated_at": report.get("generated_at",
                                   datetime.now(timezone.utc).isoformat()),
        "executive_summary": report.get("executive_summary", "No summary available."),
        "features": safe_features,
        "total_sources_analysed": report.get("total_sources_analysed", 0),
        "total_features_verified": report.get("total_features_verified", 0),
        "all_sources": safe_sources,
        "metadata": report.get("metadata"),
    }


def _record_metrics(report: Dict[str, Any], company_name: str, error: str | None):
    features = report.get("features", []) or []

    if error and not features:
        PIPELINE_RUNS.labels(status="error").inc()
    else:
        PIPELINE_RUNS.labels(status="completed").inc()

    for f in features:
        if not isinstance(f, dict):
            continue
        cat = f.get("category", "unknown")
        FEATURES_EXTRACTED.labels(company=company_name, category=cat).inc()
        score = f.get("confidence_score", 0) or 0
        try:
            CONFIDENCE_SCORE.observe(float(score))
        except (TypeError, ValueError):
            pass

    FEATURES_VERIFIED.labels(company=company_name).inc(
        report.get("total_features_verified", 0) or 0
    )
    SOURCES_ANALYSED.observe(report.get("total_sources_analysed", 0) or 0)


# ── Main task: user-triggered pipeline ─────────────────────────────────
@celery.task(
    bind=True,
    name="tasks.pipeline_tasks.run_market_pipeline",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
)
def run_market_pipeline(self, company_name: str, date_window_days: int) -> Dict[str, Any]:
    """Run the LangGraph intelligence pipeline and persist + return the report."""
    task_id = self.request.id
    logger.info("PIPELINE — START | task=%s | company=%s | window=%s",
                task_id, company_name, date_window_days)

    ACTIVE_PIPELINES.inc()
    self.update_state(state="PROGRESS",
                      meta={"stage": "pipeline_running", "company": company_name})

    try:
        graph = _get_graph()
        try:
            result = asyncio.run(graph.ainvoke({
                "company_name": company_name,
                "date_window_days": date_window_days,
            }))
        except SoftTimeLimitExceeded:
            logger.error("PIPELINE — soft time limit hit | task=%s | company=%s",
                         task_id, company_name)
            PIPELINE_RUNS.labels(status="error").inc()
            raise

        report = result.get("synthesis_report", {}) or {}
        if not report:
            PIPELINE_RUNS.labels(status="error").inc()
            raise RuntimeError("Pipeline produced no synthesis report.")

        error = result.get("error") or report.get("metadata", {}).get("error")
        _record_metrics(report, company_name, error)

        # Persist
        db = SessionLocal()
        try:
            crud.save_report(db, company_name, report)
        except Exception as exc:
            logger.warning("PIPELINE — DB persist failed (non-fatal) | task=%s | %s",
                           task_id, exc)
        finally:
            db.close()

        response = _build_response(report, company_name)
        logger.info("PIPELINE — DONE | task=%s | features=%d | sources=%d",
                    task_id, len(response["features"]),
                    response["total_sources_analysed"])
        return response

    finally:
        ACTIVE_PIPELINES.dec()


# ── Scheduled report task ──────────────────────────────────────────────
@celery.task(
    bind=True,
    name="tasks.pipeline_tasks.run_scheduled_report",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=2,
    acks_late=True,
)
def run_scheduled_report(self, job_id: int, company_name: str, email: str,
                         date_window_days: int = 7) -> Dict[str, Any]:
    """Run pipeline for a scheduled job, persist report, email the recipient,
    update the ScheduledJob row through its lifecycle."""
    from scheduler.email_service import send_report_email

    task_id = self.request.id
    logger.info("SCHEDULED — START | task=%s | job=%d | company=%s | email=%s",
                task_id, job_id, company_name, email)

    db = SessionLocal()
    ACTIVE_PIPELINES.inc()
    try:
        crud.update_job_status(db, job_id, status="running")

        graph = _get_graph()
        result = asyncio.run(graph.ainvoke({
            "company_name": company_name,
            "date_window_days": date_window_days,
        }))
        report = result.get("synthesis_report", {}) or {}
        if not report:
            raise RuntimeError("Pipeline produced no synthesis report.")

        error = result.get("error") or report.get("metadata", {}).get("error")
        _record_metrics(report, company_name, error)

        saved = crud.save_report(db, company_name, report)

        try:
            send_report_email(report, company_name, email)
        except Exception as exc:
            logger.error("SCHEDULED — email failed | job=%d | %s", job_id, exc,
                         exc_info=True)
            crud.update_job_status(db, job_id, status="failed",
                                   error_msg=f"email failed: {str(exc)[:400]}")
            raise

        crud.update_job_status(db, job_id, status="done", report_id=saved.id)
        logger.info("SCHEDULED — DONE | task=%s | job=%d | report=%d",
                    task_id, job_id, saved.id)
        return {"job_id": job_id, "report_id": saved.id, "status": "done"}

    except Exception as exc:
        err = str(exc)[:500]
        logger.error("SCHEDULED — FAILED | task=%s | job=%d | %s",
                     task_id, job_id, err, exc_info=True)
        try:
            crud.update_job_status(db, job_id, status="failed", error_msg=err)
        except Exception:
            pass
        raise
    finally:
        ACTIVE_PIPELINES.dec()
        db.close()


# ── Periodic: recover stale scheduled jobs ─────────────────────────────
@celery.task(name="tasks.pipeline_tasks.recover_stale_jobs")
def recover_stale_jobs() -> Dict[str, int]:
    """Mark any pending/running scheduled jobs whose scheduled_at is in the
    past by > 1 hour as failed. Beat fires this every 5 minutes."""
    from datetime import timedelta

    from database.scheduled_job_model import ScheduledJob

    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    db = SessionLocal()
    recovered = 0
    try:
        stale = (
            db.query(ScheduledJob)
            .filter(
                ScheduledJob.status.in_(["pending", "running"]),
                ScheduledJob.scheduled_at < cutoff,
            )
            .all()
        )
        for job in stale:
            job.status = "failed"
            job.error_msg = "Recovered by periodic sweep — never completed."
            recovered += 1
        if recovered:
            db.commit()
            logger.warning("MAINT — recovered %d stale scheduled job(s)", recovered)
        return {"recovered": recovered}
    finally:
        db.close()


# ── Periodic: cleanup expired result keys ──────────────────────────────
@celery.task(name="tasks.pipeline_tasks.cleanup_expired_results")
def cleanup_expired_results() -> Dict[str, int]:
    """Sanity sweep — Celery sets TTL on results via result_expires, but if a
    backend restart drops TTLs we re-prune keys older than 24h."""
    try:
        from cache.redis_client import get_redis
        r = get_redis()
        # Celery result keys: celery-task-meta-*
        deleted = 0
        for key in r.scan_iter(match="celery-task-meta-*", count=500):
            ttl = r.ttl(key)
            if ttl == -1:  # no TTL set — orphan
                r.delete(key)
                deleted += 1
        if deleted:
            logger.info("MAINT — pruned %d orphan result keys", deleted)
        return {"deleted": deleted}
    except Exception as exc:
        logger.warning("MAINT — cleanup_expired_results skipped: %s", exc)
        return {"deleted": 0}
