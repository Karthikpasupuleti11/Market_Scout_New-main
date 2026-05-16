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
    response_model=AgentResponse,
    tags=["Intelligence"],
    summary="Run Market Intelligence Pipeline",
)
async def run_agent(request: AgentRequest):
    """Execute the full intelligence pipeline for a given company."""
    # Global concurrency cap — prevents thundering herd against LLM rate limit.
    from cache.redis_client import check_rate_limit
    if not check_rate_limit(
        "pipeline_global",
        limit=settings.LLM_GLOBAL_PIPELINE_LIMIT,
        window_seconds=120,
    ):
        raise HTTPException(
            status_code=429,
            detail=f"Pipeline capacity reached (max {settings.LLM_GLOBAL_PIPELINE_LIMIT} concurrent). Retry in ~2 min.",
        )

    logger.info("API — Pipeline invoked for: '%s'", request.company_name)
    ACTIVE_PIPELINES.inc()

    try:
        graph = app.state.graph
        # Run the pipeline in a thread pool to avoid blocking the event loop
        result = await asyncio.to_thread(
            graph.invoke,
            {
                "company_name": request.company_name,
                "date_window_days": request.date_window_days,
            },
        )

        report = result.get("synthesis_report", {})
        if not report:
            PIPELINE_RUNS.labels(status="error").inc()
            raise HTTPException(status_code=500, detail="Pipeline produced no report.")

        # ── Record metrics ─────────────────────────────────────────
        error = result.get("error") or report.get("metadata", {}).get("error")
        features = report.get("features", [])

        if error and not features:
            PIPELINE_RUNS.labels(status="error").inc()
        else:
            PIPELINE_RUNS.labels(status="completed").inc()

        # Feature-level metrics
        for f in features:
            cat = f.get("category", "unknown") if isinstance(f, dict) else "unknown"
            FEATURES_EXTRACTED.labels(company=request.company_name, category=cat).inc()
            score = f.get("confidence_score", 0) if isinstance(f, dict) else 0
            CONFIDENCE_SCORE.observe(score)

        FEATURES_VERIFIED.labels(company=request.company_name).inc(
            report.get("total_features_verified", 0)
        )
        SOURCES_ANALYSED.observe(report.get("total_sources_analysed", 0))

        # ── Build response ─────────────────────────────────────────
        safe_features = []
        for i, f in enumerate(features):
            if isinstance(f, dict):
                try:
                    safe_features.append(_safe_feature(f, i))
                except Exception as feat_exc:
                    logger.warning("API — Skipping invalid feature #%d: %s — data: %s", i, feat_exc, f)
            else:
                logger.warning("API — Skipping non-dict feature #%d: %s", i, type(f))

        # Ensure all_sources is a list of strings
        raw_sources = report.get("all_sources") or []
        safe_sources = [str(s) for s in raw_sources] if isinstance(raw_sources, list) else None

        response = AgentResponse(
            company_name=report.get("company_name", request.company_name),
            generated_at=report.get("generated_at", datetime.now(timezone.utc).isoformat()),
            executive_summary=report.get("executive_summary", "No summary available."),
            features=safe_features,
            total_sources_analysed=report.get("total_sources_analysed", 0),
            total_features_verified=report.get("total_features_verified", 0),
            all_sources=safe_sources,
            metadata=report.get("metadata"),
        )

        # ── Persist to PostgreSQL ──────────────────────────────────
        try:
            db = next(get_db())
            crud.save_report(db, request.company_name, report)
            logger.info("API — Report saved to PostgreSQL for '%s'", request.company_name)
        except Exception as db_exc:
            logger.warning("API — DB persistence failed (non-fatal): %s", db_exc)

        logger.info(
            "API — Report: %d features, %d sources",
            len(response.features), response.total_sources_analysed,
        )
        return response

    except HTTPException:
        raise
    except ValueError as exc:
        PIPELINE_RUNS.labels(status="guardrail_blocked").inc()
        logger.error("API — ValueError during response build: %s", exc, exc_info=True)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        PIPELINE_RUNS.labels(status="error").inc()
        logger.error("API — Unexpected error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(exc)}")
    finally:
        ACTIVE_PIPELINES.dec()


# ────────────────────────────────────────────────────────────────────
# SSE Streaming Pipeline Endpoint
# ────────────────────────────────────────────────────────────────────

from fastapi.responses import StreamingResponse
from queue import Queue
import json as json_lib
import threading

@app.post(
    "/run-agent/stream",
    tags=["Intelligence"],
    summary="Run Pipeline with Real-Time SSE Progress",
)
async def run_agent_stream(request: AgentRequest):
    """Execute the intelligence pipeline and stream progress events via SSE."""
    from cache.redis_client import check_rate_limit

    if not check_rate_limit(
        "pipeline_global",
        limit=settings.LLM_GLOBAL_PIPELINE_LIMIT,
        window_seconds=120,
    ):
        raise HTTPException(
            status_code=429,
            detail=f"Pipeline capacity reached (max {settings.LLM_GLOBAL_PIPELINE_LIMIT} concurrent). Retry in ~2 min.",
        )

    progress_queue: Queue = Queue()

    def progress_callback(node_name: str, status: str, elapsed: float = 0):
        """Called by each graph node via the _progress_callback state key."""
        progress_queue.put({
            "event": "node_progress",
            "node": node_name,
            "status": status,
            "elapsed": round(elapsed, 2),
        })

    def run_pipeline_thread():
        """Run the graph in a background thread, pushing events to the queue."""
        ACTIVE_PIPELINES.inc()
        try:
            graph = app.state.graph
            result = asyncio.run(graph.ainvoke({
                "company_name": request.company_name,
                "date_window_days": request.date_window_days,
                "_progress_callback": progress_callback,
            }))

            report = result.get("synthesis_report", {})
            if not report:
                progress_queue.put({
                    "event": "error",
                    "detail": "Pipeline produced no report.",
                })
                return

            # Record metrics
            error_msg = result.get("error") or report.get("metadata", {}).get("error")
            features = report.get("features", [])
            if error_msg and not features:
                PIPELINE_RUNS.labels(status="error").inc()
            else:
                PIPELINE_RUNS.labels(status="completed").inc()

            for f in features:
                cat = f.get("category", "unknown") if isinstance(f, dict) else "unknown"
                FEATURES_EXTRACTED.labels(company=request.company_name, category=cat).inc()
                score = f.get("confidence_score", 0) if isinstance(f, dict) else 0
                CONFIDENCE_SCORE.observe(score)

            FEATURES_VERIFIED.labels(company=request.company_name).inc(
                report.get("total_features_verified", 0)
            )
            SOURCES_ANALYSED.observe(report.get("total_sources_analysed", 0))

            # Build safe response
            safe_features = []
            for i, f in enumerate(features):
                if isinstance(f, dict):
                    try:
                        safe_features.append(_safe_feature(f, i).model_dump())
                    except Exception:
                        pass

            raw_sources = report.get("all_sources") or []
            safe_sources = [str(s) for s in raw_sources] if isinstance(raw_sources, list) else []

            # Persist to DB
            try:
                db = SessionLocal()
                crud.save_report(db, request.company_name, report)
                db.close()
            except Exception as db_exc:
                logger.warning("SSE — DB persistence failed (non-fatal): %s", db_exc)

            # Push final result event
            progress_queue.put({
                "event": "complete",
                "data": {
                    "company_name": report.get("company_name", request.company_name),
                    "generated_at": report.get("generated_at", datetime.now(timezone.utc).isoformat()),
                    "executive_summary": report.get("executive_summary", "No summary available."),
                    "features": safe_features,
                    "total_sources_analysed": report.get("total_sources_analysed", 0),
                    "total_features_verified": report.get("total_features_verified", 0),
                    "all_sources": safe_sources,
                    "metadata": report.get("metadata"),
                },
            })

        except Exception as exc:
            PIPELINE_RUNS.labels(status="error").inc()
            logger.error("SSE — Pipeline error: %s", exc, exc_info=True)
            progress_queue.put({
                "event": "error",
                "detail": str(exc)[:500],
            })
        finally:
            ACTIVE_PIPELINES.dec()
            progress_queue.put(None)  # Sentinel to close stream

    # Start pipeline in a background thread
    thread = threading.Thread(target=run_pipeline_thread, daemon=True)
    thread.start()

    async def event_generator():
        """Async generator that yields SSE events from the queue."""
        while True:
            msg = await asyncio.to_thread(progress_queue.get, timeout=300)
            if msg is None:
                break
            yield f"data: {json_lib.dumps(msg)}\n\n"

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
def create_schedule(job: schemas.ScheduledJobCreate, request: Request, db: Session = Depends(get_db)):
    """Create a new scheduled report job."""
    # Ensure scheduled format is UTC
    if job.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future.")
        
    db_job = crud.create_scheduled_job(db, job.company_name, job.email, job.scheduled_at)
    
    # Add to APScheduler
    scheduler.schedule_job(
        job_id=db_job.id,
        run_at=job.scheduled_at,
        company_name=job.company_name,
        email=job.email,
        db_factory=SessionLocal, # we need a factory for the background thread
        graph=request.app.state.graph
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