"""
Market Intelligence Scout — OpenTelemetry Tracing

Distributed tracing for the pipeline with:
  • Automatic FastAPI instrumentation
  • Custom spans per pipeline node
  • Trace context propagation
  • Exportable to Jaeger, Zipkin, or OTLP backends
"""

import logging
from contextlib import contextmanager
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Tracer Setup
# ────────────────────────────────────────────────────────────────────

_tracer: Optional[trace.Tracer] = None


def setup_tracing(app, service_name: str = "market-intelligence-scout"):
    """Initialise OpenTelemetry tracing and instrument FastAPI.

    Disabled by default — console span export adds I/O overhead on every request.
    Set OTEL_ENABLED=true to turn on (development / Jaeger wiring).
    """
    import os

    if os.getenv("OTEL_ENABLED", "").strip().lower() not in ("1", "true", "yes"):
        logger.info("TRACING — OpenTelemetry skipped (set OTEL_ENABLED=true to enable)")
        return

    global _tracer

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(__name__)

    FastAPIInstrumentor.instrument_app(app)
    logger.info("TRACING — OpenTelemetry initialised for '%s'", service_name)


def get_tracer() -> trace.Tracer:
    """Return the application tracer, or a no-op if not initialised."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer


# ────────────────────────────────────────────────────────────────────
# Convenience Decorator / Context Manager
# ────────────────────────────────────────────────────────────────────

@contextmanager
def trace_node(node_name: str, attributes: Optional[dict] = None):
    """Context manager to create a span for a pipeline node.

    Usage:
        with trace_node("guardrails", {"company": "OpenAI"}):
            # ... node logic ...
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(
        f"pipeline.{node_name}",
        attributes=attributes or {},
    ) as span:
        try:
            yield span
        except Exception as exc:
            span.set_status(trace.StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
