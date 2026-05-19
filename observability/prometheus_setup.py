"""
Prometheus metrics exposition for multi-process deployments.

Uvicorn runs multiple workers and Celery runs in a separate process; each has
its own in-memory registry by default. PROMETHEUS_MULTIPROC_DIR lets all processes
write to shared files that are aggregated on GET /metrics.
"""

import logging
import os
import shutil

logger = logging.getLogger(__name__)


def prepare_multiproc_dir() -> None:
    """Create (and optionally reset) the multiprocess metrics directory."""
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not multiproc_dir:
        return
    if os.path.isdir(multiproc_dir):
        shutil.rmtree(multiproc_dir, ignore_errors=True)
    os.makedirs(multiproc_dir, exist_ok=True)


def _remove_empty_db_files(multiproc_dir: str) -> int:
    """Delete zero-byte .db files that cause parse errors. Returns count removed."""
    removed = 0
    try:
        for fname in os.listdir(multiproc_dir):
            if not fname.endswith(".db"):
                continue
            fpath = os.path.join(multiproc_dir, fname)
            try:
                if os.path.getsize(fpath) == 0:
                    os.remove(fpath)
                    removed += 1
                    logger.warning("Removed zero-byte Prometheus db file: %s", fpath)
            except OSError:
                pass
    except OSError:
        pass
    return removed


def _remove_all_multiprocess_files(multiproc_dir: str) -> int:
    """Delete every regular file in the multiproc dir (corrupt / stale merge data).

    Safe for a directory used only for PROMETHEUS_MULTIPROC_DIR. Avoids
    JSONDecodeError from truncated or non-JSON keys left by crashed processes.
    """
    removed = 0
    try:
        for fname in os.listdir(multiproc_dir):
            fpath = os.path.join(multiproc_dir, fname)
            try:
                if os.path.isfile(fpath):
                    os.remove(fpath)
                    removed += 1
            except OSError:
                pass
    except OSError:
        pass
    if removed:
        logger.warning(
            "Prometheus multiprocess — removed %d file(s) from %s for scrape recovery",
            removed,
            multiproc_dir,
        )
    return removed


def create_metrics_asgi_app():
    """Return an ASGI app that exposes aggregated Prometheus metrics.

    In multiprocess mode (PROMETHEUS_MULTIPROC_DIR set), the registry is built
    fresh on every scrape request so a corrupt file on one request auto-recovers
    on the next. Any exception during collection is caught and a graceful empty
    response is returned instead of a 500.
    """
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")

    if multiproc_dir:
        async def safe_metrics_app(scope, receive, send):
            """Resilient /metrics ASGI endpoint — survives corrupt db files."""
            if scope["type"] != "http":
                return

            # Lazy import so module-level import never crashes
            from prometheus_client import (
                CollectorRegistry,
                generate_latest,
                multiprocess,
                CONTENT_TYPE_LATEST,
            )

            # Multiple attempts: empty-file cleanup, then full dir wipe for corrupt keys
            for attempt in range(3):
                try:
                    registry = CollectorRegistry()
                    multiprocess.MultiProcessCollector(registry)
                    output = generate_latest(registry)
                    await send({
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [
                            [b"content-type", CONTENT_TYPE_LATEST.encode()],
                            [b"content-length", str(len(output)).encode()],
                        ],
                    })
                    await send({"type": "http.response.body", "body": output})
                    return
                except Exception as exc:
                    if attempt == 0:
                        cleaned = _remove_empty_db_files(multiproc_dir)
                        logger.warning(
                            "Prometheus scrape failed (attempt 1), "
                            "cleaned %d empty file(s): %s",
                            cleaned, exc,
                        )
                    elif attempt == 1:
                        cleaned = _remove_all_multiprocess_files(multiproc_dir)
                        logger.warning(
                            "Prometheus scrape failed (attempt 2), "
                            "wiped %d multiproc file(s), retrying: %s",
                            cleaned, exc,
                        )
                    else:
                        logger.error(
                            "Prometheus scrape failed after full wipe (attempt 3): %s", exc
                        )

            # All attempts failed — return 200 with comment so Prometheus
            # marks the target as UP but shows stale/no data instead of DOWN.
            body = b"# Prometheus metrics temporarily unavailable\n"
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", b"text/plain; version=0.0.4; charset=utf-8"],
                    [b"content-length", str(len(body)).encode()],
                ],
            })
            await send({"type": "http.response.body", "body": body})

        return safe_metrics_app

    # No multiprocess dir — use simple default single-process app
    from prometheus_client import make_asgi_app
    return make_asgi_app()
