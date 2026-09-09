"""Optional OpenTelemetry setup for ULPF request tracing."""

import os
from contextlib import contextmanager
from typing import Iterator
from uuid import uuid4

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only in minimal installations
    OTEL_AVAILABLE = False


TRACER_NAME = "ulpf.api"


def configure_tracing() -> bool:
    """Configure an OpenTelemetry provider when tracing is enabled."""
    if not OTEL_AVAILABLE or os.getenv("ULPF_OTEL_ENABLED", "true").lower() != "true":
        return False

    provider = TracerProvider(
        resource=Resource.create(
            {"service.name": os.getenv("OTEL_SERVICE_NAME", "ulpf")}
        )
    )
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    elif os.getenv("ULPF_OTEL_CONSOLE_EXPORT", "false").lower() == "true":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return True


@contextmanager
def request_span(method: str, path: str) -> Iterator[tuple[str, object | None]]:
    """Create a server span and yield its trace ID."""
    if not OTEL_AVAILABLE or os.getenv("ULPF_OTEL_ENABLED", "true").lower() != "true":
        yield str(uuid4()), None
        return

    tracer = trace.get_tracer(TRACER_NAME)
    with tracer.start_as_current_span(f"{method} {path}") as span:
        span.set_attribute("http.method", method)
        span.set_attribute("http.route", path)
        context = span.get_span_context()
        trace_id = format(context.trace_id, "032x") if context.is_valid else str(uuid4())
        yield trace_id, span
