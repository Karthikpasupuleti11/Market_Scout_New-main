"""
Prometheus metrics exposition for multi-process deployments.

Uvicorn runs multiple workers and Celery runs in a separate process; each has
its own in-memory registry by default. PROMETHEUS_MULTIPROC_DIR lets all processes
write to shared files that are aggregated on GET /metrics.
"""

import os
import shutil

from prometheus_client import CollectorRegistry, make_asgi_app, multiprocess


def prepare_multiproc_dir() -> None:
    """Create (and optionally reset) the multiprocess metrics directory."""
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not multiproc_dir:
        return
    if os.path.isdir(multiproc_dir):
        shutil.rmtree(multiproc_dir, ignore_errors=True)
    os.makedirs(multiproc_dir, exist_ok=True)


def create_metrics_asgi_app():
    """Return an ASGI app that exposes aggregated Prometheus metrics."""
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if multiproc_dir:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return make_asgi_app(registry=registry)
    return make_asgi_app()
