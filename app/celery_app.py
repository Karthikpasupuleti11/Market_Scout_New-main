from celery import Celery
from celery.signals import worker_process_init
from prometheus_client import start_http_server

celery = Celery(
    "market_scout",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1"
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
)