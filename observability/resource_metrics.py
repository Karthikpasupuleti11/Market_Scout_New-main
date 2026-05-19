"""
Host process resource gauges compatible with Prometheus multiprocess mode.

Default process_* metrics are not aggregated across uvicorn workers in
multiprocess mode, so we expose app_* metrics updated per worker.
"""

import os
import resource
import threading
import time

from prometheus_client import Counter, Gauge

APP_CPU_PERCENT = Gauge(
    "app_cpu_percent",
    "Approximate CPU usage percent for this worker process",
    multiprocess_mode="max",
)
APP_MEMORY_BYTES = Gauge(
    "app_resident_memory_bytes",
    "Resident memory (RSS) of this worker process",
    multiprocess_mode="livesum",
)
APP_GC_COLLECTIONS = Counter(
    "app_gc_collections_total",
    "Python GC collections in this worker (by generation)",
    ["generation"],
)

_prev_gc_collections: list = [0, 0, 0]
_prev_cpu_seconds: float = 0.0


def _read_rss_bytes() -> float:
    """Best-effort RSS for Linux /proc, fallback to ru_maxrss."""
    try:
        with open("/proc/self/statm", encoding="ascii") as f:
            pages = int(f.read().split()[1])
        page_size = os.sysconf("SC_PAGE_SIZE")
        return float(pages * page_size)
    except (OSError, ValueError, IndexError):
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return float(usage.ru_maxrss * 1024)


def _update_gc_counters() -> None:
    import gc

    global _prev_gc_collections
    if not hasattr(gc, "get_stats"):
        return
    stats = gc.get_stats()
    for i, stat in enumerate(stats[:3]):
        total = int(stat.get("collections", 0))
        delta = total - _prev_gc_collections[i]
        _prev_gc_collections[i] = total
        if delta > 0:
            APP_GC_COLLECTIONS.labels(generation=str(i)).inc(delta)


def _update_resource_gauges(interval_seconds: float) -> None:
    global _prev_cpu_seconds
    usage = resource.getrusage(resource.RUSAGE_SELF)
    cpu_total = usage.ru_utime + usage.ru_stime
    cpu_delta = max(cpu_total - _prev_cpu_seconds, 0.0)
    _prev_cpu_seconds = cpu_total
    APP_CPU_PERCENT.set(min((cpu_delta / interval_seconds) * 100.0, 100.0))
    APP_MEMORY_BYTES.set(_read_rss_bytes())
    _update_gc_counters()


def start_resource_metrics_collector(interval_seconds: float = 15.0) -> None:
    """Background loop updating per-worker resource gauges."""

    def _loop():
        while True:
            try:
                _update_resource_gauges(interval_seconds)
            except Exception:
                pass
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_loop, name="resource-metrics", daemon=True)
    thread.start()
