"""
Market Intelligence Scout — Report Cache Layer

L1 (Redis) + L2 (PostgreSQL) caching for pipeline reports.
Prevents redundant scraping/LLM processing for the same company
within a 6-hour window.
"""

import re
import json
import logging
from typing import Optional, Any

from cache.redis_client import get_redis, set_cache, get_cache, delete_cache
from app.config import settings

logger = logging.getLogger(__name__)

REPORT_CACHE_PREFIX = "report"


def normalize_company_name(name: str) -> str:
    """Normalise a company name to a deterministic cache-safe key.
    
    e.g. '  Google DeepMind  ' → 'google_deepmind'
    """
    cleaned = name.strip().lower()
    cleaned = re.sub(r'\s+', '_', cleaned)
    cleaned = re.sub(r'[^a-z0-9_]', '', cleaned)
    return cleaned


def make_report_cache_key(company: str, window_days: int) -> str:
    """Generate a Redis key for a report cache entry.
    
    Pattern: report:{normalised_name}:{window}d
    """
    normalised = normalize_company_name(company)
    return f"{REPORT_CACHE_PREFIX}:{normalised}:{window_days}d"


def get_report_from_redis(company: str, window_days: int) -> Optional[dict]:
    """L1 lookup — check Redis for a cached report."""
    key = make_report_cache_key(company, window_days)
    data = get_cache(key)
    if data:
        logger.info("REPORT CACHE HIT (L1/Redis) company=%s window=%dd", company, window_days)
    return data


def set_report_in_redis(
    company: str,
    window_days: int,
    report_data: dict,
    ttl: int = None,
) -> bool:
    """Write report to L1 (Redis) cache."""
    if ttl is None:
        ttl = settings.REPORT_CACHE_TTL
    key = make_report_cache_key(company, window_days)
    return set_cache(key, report_data, expire=ttl)


def invalidate_stored_report(company: str, window_days: int, db=None) -> bool:
    """Purge report from both L1 (Redis) and L2 (PostgreSQL).
    
    Called when force_refresh=True is requested.
    """
    key = make_report_cache_key(company, window_days)

    # ── L1: Redis delete ───────────────────────────────
    redis_ok = delete_cache(key)
    logger.info("L1 invalidation %s for %s", "OK" if redis_ok else "FAILED", key)

    # ── L2: PostgreSQL delete ──────────────────────────
    if db is not None:
        try:
            from database.models import Report, Competitor
            from datetime import datetime, timezone, timedelta

            cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.REPORT_CACHE_TTL)
            normalised = normalize_company_name(company)

            # Find the competitor
            competitor = db.query(Competitor).filter(
                Competitor.name.ilike(f"%{company.strip()}%")
            ).first()

            if competitor:
                deleted = db.query(Report).filter(
                    Report.competitor_id == competitor.id,
                    Report.created_at >= cutoff,
                ).delete(synchronize_session="fetch")
                db.commit()
                logger.info("L2 invalidation: deleted %d report(s) for %s", deleted, company)
        except Exception as exc:
            db.rollback()
            logger.warning("L2 invalidation failed for %s: %s", company, exc)

    return redis_ok
