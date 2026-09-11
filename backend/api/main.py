"""FastAPI entry point for the ULPF log processing service."""

import logging
import os
from fastapi import HTTPException
from backend.core.approval_service import ApprovalService
from backend.models.parser_approval import ParserApproval
from backend.models.parser_approval_request import ParserApprovalRequest
from backend.core.local_ai_mock import DeterministicLocalAI
from backend.core.pipeline import LogProcessingPipeline
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from starlette.responses import PlainTextResponse
from backend.models.parser_validation_request import (
    ParserValidationRequest,
)
from backend.core.unknown_log_intelligence import analyze_unknown_log
from backend.core.pipeline import LogProcessingPipeline, PipelineError, register_builtin_parsers
from backend.models.event import EventResponse, ParseError, FieldExplanation
from backend.core.parser_validation_service import (
    ParserValidationService,
)
from backend.models.parser_definition import ParserDefinition
from backend.core.explainability import explain_field
from backend.api.security import (
    RateLimitExceeded,
    RateLimiter,
    RequestMetrics,
    configured_api_key,
    configured_rate_limit,
)
from backend.api.observability import request_logging_middleware
from backend.api.tracing import configure_tracing


MAX_LOG_MESSAGE_LENGTH = 64 * 1024


class LogRequest(BaseModel):
    """Request body containing one raw log message."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_LOG_MESSAGE_LENGTH,
        description="Original log message",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        """Reject messages that contain only whitespace."""
        if not value.strip():
            raise ValueError("message must contain non-whitespace characters")
        return value

class ExplainRequest(BaseModel):
    """Request body for explaining one canonical field."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_LOG_MESSAGE_LENGTH,
        description="Original log message",
    )

    field: str = Field(
        ...,
        min_length=1,
        description="Canonical field to explain",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        """Reject messages that contain only whitespace."""
        if not value.strip():
            raise ValueError("message must contain non-whitespace characters")
        return value

    @field_validator("field")
    @classmethod
    def validate_field(cls, value: str) -> str:
        """Reject fields that contain only whitespace."""
        if not value.strip():
            raise ValueError("field must contain non-whitespace characters")
        return value.strip()


app = FastAPI(
    title="ULPF - Universal Log Pre-processing Framework",
    version="0.1.0",
    description="Phase 1 canonical log normalization engine",
)
app.middleware("http")(request_logging_middleware)
MAX_REQUEST_BODY_BYTES = 70 * 1024


@app.middleware("http")
async def request_size_limit_middleware(request: Request, call_next):
    """Reject HTTP requests whose declared body is too large."""
    content_length = request.headers.get("content-length")

    if content_length:
        try:
            body_size = int(content_length)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid Content-Length",
            )

        if body_size > MAX_REQUEST_BODY_BYTES:
            return PlainTextResponse(
                "Request body too large",
                status_code=413,
            )

    return await call_next(request)

logging.basicConfig(
    level=os.getenv("ULPF_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
configure_tracing()

register_builtin_parsers()
pipeline = LogProcessingPipeline()
_rate_limit, _rate_window = configured_rate_limit()
rate_limiter = RateLimiter(_rate_limit, _rate_window)
metrics = RequestMetrics()


@app.get("/health")
def health() -> dict[str, str]:
    """Return service readiness."""
    return {"status": "ok"}


@app.get("/metrics")
def service_metrics() -> dict[str, int]:
    """Return process-local request counters."""
    return metrics.snapshot()


@app.get("/metrics/prometheus", response_class=PlainTextResponse)
def prometheus_metrics() -> str:
    """Return counters in Prometheus text exposition format."""
    snapshot = metrics.snapshot()
    lines = [
        "# HELP ulpf_requests_total Total HTTP requests received.",
        "# TYPE ulpf_requests_total counter",
        f"ulpf_requests_total {snapshot['total_requests']}",
        "# HELP ulpf_parse_success_total Successfully parsed log requests.",
        "# TYPE ulpf_parse_success_total counter",
        f"ulpf_parse_success_total {snapshot['successful_parses']}",
        "# HELP ulpf_parse_failure_total Log requests that could not be parsed.",
        "# TYPE ulpf_parse_failure_total counter",
        f"ulpf_parse_failure_total {snapshot['failed_parses']}",
        "# HELP ulpf_rejected_requests_total Authentication or rate-limit rejections.",
        "# TYPE ulpf_rejected_requests_total counter",
        f"ulpf_rejected_requests_total {snapshot['rejected_requests']}",
    ]
    return "\n".join(lines) + "\n"


@app.post("/parse", response_model=EventResponse)
def parse_log(
    request: LogRequest,
    http_request: Request,
    x_api_key: str | None = Header(default=None),
) -> EventResponse:
    """Parse one raw log into a canonical event."""
    metrics.record_request()
    expected_key = configured_api_key()
    if expected_key is not None and x_api_key != expected_key:
        metrics.record_rejection()
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    client_id = http_request.client.host if http_request.client else "unknown"

    hpa_test_mode = os.getenv("ULPF_HPA_TEST_MODE", "").strip().lower() == "true"

    if not hpa_test_mode:
        try:
            rate_limiter.check(client_id)
        except RateLimitExceeded:
            metrics.record_rejection()
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:
        event = pipeline.process(request.message)
        metrics.record_success()
        return EventResponse(accepted=True, event=event)
    except PipelineError as exc:
        metrics.record_failure()
        return EventResponse(
            accepted=False,
            error=ParseError(
                status="parse_failure",
                message=str(exc),
                raw_message=request.message,
            ),
        )


@app.post("/explain", response_model=FieldExplanation)
def explain_log_field(
    request: ExplainRequest,
    http_request: Request,
    x_api_key: str | None = Header(default=None),
) -> FieldExplanation:
    """Process a log and explain how one canonical field was produced."""
    metrics.record_request()

    expected_key = configured_api_key()
    if expected_key is not None and x_api_key != expected_key:
        metrics.record_rejection()
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )

    client_id = http_request.client.host if http_request.client else "unknown"

    hpa_test_mode = (
        os.getenv("ULPF_HPA_TEST_MODE", "").strip().lower() == "true"
    )

    if not hpa_test_mode:
        try:
            rate_limiter.check(client_id)
        except RateLimitExceeded:
            metrics.record_rejection()
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
            )

    try:
        event = pipeline.process(request.message)
        explanation = explain_field(
            event.provenance,
            request.field,
        )
        metrics.record_success()
        return explanation

    except PipelineError as exc:
        metrics.record_failure()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except KeyError as exc:
        metrics.record_failure()
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

@app.post("/api/unknown/analyze")
def analyze_unknown_endpoint(payload: dict):
    """Analyze an unrecognized log without invoking an AI service."""
    raw_log = payload.get("raw_log")

    if not isinstance(raw_log, str):
        raise HTTPException(
            status_code=400,
            detail="raw_log must be a string",
        )

    return analyze_unknown_log(raw_log)

@app.post("/api/parser-factory/propose")
def parser_factory_propose_endpoint(payload: dict):
    """Generate a validated parser proposal for an unknown log."""

    raw_log = payload.get("raw_log")

    if not isinstance(raw_log, str) or not raw_log.strip():
        raise HTTPException(
            status_code=400,
            detail="raw_log must be a non-empty string",
        )

    pipeline = LogProcessingPipeline()
    adapter = DeterministicLocalAI()

    proposal = pipeline.generate_parser_proposal(
        raw_log=raw_log,
        adapter=adapter,
    )

    return proposal

@app.post("/api/parser-factory/validate")
def validate_parser_definition(
    request: ParserValidationRequest,
):
    """Generate and run automated tests for a parser definition."""

    service = ParserValidationService()

    return service.validate(
        definition=request.definition,
        raw_log=request.raw_log,
    )

@app.post("/api/parser-approval/approve")
def approve_parser(request: ParserApprovalRequest):
    """Approve a pending parser proposal through human review."""

    approval = ParserApproval(
        parser_name=request.parser_name,
    )

    service = ApprovalService()

    try:
        result = service.approve(
            approval=approval,
            reviewer=request.reviewer,
            comment=request.comment,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return result

@app.post("/api/parser-approval/reject")
def reject_parser(request: ParserApprovalRequest):
    """Reject a pending parser proposal through human review."""

    approval = ParserApproval(
        parser_name=request.parser_name,
    )

    service = ApprovalService()

    try:
        result = service.reject(
            approval=approval,
            reviewer=request.reviewer,
            comment=request.comment,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return result