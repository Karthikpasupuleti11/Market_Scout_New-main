"""System, health, and dashboard routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.schemas.api import HealthResponse, ReadinessResponse, utc_now_iso
from database import crud
from database.models import Competitor, Feature, Report
from database.scheduled_job_model import ScheduledJob
from database.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["System"])

APP_VERSION = "2.0.0"


@router.get("/")
def root():
    return {
        "service": settings.APP_NAME,
        "version": APP_VERSION,
        "status": "operational",
        "docs": "/docs",
        "metrics": "/metrics",
        "pipeline": "celery",
    }


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Liveness — process is up."""
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        timestamp=utc_now_iso(),
    )


@router.get("/health/ready", response_model=ReadinessResponse)
def readiness_check(db: Session = Depends(get_db)):
    """Readiness — dependencies required for demos (DB + Redis)."""
    checks: dict[str, str] = {}

    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        logger.warning("Readiness — Postgres failed: %s", exc)
        checks["postgres"] = "error"

    try:
        from cache.redis_client import get_redis

        get_redis().ping()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.warning("Readiness — Redis failed: %s", exc)
        checks["redis"] = "error"

    all_ok = all(v == "ok" for v in checks.values())
    return ReadinessResponse(
        status="ready" if all_ok else "degraded",
        version=APP_VERSION,
        timestamp=utc_now_iso(),
        checks=checks,
    )


@router.get("/dashboard-stats", summary="Dashboard overview stats")
def dashboard_stats(db: Session = Depends(get_db)):
    latest = crud.get_latest_report(db)
    total_companies = len(crud.get_competitors(db))
    return {
        "latest_report": latest,
        "total_companies": total_companies,
    }


@router.post("/system/clear-cache", summary="Clear Redis Cache")
def clear_cache():
    """Flush application cache keys (demo reset). Uses Redis db0."""
    try:
        from cache.redis_client import get_redis

        get_redis().flushdb()
        return {"status": "success", "message": "Redis cache cleared."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(exc)}") from exc


@router.post("/system/clear-storage", summary="Clear Database Storage")
def clear_storage(db: Session = Depends(get_db)):
    """Delete all competitors, reports, features, and scheduled jobs (demo reset)."""
    try:
        db.query(ScheduledJob).delete()
        db.query(Feature).delete()
        db.query(Report).delete()
        db.query(Competitor).delete()
        db.commit()
        return {"status": "success", "message": "Database storage cleared."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to clear storage: {str(exc)}"
        ) from exc
