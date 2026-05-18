"""
Record pipeline completion metrics once per task (Celery worker process).

Metrics are written in the worker where the pipeline runs, then aggregated
via Prometheus multiprocess scraping on the API /metrics endpoint.
"""

import logging

logger = logging.getLogger(__name__)


def record_pipeline_completion(
    company: str,
    report: dict,
    *,
    failed: bool = False,
) -> None:
    """Increment counters and histograms for a finished pipeline run."""
    from observability.metrics import (
        CONFIDENCE_SCORE,
        FEATURES_EXTRACTED,
        FEATURES_VERIFIED,
        PIPELINE_RUNS,
        SOURCES_ANALYSED,
    )

    if failed:
        PIPELINE_RUNS.labels(status="error").inc()
        return

    features = report.get("features", []) if isinstance(report, dict) else []
    error_msg = None
    if isinstance(report, dict):
        meta = report.get("metadata")
        error_msg = meta.get("error") if isinstance(meta, dict) else None

    if error_msg and not features:
        PIPELINE_RUNS.labels(status="error").inc()
        return

    PIPELINE_RUNS.labels(status="completed").inc()

    for f in features:
        if not isinstance(f, dict):
            continue
        cat = f.get("category", "unknown")
        FEATURES_EXTRACTED.labels(company=company, category=cat).inc()
        CONFIDENCE_SCORE.observe(float(f.get("confidence_score") or 0))

    verified_count = int(report.get("total_features_verified", 0) or len(features))
    FEATURES_VERIFIED.labels(company=company).inc(verified_count)
    SOURCES_ANALYSED.observe(float(report.get("total_sources_analysed", 0) or 0))

    logger.info(
        "METRICS — Recorded: company=%s, features=%d, verified=%d, sources=%s",
        company,
        len(features),
        verified_count,
        report.get("total_sources_analysed", 0),
    )
