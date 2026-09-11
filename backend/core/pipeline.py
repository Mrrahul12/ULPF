"""Lossless log processing pipeline for ULPF Phase 1."""

from typing import Any

from backend.core.detector import SourceDetector
from backend.core.normalizer import EventNormalizer
from backend.core.provenance import (
    build_field_provenance,
    build_provenance,
)
from backend.core.validator import EventValidationError, EventValidator
from backend.models.event import CanonicalEvent
from backend.parsers.registry import get_registry


class PipelineError(ValueError):
    """Raised when a log cannot be converted into a canonical event."""


class LogProcessingPipeline:
    """Coordinate detection, parsing, normalization, provenance, and validation."""

    def __init__(self):
        self.registry = get_registry()
        self.detector = SourceDetector()
        self.normalizer = EventNormalizer()
        self.validator = EventValidator()

    def process(self, raw_log: str) -> CanonicalEvent:
        """Process one raw log and return a validated canonical event."""
        if not isinstance(raw_log, str) or not raw_log:
            raise PipelineError("raw_log must be a non-empty string")

        source = self.detector.detect(raw_log)
        if source == "unknown":
            raise PipelineError("No registered parser detected the log")

        parser = self.registry.get_parser(source)
        if parser is None:
            raise PipelineError(f"Detected parser '{source}' is not registered")

        success, parsed, error = parser.parse(raw_log)
        if not success:
            raise PipelineError(error or f"Parser '{source}' failed")

        normalized_fields, unmapped = parser.normalize(dict(parsed))

        field_provenance = build_field_provenance(
            dict(parsed),
            normalized_fields,
        )

        event_data, unmapped = self.normalizer.normalize(
            normalized_fields,
            unmapped,
        )

        event_data["raw"] = {"message": raw_log}
        event_data["unmapped"] = unmapped
        event_data["provenance"] = build_provenance(
            parser.name,
            parser.version,
            field_provenance,
        )

        try:
            return self.validator.validate(event_data)
        except EventValidationError as exc:
            raise PipelineError(str(exc)) from exc


def register_builtin_parsers() -> None:
    """Register all built-in parsers once in the global registry."""
    from backend.parsers.cisco_asa import CiscoASAParser
    from backend.parsers.fortinet import FortinetParser
    from backend.parsers.json_parser import JSONParser
    from backend.parsers.paloalto import PaloAltoParser
    from backend.parsers.syslog import SyslogParser

    registry = get_registry()
    for parser in (JSONParser(), CiscoASAParser(), FortinetParser(), PaloAltoParser(), SyslogParser()):
        registry.update(parser)
