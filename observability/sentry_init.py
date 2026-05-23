"""
Sentry setup — errors only by default so pipeline latency stays ~1–3 minutes.

100% tracing/profiling (traces_sample_rate=1.0) adds large overhead on Celery
workers and can push runs from minutes to 10+ minutes.
"""

from __future__ import annotations

import logging
import os
from typing import Callable, Optional, Sequence

import sentry_sdk

logger = logging.getLogger(__name__)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return default


def _sentry_before_send_factory() -> Callable:
    """Shared filter: drop expected business outcomes, keep real bugs."""

    def _before_send(event, hint):
        exc_info = hint.get("exc_info")
        if not exc_info:
            return event
        exc_type, exc_value, _ = exc_info
        msg = str(exc_value).lower()

        if exc_type.__name__ == "HTTPException":
            status = getattr(exc_value, "status_code", 500)
            if 400 <= status < 500:
                return None

        if exc_type is ValueError and any(
            kw in msg
            for kw in (
                "blocked keyword",
                "rate limit",
                "invalid company",
                "exceeds maximum length",
                "flagged as potentially malicious",
            )
        ):
            return None

        if any(
            kw in msg
            for kw in (
                "no features extracted",
                "no report",
                "no synthesis report",
                "empty report text",
            )
        ):
            return None

        return event

    return _before_send


def _traces_sampler() -> Callable:
    """Sample pipeline/Celery tasks at a separate (usually zero) rate."""

    pipeline_rate = _float_env("SENTRY_PIPELINE_TRACES_SAMPLE_RATE", 0.0)
    default_rate = _float_env("SENTRY_TRACES_SAMPLE_RATE", 0.0)

    def sampler(sampling_context) -> float:
        transaction = sampling_context.get("transaction_context") or {}
        name = transaction.get("name") or ""
        if name.startswith("tasks.") or "run_market_pipeline" in name:
            return pipeline_rate
        parent = sampling_context.get("parent_sampled")
        if parent is not None:
            return float(parent)
        return default_rate

    return sampler


def init_sentry(*, integrations: Optional[Sequence] = None) -> bool:
    """
    Initialize Sentry only when SENTRY_DSN_BACKEND is set.

    Defaults (no extra env): error events only — no performance traces, no profiling.
    """
    dsn = os.getenv("SENTRY_DSN_BACKEND", "").strip()
    if not dsn:
        return False

    traces_rate = _float_env("SENTRY_TRACES_SAMPLE_RATE", 0.0)
    profiles_rate = _float_env("SENTRY_PROFILES_SAMPLE_RATE", 0.0)
    pipeline_traces = _float_env("SENTRY_PIPELINE_TRACES_SAMPLE_RATE", 0.0)
    tracing_on = traces_rate > 0 or pipeline_traces > 0

    kwargs = {
        "dsn": dsn,
        "environment": os.getenv("SENTRY_ENVIRONMENT", "production"),
        "before_send": _sentry_before_send_factory(),
        "integrations": list(integrations or []),
        "enable_tracing": tracing_on,
    }
    if tracing_on:
        kwargs["traces_sampler"] = _traces_sampler()
    if profiles_rate > 0:
        kwargs["profiles_sample_rate"] = profiles_rate

    sentry_sdk.init(**kwargs)

    logger.info(
        "Sentry enabled (errors only=%s, traces=%s, pipeline_traces=%s, profiles=%s)",
        traces_rate == 0 and pipeline_traces == 0,
        traces_rate,
        pipeline_traces,
        profiles_rate,
    )
    return True
