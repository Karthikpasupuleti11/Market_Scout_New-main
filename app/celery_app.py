import os
from celery import Celery
from celery.signals import worker_process_init
from prometheus_client import start_http_server
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from dotenv import load_dotenv

load_dotenv()

_redis_host = os.environ.get("REDIS_HOST", "redis")
_redis_port = os.environ.get("REDIS_PORT", "6379")

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN_BACKEND", ""),
    environment="development",
    integrations=[
        CeleryIntegration(),
    ],
    traces_sample_rate=1.0,
)

celery = Celery(
    "market_scout",
    broker=f"redis://{_redis_host}:{_redis_port}/0",
    backend=f"redis://{_redis_host}:{_redis_port}/1",
)


@worker_process_init.connect
def _start_metrics_server(**_):
    start_http_server(9100)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# IMPORTANT
# IMPORTANT
celery.conf.imports = (
    "tasks.pipeline_tasks",
    "tasks.serve_cached",
    "tasks.scheduled_tasks",
)