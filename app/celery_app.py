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


def _sentry_before_send(event, hint):
    """Filter out expected business-logic outcomes — keep only real errors."""
    exc_info = hint.get("exc_info")
    if exc_info:
        exc_type, exc_value, _ = exc_info
        msg = str(exc_value).lower()
        exc_name = exc_type.__name__

        # Ignore safely handled third-party API exceptions (e.g. NVIDIA/Tavily retries)
        if exc_name in ("PermissionDeniedError", "AuthenticationError", "RateLimitError"):
            return None

        # Ignore non-fatal Redis cache read-only errors
        if exc_name == "ReadOnlyError" or "read only replica" in msg:
            return None

        # ValueError from guardrails / validation = expected user input issues
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
    environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
    before_send=_sentry_before_send,
    integrations=[CeleryIntegration()],
    traces_sample_rate=float(os.environ.get("SENTRY_PIPELINE_TRACES_SAMPLE_RATE", 0.0)),
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