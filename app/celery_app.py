"""
Market Intelligence Scout — Celery Application

Production-grade Celery configuration:
  - Env-driven broker / result backend (Redis)
  - Dedicated queues for pipeline + scheduled work
  - acks_late + prefetch=1 (long-running tasks must not be lost on worker crash)
  - Worker recycling to bound memory growth (LangGraph + transformers leak)
  - Soft + hard time limits per task
  - Result expiration to stop Redis from ballooning
  - Beat schedule for periodic cleanup
  - Structured logging via signals
"""

from __future__ import annotations

import logging
import os

from celery import Celery
from celery.signals import (
    after_setup_logger,
    task_failure,
    task_postrun,
    task_prerun,
    task_retry,
    worker_init,
    worker_process_init,
    worker_ready,
)
from kombu import Queue

logger = logging.getLogger(__name__)


# ── Broker / Backend URLs ──────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
DEFAULT_BROKER = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
DEFAULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

BROKER_URL = os.getenv("CELERY_BROKER_URL", DEFAULT_BROKER)
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", DEFAULT_BACKEND)


# ── Celery app ─────────────────────────────────────────────────────────
celery = Celery(
    "market_scout",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["tasks.pipeline_tasks"],
)


# ── Queues ─────────────────────────────────────────────────────────────
# pipeline:   user-triggered intelligence runs (heavy, slow)
# scheduled:  cron / one-shot scheduled reports (heavy, slow)
# maintenance: periodic cleanup / housekeeping (light, fast)
celery.conf.task_queues = (
    Queue("pipeline", routing_key="pipeline.#"),
    Queue("scheduled", routing_key="scheduled.#"),
    Queue("maintenance", routing_key="maintenance.#"),
)
celery.conf.task_default_queue = "pipeline"
celery.conf.task_default_routing_key = "pipeline.default"

celery.conf.task_routes = {
    "tasks.pipeline_tasks.run_market_pipeline": {
        "queue": "pipeline",
        "routing_key": "pipeline.run",
    },
    "tasks.pipeline_tasks.run_scheduled_report": {
        "queue": "scheduled",
        "routing_key": "scheduled.run",
    },
    "tasks.pipeline_tasks.recover_stale_jobs": {
        "queue": "maintenance",
        "routing_key": "maintenance.recover",
    },
    "tasks.pipeline_tasks.cleanup_expired_results": {
        "queue": "maintenance",
        "routing_key": "maintenance.cleanup",
    },
}


# ── Core config ────────────────────────────────────────────────────────
celery.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Time
    timezone="UTC",
    enable_utc=True,
    # Reliability — task survives worker crash, re-queued
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Concurrency — one heavy task per worker slot, no prefetch hoarding
    worker_prefetch_multiplier=1,
    # Memory hygiene — recycle worker after N tasks (transformers/torch leak)
    worker_max_tasks_per_child=int(os.getenv("CELERY_WORKER_MAX_TASKS", "20")),
    worker_max_memory_per_child=int(os.getenv("CELERY_WORKER_MAX_MEMORY_KB", "1500000")),
    # Time limits — hard kill at 30 min, soft warn at 25 min
    task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT", "1800")),
    task_soft_time_limit=int(os.getenv("CELERY_TASK_SOFT_LIMIT", "1500")),
    # Tracking — emit started state so /task-status can show PROGRESS vs PENDING
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
    # Results — expire after 24h to stop Redis growth
    result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", "86400")),
    result_extended=True,
    # Broker — Celery 5+ requires this to silence warning + survive Redis restarts
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    # Visibility timeout — must exceed longest task to avoid duplicate delivery
    broker_transport_options={"visibility_timeout": 3600},
    result_backend_transport_options={"visibility_timeout": 3600},
)


# ── Beat schedule (periodic tasks) ─────────────────────────────────────
celery.conf.beat_schedule = {
    "recover-stale-scheduled-jobs": {
        "task": "tasks.pipeline_tasks.recover_stale_jobs",
        "schedule": 300.0,  # every 5 minutes
        "options": {"queue": "maintenance", "routing_key": "maintenance.recover"},
    },
    "cleanup-expired-results": {
        "task": "tasks.pipeline_tasks.cleanup_expired_results",
        "schedule": 3600.0,  # hourly
        "options": {"queue": "maintenance", "routing_key": "maintenance.cleanup"},
    },
}


# ── Logging + lifecycle signals ────────────────────────────────────────
@after_setup_logger.connect
def _setup_logger(logger, *args, **kwargs):
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(processName)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    for h in logger.handlers:
        h.setFormatter(fmt)


def _start_metrics_server():
    """Start Prometheus HTTP server in the worker process so task-emitted
    metrics (PIPELINE_RUNS, FEATURES_EXTRACTED, ACTIVE_PIPELINES, ...) become
    scrapable. With --pool=threads all task threads share this single process
    + registry, so all counter increments are exposed."""
    import os

    from prometheus_client import start_http_server

    port = int(os.getenv("WORKER_METRICS_PORT", "9100"))
    try:
        start_http_server(port, addr="0.0.0.0")
        logger.info("CELERY — worker metrics server listening on :%d", port)
    except OSError as exc:
        logger.debug("CELERY — metrics server bind skipped: %s", exc)


@worker_init.connect
def _on_worker_init(sender=None, **kwargs):
    # Threads / solo / gevent / eventlet pools: tasks run in the main worker
    # process. Bind here so metrics are scrapable.
    _start_metrics_server()


@worker_process_init.connect
def _on_worker_process_init(sender=None, **kwargs):
    # Prefork pool: tasks run in forked children. Only the first child to bind
    # will hold the port; the rest log a debug-level skip. Switch to
    # --pool=threads for full metric coverage with concurrency > 1.
    _start_metrics_server()


@worker_ready.connect
def _on_worker_ready(sender=None, **kwargs):
    logger.info("CELERY — worker ready | hostname=%s", getattr(sender, "hostname", "?"))


@task_prerun.connect
def _on_task_prerun(task_id=None, task=None, **kwargs):
    logger.info("CELERY — task START | id=%s | name=%s", task_id, getattr(task, "name", "?"))


@task_postrun.connect
def _on_task_postrun(task_id=None, task=None, state=None, **kwargs):
    logger.info(
        "CELERY — task END | id=%s | name=%s | state=%s",
        task_id, getattr(task, "name", "?"), state,
    )


@task_retry.connect
def _on_task_retry(request=None, reason=None, **kwargs):
    logger.warning("CELERY — task RETRY | id=%s | reason=%s",
                   getattr(request, "id", "?"), reason)


@task_failure.connect
def _on_task_failure(task_id=None, exception=None, **kwargs):
    logger.error("CELERY — task FAILED | id=%s | exc=%s", task_id, exception)


# CLI entry: `celery -A app.celery_app worker ...`
__all__ = ["celery"]
