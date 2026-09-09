"""Validation for canonical ULPF events."""

from typing import Any, List
from pydantic import ValidationError

from backend.config import MAX_PORT, MIN_PORT
from backend.models.event import CanonicalEvent


class EventValidationError(ValueError):
    """Raised when canonical event validation fails."""


class EventValidator:
    """Validate canonical events and enforce network port constraints."""

    def validate(self, data: CanonicalEvent | dict[str, Any]) -> CanonicalEvent:
        """Return a validated event or raise EventValidationError."""
        try:
            event = data if isinstance(data, CanonicalEvent) else CanonicalEvent.model_validate(data)
        except ValidationError as exc:
            raise EventValidationError(str(exc)) from exc

        invalid_ports: List[str] = []
        for label, port in (
            ("source.port", event.source.port),
            ("destination.port", event.destination.port),
        ):
            if port is not None and not MIN_PORT <= port <= MAX_PORT:
                invalid_ports.append(f"{label} must be between {MIN_PORT} and {MAX_PORT}")
        if invalid_ports:
            raise EventValidationError("; ".join(invalid_ports))
        return event
