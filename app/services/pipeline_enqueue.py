"""
Market Intelligence Scout — Pipeline Enqueue Service

Orchestrates the L1 → L2 → Celery flow:
  1. If force_refresh: invalidate caches, enqueue fresh run
  2. Check L1 (Redis) for cached report
  3. Check L2 (PostgreSQL) for recent report within max_age
  4. If both miss: enqueue a new Celery pipeline task
"""

import logging
from typing import Optional

from app.config import settings
from cache.report_cache import (
    get_report_from_redis,
    set_report_in_redis,
    invalidate_stored_report,
)
from database import crud
from database.session import get_db
from tasks.pipeline_tasks import run_market_pipeline
from tasks.serve_cached import serve_cached_report_task

logger = logging.getLogger(__name__)


def _report_orm_to_dict(report) -> dict:
    """Convert a Report ORM instance to the dict format the frontend expects."""
    features = []
    for f in report.features:
        features.append({
            "rank": None,
            "title": f.feature_title,
            "description": f.description,
            "category": f.category,
            "confidence_score": f.confidence_score,
            "impact_assessment": f.impact_assessment,
            "source_url": f.source_url,
            "source_count": f.source_count,
            "key_metrics": f.metrics,
        })

    return {
        "company_name": report.competitor.name if report.competitor else "",
        "generated_at": report.created_at.isoformat() if report.created_at else None,
        "executive_summary": report.executive_summary,
        "features": features,
        "total_sources_analysed": report.total_sources,
        "total_features_verified": report.total_features,
        "all_sources": report.all_sources or [],
        "metadata": report.metadata_,
    }


def enqueue_pipeline_or_cache(
    company_name: str,
    date_window_days: int,
    session_id: str,
    force_refresh: bool = False,
) -> dict:
    """Central entry point for pipeline execution.

    Returns a dict with:
      - task_id: Celery task ID for frontend polling
      - status: 'processing' | 'cached'
      - cache_invalidated: True if force_refresh triggered invalidation
    """

    # ── 1. Force refresh: purge caches first ──────────────
    if force_refresh:
        logger.info("Force refresh requested for %s — invalidating caches", company_name)
        try:
            db = next(get_db())
            invalidate_stored_report(company_name, date_window_days, db=db)
        except Exception as exc:
            logger.warning("Cache invalidation error: %s — proceeding with fresh run", exc)

        task = run_market_pipeline.delay(
            company_name, date_window_days, session_id
        )
        return {
            "task_id": task.id,
            "status": "processing",
            "cache_invalidated": True,
        }

    # ── 2. L1: Check Redis ────────────────────────────────
    cached = get_report_from_redis(company_name, date_window_days)
    if cached:
        logger.info("L1 HIT for %s — serving cached report via Celery", company_name)
        task = serve_cached_report_task.delay(cached)
        return {
            "task_id": task.id,
            "status": "cached",
        }

    # ── 3. L2: Check PostgreSQL ───────────────────────────
    try:
        db = next(get_db())
        db_report = crud.get_latest_report_matching_window(
            db, company_name, max_age_seconds=settings.REPORT_CACHE_TTL
        )
        if db_report:
            logger.info("L2 HIT for %s — re-warming Redis and serving", company_name)
            report_dict = _report_orm_to_dict(db_report)
            # Re-warm L1
            set_report_in_redis(company_name, date_window_days, report_dict)
            task = serve_cached_report_task.delay(report_dict)
            return {
                "task_id": task.id,
                "status": "cached",
            }
    except Exception as exc:
        logger.warning("L2 lookup failed: %s — falling through to fresh run", exc)

    # ── 4. Cache miss: enqueue fresh Celery task ──────────
    logger.info("Cache MISS for %s — enqueuing fresh pipeline run", company_name)
    task = run_market_pipeline.delay(
        company_name, date_window_days, session_id
    )
    return {
        "task_id": task.id,
        "status": "processing",
    }
