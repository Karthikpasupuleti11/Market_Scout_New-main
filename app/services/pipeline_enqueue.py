"""Enqueue intelligence pipeline tasks (Celery) with cache fast-path."""

import logging

from fastapi import HTTPException

from app.config import settings
from database.session import SessionLocal

logger = logging.getLogger(__name__)


def enqueue_pipeline_or_cache(
    company_name: str,
    date_window_days: int,
    force_refresh: bool,
) -> dict:
    """Redis → DB cache lookup, or enqueue full Celery pipeline."""
    from cache.report_cache import (
        build_task_response,
        invalidate_stored_report,
        lookup_cached_report,
        sanitise_company_name,
    )
    from tasks.pipeline_tasks import run_pipeline_task, serve_cached_report_task

    company = sanitise_company_name(company_name)
    if not company:
        raise HTTPException(status_code=400, detail="Empty company name provided.")

    cache_invalidated = None
    if force_refresh:
        db = SessionLocal()
        try:
            cache_invalidated = invalidate_stored_report(
                db, company, date_window_days
            )
        finally:
            db.close()
        logger.info(
            "API — Force refresh: cleared stored report for '%s' (%dd) %s",
            company, date_window_days, cache_invalidated,
        )

    if not force_refresh:
        db = SessionLocal()
        try:
            report, source = lookup_cached_report(db, company, date_window_days)
        finally:
            db.close()

        if report and source:
            payload = build_task_response(
                report,
                company,
                elapsed_seconds=0.0,
                from_cache=True,
                cache_source=source,
            )
            task = serve_cached_report_task.delay(payload, cache_source=source)
            logger.info(
                "API — Cache hit (%s) for '%s' (%dd), task_id=%s",
                source, company, date_window_days, task.id,
            )
            return {
                "task_id": task.id,
                "status": "PENDING",
                "company_name": company,
                "from_cache": True,
                "cache_source": source,
                "message": f"Cached report ({source}). Poll /task/{task.id} for results.",
            }

    from cache.redis_client import check_rate_limit

    if not check_rate_limit(
        "pipeline_global",
        limit=settings.LLM_GLOBAL_PIPELINE_LIMIT,
        window_seconds=120,
    ):
        raise HTTPException(
            status_code=429,
            detail=(
                f"Pipeline capacity reached (max {settings.LLM_GLOBAL_PIPELINE_LIMIT} "
                "concurrent runs). Please wait about two minutes and try again."
            ),
        )

    logger.info("API — Pipeline enqueued for: '%s'", company)
    task = run_pipeline_task.delay(
        company_name=company,
        date_window_days=date_window_days,
    )
    response = {
        "task_id": task.id,
        "status": "PENDING",
        "company_name": company,
        "from_cache": False,
        "message": "Pipeline enqueued. Poll /task/{task_id} for progress.",
    }
    if cache_invalidated is not None:
        response["cache_invalidated"] = cache_invalidated
        response["force_refresh"] = True
    return response
