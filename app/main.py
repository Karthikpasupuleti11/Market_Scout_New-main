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


load_dotenv()

# ── Internal Imports ───────────────────────────────────────────────
from database.session import engine, get_db, SessionLocal
from database.models import Base
from database import crud, schemas
from graph.builder import build_graph
from app.config import settings
from scheduler import scheduler
from observability.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
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

    # Start the APScheduler (only one process should own it)
    if settings.ENABLE_SCHEDULER:
        scheduler.init_scheduler()

        # ── Recover stale jobs after server restart ────────────────────
        # APScheduler is in-memory, so any "pending"/"running" jobs whose
        # scheduled_at has already passed are orphans — mark them failed.
        try:
            from database.scheduled_job_model import ScheduledJob
            recovery_db = SessionLocal()
            stale_jobs = (
                recovery_db.query(ScheduledJob)
                .filter(
                    ScheduledJob.status.in_(["pending", "running"]),
                    ScheduledJob.scheduled_at < datetime.now(timezone.utc),
                )
                .all()
            )
            for job in stale_jobs:
                job.status = "failed"
                job.error_msg = (
                    "Server restarted before this job could complete. "
                    "Please reschedule."
                )
                logger.warning(
                    "SCHEDULER — Recovered stale job %d (%s) → marked as failed",
                    job.id, job.company_name,
                )
            if stale_jobs:
                recovery_db.commit()
                logger.info("SCHEDULER — Recovered %d stale job(s)", len(stale_jobs))
            recovery_db.close()
        except Exception as exc:
            logger.warning("SCHEDULER — Stale job recovery failed (non-fatal): %s", exc)
    else:
        logger.info("Scheduler disabled in this process (ENABLE_SCHEDULER=False)")

    # Initialise tracing (optional — only if OpenTelemetry deps are present)
    try:
        from observability.tracing import setup_tracing
        setup_tracing(app)
    except Exception as exc:
        logger.warning("Tracing setup skipped: %s", exc)

    yield
    
    logger.info("Shutting down %s", settings.APP_NAME)
    if settings.ENABLE_SCHEDULER:
        scheduler.shutdown_scheduler()


# ────────────────────────────────────────────────────────────────────
# FastAPI Application
# ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Market Intelligence Scout 🚀",
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "https://market-scout.me",
    "https://www.market-scout.me",
    "https://market-scout-new-main.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/dashboard-stats", tags=["System"], summary="Dashboard overview stats")
def dashboard_stats(db: Session = Depends(get_db)):
    """Return aggregated stats for the overview dashboard.

    Includes: latest report info, total reports count, and total companies.
    """
    latest = crud.get_latest_report(db)
    total_companies = len(crud.get_competitors(db))
    return {
        "latest_report": latest,
        "total_companies": total_companies,
    }


@app.post(
    "/run-agent",
    tags=["Intelligence"],
    summary="Run Market Intelligence Pipeline (Async via Celery)",
)
async def run_agent(request: AgentRequest):
    """Dispatch the intelligence pipeline as a Celery task. Returns task_id for polling.

    Concurrency is bounded only by Celery worker pool capacity and broker queue
    depth — no per-window dispatch cap.
    """
    logger.info("API — Pipeline dispatched for: '%s'", request.company_name)
    task = run_market_pipeline.delay(request.company_name, request.date_window_days)
    return {"task_id": task.id, "status": "PENDING"}


@app.get("/task-status/{task_id}", tags=["Intelligence"], summary="Poll Celery Task")
def task_status(task_id: str):
    """Return Celery task status and result (when ready)."""
    from app.celery_app import celery
    try:
        res = AsyncResult(task_id, app=celery)
        payload = {"task_id": task_id, "status": res.status}
        if res.successful():
            payload["result"] = res.result
        elif res.failed():
            payload["error"] = str(res.result)
        elif res.status == "PROGRESS":
            payload["progress"] = res.info if isinstance(res.info, dict) else {}
        return payload
    except Exception as exc:
        logger.error("API — task-status error for %s: %s", task_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"task-status error: {exc}")


# ────────────────────────────────────────────────────────────────────
# SSE Streaming Pipeline Endpoint
# ────────────────────────────────────────────────────────────────────

from fastapi.responses import StreamingResponse
import json as json_lib
import uuid

# SSE stream <-> Celery task bridge. Keep in sync with tasks.pipeline_tasks.
_STREAM_KEY_FMT = "pipeline:events:{stream_id}"
_STREAM_TERMINAL_EVENTS = {"complete", "error"}
_STREAM_HEARTBEAT_SECONDS = 15
_STREAM_MAX_SECONDS = 3600  # hard cap so a wedged task can't hold the connection forever


@app.post(
    "/run-agent/stream",
    tags=["Intelligence"],
    summary="Run Pipeline with Real-Time SSE Progress (via Celery)",
)
async def run_agent_stream(request: AgentRequest):
    """Dispatch the pipeline as a Celery task and stream progress + final result
    over SSE. Heavy work runs on the Celery worker pool, not the API process,
    so concurrency scales with worker capacity instead of API event-loop slots.
    """
    from cache.redis_client import get_redis
    from app.celery_app import celery as _celery

    stream_id = uuid.uuid4().hex
    stream_key = _STREAM_KEY_FMT.format(stream_id=stream_id)

    task = run_market_pipeline.apply_async(
        args=[request.company_name, request.date_window_days],
        kwargs={"stream_id": stream_id},
        queue="pipeline",
        routing_key="pipeline.run",
    )
    logger.info("SSE — dispatched task=%s stream=%s company='%s'",
                task.id, stream_id, request.company_name)

    redis_conn = get_redis()

    async def event_generator():
        start = time.time()
        try:
            yield (
                f"data: {json_lib.dumps({'event': 'dispatched', 'task_id': task.id, 'stream_id': stream_id})}\n\n"
            )
            while True:
                if time.time() - start > _STREAM_MAX_SECONDS:
                    yield f"data: {json_lib.dumps({'event': 'error', 'detail': 'stream timeout'})}\n\n"
                    break

                popped = await asyncio.to_thread(
                    redis_conn.brpop, stream_key, _STREAM_HEARTBEAT_SECONDS
                )
                if popped is None:
                    # No event in this window — emit a heartbeat and check the
                    # task hasn't died silently (worker crash, lost message).
                    yield ": keepalive\n\n"
                    try:
                        result = AsyncResult(task.id, app=_celery)
                        if result.failed():
                            err = str(result.result)[:500] if result.result else "task failed"
                            yield f"data: {json_lib.dumps({'event': 'error', 'detail': err})}\n\n"
                            break
                    except Exception:
                        pass
                    continue

                _, raw = popped
                try:
                    msg = json_lib.loads(raw)
                except Exception as exc:
                    logger.debug("SSE — malformed stream event dropped: %s", exc)
                    continue

                yield f"data: {json_lib.dumps(msg)}\n\n"
                if msg.get("event") in _STREAM_TERMINAL_EVENTS:
                    break
        finally:
            try:
                redis_conn.delete(stream_key)
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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

    # The standalone scheduler process polls the DB and arms new pending jobs.
    # If ENABLE_SCHEDULER is True in *this* process (single-worker dev mode),
    # arm immediately so the trigger fires without waiting for the poll.
    if settings.ENABLE_SCHEDULER:
        try:
            scheduler.schedule_job(
                job_id=db_job.id,
                run_at=job.scheduled_at,
                company_name=job.company_name,
                email=job.email,
                date_window_days=getattr(job, "date_window_days", 7),
            )
        except RuntimeError as exc:
            logger.warning("SCHEDULES — in-process arm skipped: %s", exc)

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

    # Remove from APScheduler if running in-process; otherwise the standalone
    # scheduler will notice the row is gone on its next sweep.
    if settings.ENABLE_SCHEDULER:
        try:
            scheduler.cancel_job(job_id)
        except RuntimeError:
            pass
    return