"""
Market Intelligence Scout — Celery application.

Single Celery instance used by workers (``celery -A app.celery_app``) and by FastAPI
to enqueue tasks defined in ``tasks.pipeline_tasks``.
"""

import os

from celery import Celery
from celery.signals import worker_process_init
from dotenv import load_dotenv
from prometheus_client import start_http_server

load_dotenv()

# Redis DB separation:
#   db=0 → application cache
#   db=1 → Celery broker
#   db=2 → Celery result backend
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
)
RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    f"redis://{REDIS_HOST}:{REDIS_PORT}/2",
)

celery = Celery(
    "market_scout",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_soft_time_limit=300,
    task_time_limit=360,
    result_expires=3600,
    result_extended=True,
    worker_max_tasks_per_child=50,
    worker_max_memory_per_child=512_000,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 600,
    },
    imports=("tasks.pipeline_tasks",),
)


@worker_process_init.connect
def _start_metrics_server(**_):
    """Expose Prometheus metrics from each worker child process."""
    start_http_server(9100)
