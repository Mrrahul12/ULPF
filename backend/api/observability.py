"""Request correlation and structured logging helpers."""

import logging
import time
from uuid import uuid4

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.api.tracing import request_span


logger = logging.getLogger("ulpf.api")


async def request_logging_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Attach a request ID and emit one structured request log."""
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started = time.perf_counter()
    with request_span(request.method, request.url.path) as (trace_id, span):
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        if span is not None:
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.duration_ms", duration_ms)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        logger.info(
            "request_completed method=%s path=%s status=%s duration_ms=%s request_id=%s trace_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
            trace_id,
        )
        return response
