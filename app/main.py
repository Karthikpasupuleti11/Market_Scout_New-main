"""
Market Intelligence Scout — FastAPI application entrypoint.

Routes live in ``app.routers.*``; pipeline execution runs in Celery workers only.
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.config import settings
from app.routers import competitors, history, intelligence, schedules, system
from database.models import Base
from database.scheduled_job_model import ScheduledJob
from database.session import SessionLocal, engine
from graph.builder import build_graph
from observability.metrics import REQUEST_COUNT, REQUEST_LATENCY
from observability.prometheus_setup import create_metrics_asgi_app
from scheduler import scheduler

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.APP_NAME)
    Base.metadata.create_all(bind=engine)
    app.state.graph = build_graph()
    logger.info("LangGraph pipeline compiled and ready")

    from observability.resource_metrics import start_resource_metrics_collector

    start_resource_metrics_collector()

    if settings.ENABLE_SCHEDULER:
        scheduler.init_scheduler()
        try:
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
                    "SCHEDULER — Recovered stale job %d (%s) → failed",
                    job.id,
                    job.company_name,
                )
            if stale_jobs:
                recovery_db.commit()
                logger.info("SCHEDULER — Recovered %d stale job(s)", len(stale_jobs))
            recovery_db.close()
        except Exception as exc:
            logger.warning("SCHEDULER — Stale job recovery failed (non-fatal): %s", exc)
    else:
        logger.info("Scheduler disabled (ENABLE_SCHEDULER=False)")

    try:
        from observability.tracing import setup_tracing

        setup_tracing(app)
    except Exception as exc:
        logger.warning("Tracing setup skipped: %s", exc)

    # Pre-warm the RAG embedding model so first index is instant
    try:
        from app.rag.embedding import preload as preload_embeddings

        preload_embeddings()
        logger.info("RAG embedding model pre-loaded")
    except Exception as exc:
        logger.warning("RAG embedding preload skipped (non-fatal): %s", exc)

    yield

    logger.info("Shutting down %s", settings.APP_NAME)
    if settings.ENABLE_SCHEDULER:
        scheduler.shutdown_scheduler()


app = FastAPI(
    title="Market Intelligence Scout",
    description=(
        "Enterprise-grade market intelligence: extract, verify, and score "
        "technical features from public sources."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(system.router)
app.include_router(intelligence.router)
app.include_router(history.router)
app.include_router(competitors.router)
app.include_router(schedules.router)

try:
    from app.rag.routes import router as rag_router

    app.include_router(rag_router)
except Exception as exc:
    logger.warning("RAG routes not loaded (optional): %s", exc)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://market-scout.me",
        "https://www.market-scout.me",
        "https://market-scout-new-main.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/metrics", create_metrics_asgi_app())


@app.middleware("http")
async def track_request_metrics(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    endpoint = request.url.path
    if endpoint != "/metrics":
        REQUEST_COUNT.labels(
            endpoint=endpoint,
            method=request.method,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)
    return response
