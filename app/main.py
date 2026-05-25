"""
Market Intelligence Scout — FastAPI Application

Production-ready API with:
  • Structured request/response schemas
  • Prometheus metrics endpoint (/metrics)
  • OpenTelemetry tracing
  • Health check endpoint
  • CORS support
  • Startup/shutdown lifecycle hooks
"""

import time
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from prometheus_client import make_asgi_app
from celery.result import AsyncResult
from tasks.pipeline_tasks import run_market_pipeline
from app.services.pipeline_enqueue import enqueue_pipeline_or_cache

import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

load_dotenv()


def _sentry_before_send(event, hint):
    """Filter out expected business-logic outcomes — keep only real errors."""
    exc_info = hint.get("exc_info")
    if exc_info:
        exc_type, exc_value, _ = exc_info
        msg = str(exc_value).lower()

        # HTTPException 4xx are normal client errors, not bugs
        if exc_type.__name__ == "HTTPException":
            status = getattr(exc_value, "status_code", 500)
            if 400 <= status < 500:
                return None

        # ValueError from guardrails = user sent bad input, not a bug
        if exc_type is ValueError and any(kw in msg for kw in [
            "blocked keyword", "rate limit", "invalid company",
            "exceeds maximum length", "flagged as potentially malicious",
        ]):
            return None

        # Expected pipeline outcomes — no data found
        if any(kw in msg for kw in [
            "no features extracted",
            "no report",
            "no synthesis report",
            "empty report text",
        ]):
            return None

    return event


sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN_BACKEND", ""),
    environment="development",
    before_send=_sentry_before_send,
    integrations=[
        FastApiIntegration(),
    ],
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)


# ── Internal Imports ───────────────────────────────────────────────
from database.session import engine, get_db
from database.models import Base
from database import crud, schemas
from graph.builder import build_graph
from app.config import settings
from scheduler import scheduler
from observability.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    PIPELINE_RUNS,
    ACTIVE_PIPELINES,
    FEATURES_EXTRACTED,
    FEATURES_VERIFIED,
    CONFIDENCE_SCORE,
    SOURCES_ANALYSED,
)

from app.api_models import (
    AgentRequest,
    AgentResponse,
    FeatureItem,
    HealthResponse
)

# ────────────────────────────────────────────────────────────────────
# Logging Configuration
# ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)



# ────────────────────────────────────────────────────────────────────
# App Lifecycle
# ────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    logger.info("Starting %s", settings.APP_NAME)
    Base.metadata.create_all(bind=engine)
    app.state.graph = build_graph()
    logger.info("LangGraph pipeline compiled and ready")

    # Start the APScheduler
    scheduler.init_scheduler()

    # Initialise tracing (optional — only if OpenTelemetry deps are present)
    try:
        from observability.tracing import setup_tracing
        setup_tracing(app)
    except Exception as exc:
        logger.warning("Tracing setup skipped: %s", exc)

    yield
    
    logger.info("Shutting down %s", settings.APP_NAME)
    scheduler.shutdown_scheduler()


# ────────────────────────────────────────────────────────────────────
# FastAPI Application
# ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Market Intelligence Scout",
    description=(
        "Enterprise-grade Market Intelligence System that extracts, verifies, "
        "and scores technical features from public sources."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ✅ MOVE INSIDE FUNCTION STYLE (IMPORTANT)
def register_routes(app):
    from app.rag.routes import router as rag_router
    app.include_router(rag_router)

register_routes(app)

# ── Mount Prometheus /metrics endpoint ─────────────────────────────
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ────────────────────────────────────────────────────────────────────
# Middleware — Request Metrics
# ────────────────────────────────────────────────────────────────────

@app.middleware("http")
async def track_request_metrics(request: Request, call_next):
    """Record request count and latency for every endpoint."""
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    endpoint = request.url.path
    if endpoint != "/metrics":  # Don't track metrics scraping itself
        REQUEST_COUNT.labels(
            endpoint=endpoint,
            method=request.method,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)

    return response


def _cors_allow_origins() -> List[str]:
    """Explicit origins; regex below also allows market-scout.me subdomains."""
    defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://market-scout.me",
        "http://www.market-scout.me",
        "https://market-scout.me",
        "https://www.market-scout.me",
        "https://market-scout-new-main.vercel.app",
    ]
    extra = [
        o.strip()
        for o in (settings.CORS_ORIGINS or "").split(",")
        if o.strip()
    ]
    return list(dict.fromkeys(defaults + extra))


# CORS must be registered last so it wraps all responses (including errors).
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_origin_regex=r"https?://([\w-]+\.)?market-scout\.me(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ────────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["System"])
def root():
    return {
        "service": settings.APP_NAME,
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "metrics": "/metrics",
    }


@app.post("/system/clear-cache", tags=["System"], summary="Clear Redis Cache")
def clear_cache():
    """Flush all keys in the current Redis database."""
    try:
        from cache.redis_client import get_redis
        get_redis().flushdb()
        return {"status": "success", "message": "Redis cache cleared."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(exc)}")


@app.post("/system/clear-storage", tags=["System"], summary="Clear Database Storage")
def clear_storage(db: Session = Depends(get_db)):
    """Delete all competitors, reports, features, and scheduled jobs from the PostgreSQL database."""
    try:
        from database.models import Competitor, Report, Feature
        from database.scheduled_job_model import ScheduledJob
        
        # Explicitly delete all to avoid FK issues
        db.query(Feature).delete()
        db.query(Report).delete()
        db.query(Competitor).delete()
        db.query(ScheduledJob).delete()
        
        db.commit()
        return {"status": "success", "message": "Database storage cleared."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear storage: {str(exc)}")


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/run-agent")
async def run_agent(request: AgentRequest):

    result = enqueue_pipeline_or_cache(
        company_name=request.company_name,
        date_window_days=request.date_window_days,
        session_id=request.session_id,
        force_refresh=request.force_refresh,
    )

    return result

@app.get("/task-status/{task_id}")
async def task_status(task_id: str):

    task = AsyncResult(task_id)

    if task.ready():
        return {
            "status": task.status,
            "result": task.result
        }

    # Forward PROGRESS metadata (current_node) for live stage tracking
    response = {"status": task.status}
    if task.status == "PROGRESS" and task.info:
        response["meta"] = {
            "current_node": task.info.get("current_node"),
            "progress": task.info.get("progress"),
        }
    return response

# ────────────────────────────────────────────────────────────────────
# History & CRUD Endpoints
# ────────────────────────────────────────────────────────────────────

@app.get(
    "/reports/{company_name}",
    response_model=list[schemas.ReportResponse],
    tags=["History"],
    summary="Get historical reports for a company",
)
def get_reports(company_name: str, limit: int = 10, db: Session = Depends(get_db)):
    """Retrieve past pipeline reports for a company."""
    return crud.get_reports_for_competitor(db, company_name, limit=limit)


@app.get(
    "/features/{company_name}",
    response_model=list[schemas.FeatureResponse],
    tags=["History"],
    summary="Get all features ever extracted for a company",
)
def get_features(company_name: str, limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve all features extracted across all reports for a company."""
    return crud.get_all_features_for_competitor(db, company_name, limit=limit)


@app.delete(
    "/reports/{report_id}",
    status_code=204,
    tags=["History"],
    summary="Delete a report and all its features",
)
def delete_report(report_id: int, db: Session = Depends(get_db)):
    """Permanently delete a report and all associated features."""
    deleted = crud.delete_report(db, report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")


@app.post("/competitors", response_model=schemas.CompetitorResponse, tags=["Database"])
def create_competitor(competitor: schemas.CompetitorCreate, db: Session = Depends(get_db)):
    return crud.create_competitor(db, name=competitor.name, industry=competitor.industry)


@app.get("/competitors", response_model=list[schemas.CompetitorResponse], tags=["Database"])
def read_competitors(db: Session = Depends(get_db)):
    return crud.get_competitors(db)


@app.delete(
    "/competitors/{competitor_id}",
    status_code=204,
    tags=["Database"],
    summary="Delete a competitor and all its reports/features",
)
def delete_competitor(competitor_id: int, db: Session = Depends(get_db)):
    """Permanently delete a competitor and all associated data (reports, features)."""
    deleted = crud.delete_competitor(db, competitor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Competitor {competitor_id} not found.")
    # 204 No Content — no body returned


# ────────────────────────────────────────────────────────────────────
# Scheduled Jobs Endpoints
# ────────────────────────────────────────────────────────────────────

@app.post("/schedules", response_model=schemas.ScheduledJobResponse, tags=["Schedules"])
def create_schedule(job: schemas.ScheduledJobCreate, db: Session = Depends(get_db)):
    """Create a new scheduled report job."""
    # Ensure scheduled format is UTC
    if job.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future.")
        
    db_job = crud.create_scheduled_job(db, job.company_name, job.email, job.scheduled_at)
    
    # Add to APScheduler — enqueues into Celery when fired
    scheduler.schedule_job(
        job_id=db_job.id,
        run_at=job.scheduled_at,
        company_name=job.company_name,
        email=job.email,
    )
    
    return db_job


@app.get("/schedules", response_model=list[schemas.ScheduledJobResponse], tags=["Schedules"])
def get_schedules(db: Session = Depends(get_db)):
    """List all scheduled jobs (newest first)."""
    return crud.get_scheduled_jobs(db)


@app.delete("/schedules/{job_id}", status_code=204, tags=["Schedules"])
def delete_schedule(job_id: int, db: Session = Depends(get_db)):
    """Cancel a scheduled job if pending, and delete it."""
    deleted = crud.delete_scheduled_job(db, job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    
    # Remove from APScheduler
    scheduler.cancel_job(job_id)
    return