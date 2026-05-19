"""
Production report cache — Redis (L1) + PostgreSQL (L2).

Lookup key: normalised company name + date_window_days.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from cache.redis_client import delete_cache, get_cache, make_cache_key, set_cache

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def sanitise_company_name(raw: str) -> str:
    """Match guardrails input normalisation for consistent cache keys."""
    cleaned = _HTML_TAG_RE.sub("", raw or "")
    cleaned = html.unescape(cleaned)
    return " ".join(cleaned.split()).strip()


def normalize_company_name(name: str) -> str:
    return sanitise_company_name(name).lower()


def _cache_lookup_key(company_name: str, date_window_days: int) -> str:
    return f"{normalize_company_name(company_name)}:{int(date_window_days)}d"


def redis_report_key(company_name: str, date_window_days: int) -> str:
    return make_cache_key("report", _cache_lookup_key(company_name, date_window_days))


def get_report_from_redis(company_name: str, date_window_days: int) -> Optional[Dict[str, Any]]:
    key = redis_report_key(company_name, date_window_days)
    report = get_cache(key)
    if report and isinstance(report, dict):
        logger.info(
            "REPORT CACHE — Redis hit for '%s' (%dd)",
            company_name, date_window_days,
        )
        return report
    return None


def set_report_in_redis(
    company_name: str,
    date_window_days: int,
    report: Dict[str, Any],
    expire: Optional[int] = None,
) -> bool:
    key = redis_report_key(company_name, date_window_days)
    ttl = expire if expire is not None else settings.REPORT_CACHE_TTL
    return set_cache(key, report, expire=ttl)


def delete_report_from_redis(company_name: str, date_window_days: int) -> bool:
    """Remove the cached report key for this company + window."""
    return delete_cache(redis_report_key(company_name, date_window_days))


def invalidate_stored_report(
    db: Session,
    company_name: str,
    date_window_days: int,
) -> Dict[str, Any]:
    """Delete the TTL-window report from Redis and matching rows in PostgreSQL."""
    from database import crud

    redis_deleted = delete_report_from_redis(company_name, date_window_days)
    db_deleted = crud.delete_cached_reports_for_company(
        db,
        company_name=company_name,
        date_window_days=date_window_days,
        max_age_seconds=settings.REPORT_CACHE_MAX_AGE,
    )
    logger.info(
        "REPORT CACHE — Invalidated '%s' (%dd): redis=%s db_reports=%d",
        company_name,
        date_window_days,
        redis_deleted,
        db_deleted,
    )
    return {
        "redis_deleted": redis_deleted,
        "db_reports_deleted": db_deleted,
    }


def lookup_cached_report(
    db: Session,
    company_name: str,
    date_window_days: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Return (synthesis_report_dict, source) where source is 'redis' or 'database'."""
    cached = get_report_from_redis(company_name, date_window_days)
    if cached:
        return cached, "redis"

    from database import crud

    report = crud.get_latest_report_matching_window(
        db,
        company_name=company_name,
        date_window_days=date_window_days,
        max_age_seconds=settings.REPORT_CACHE_MAX_AGE,
    )
    if not report:
        return None, None

    synthesis = crud.report_to_synthesis_dict(report, company_name)
    set_report_in_redis(company_name, date_window_days, synthesis)
    logger.info(
        "REPORT CACHE — DB hit for '%s' (%dd), warmed Redis",
        company_name, date_window_days,
    )
    return synthesis, "database"


def build_task_response(
    report: Dict[str, Any],
    company_name: str,
    *,
    elapsed_seconds: float = 0.0,
    from_cache: bool = False,
    cache_source: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the JSON shape returned by Celery /task polling."""
    features = report.get("features", []) or []
    safe_features = []
    for i, f in enumerate(features):
        if isinstance(f, dict):
            safe_features.append({
                "rank": f.get("rank", i + 1),
                "title": f.get("title") or f.get("feature_title") or f.get("feature_summary", ""),
                "description": (
                    f.get("description")
                    or f.get("feature_summary")
                    or f.get("feature_text", "")
                ),
                "category": f.get("category"),
                "confidence_score": f.get("confidence_score") or f.get("confidence"),
                "impact_assessment": f.get("impact_assessment"),
                "source_url": f.get("source_url") or f.get("primary_url") or f.get("url"),
                "source_count": f.get("source_count"),
                "key_metrics": f.get("key_metrics") or f.get("metrics"),
            })

    raw_sources = report.get("all_sources") or []
    safe_sources = [str(s) for s in raw_sources] if isinstance(raw_sources, list) else []

    metadata = dict(report.get("metadata") or {})
    if from_cache:
        metadata["from_cache"] = True
        if cache_source:
            metadata["cache_source"] = cache_source

    response: Dict[str, Any] = {
        "company_name": report.get("company_name", company_name),
        "generated_at": report.get(
            "generated_at", datetime.now(timezone.utc).isoformat()
        ),
        "executive_summary": report.get("executive_summary", "No summary available."),
        "features": safe_features,
        "total_sources_analysed": report.get("total_sources_analysed", 0),
        "total_features_verified": report.get("total_features_verified", 0),
        "all_sources": safe_sources,
        "metadata": metadata,
        "elapsed_seconds": round(elapsed_seconds, 2),
    }
    if from_cache:
        response["from_cache"] = True
        if cache_source:
            response["cache_source"] = cache_source
    return response
