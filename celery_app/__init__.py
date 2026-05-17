"""
Market Intelligence Scout — Celery Application Factory

Creates the Celery app instance with Redis broker/backend.
Shared by FastAPI (to enqueue) and workers (to execute).
"""

from celery import Celery
from dotenv import load_dotenv
import os

load_dotenv()

# ── Redis DB separation ────────────────────────────────────────────
#   db=0  → application cache  (existing, unchanged)
#   db=1  → Celery broker
#   db=2  → Celery result backend
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

celery_app = Celery(
    "market_scout",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

# ── Celery configuration ──────────────────────────────────────────
celery_app.conf.update(
    # Serialization — JSON only (safe, no pickle)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task behavior
    task_acks_late=True,                     # Re-queue if worker crashes
    task_reject_on_worker_lost=True,         # Don't lose tasks on OOM kill
    worker_prefetch_multiplier=1,            # Don't prefetch (long tasks)
    task_track_started=True,                 # Track STARTED state
    task_soft_time_limit=300,                # 5-min soft limit (raises exception)
    task_time_limit=360,                     # 6-min hard kill

    # Result backend
    result_expires=3600,                     # Results expire after 1 hour
    result_extended=True,                    # Store task name + args in result

    # Worker
    worker_max_tasks_per_child=50,           # Recycle workers (Playwright memory)
    worker_max_memory_per_child=512_000,     # 512MB per worker child (KB)

    # Broker connection
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 600,           # 10 min — must exceed task_time_limit
    },
)

# ── Auto-discover tasks ───────────────────────────────────────────
celery_app.autodiscover_tasks(["celery_app"])
