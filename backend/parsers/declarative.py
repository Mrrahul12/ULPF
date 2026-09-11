"""
Safe declarative parser adapter.

Converts a validated ParserDefinition into a BaseParser-compatible
parser without executing generated Python code.
"""

import json
from typing import Any, Dict, Tuple

from backend.models.parser_definition import ParserDefinition
from backend.parsers.base import BaseParser


class DeclarativeParser(BaseParser):
    """BaseParser implementation backed by safe declarative mappings."""

    def __init__(self, definition: ParserDefinition):
        super().__init__(
            name=definition.parser_name,
            version="generated-1.0",
        )
        self.definition = definition

    def detect(self, log: str) -> bool:
        """Detect whether the log matches the configured format."""
        if not isinstance(log, str) or not log:
            return False

        try:
            if self.definition.format_type == "json":
                value = json.loads(log)
                return isinstance(value, dict)

            if self.definition.format_type == "key_value":
                return "=" in log

            if self.definition.format_type == "plain_text":
                return bool(log.strip())

            return False

        except (ValueError, TypeError):
            return False

    def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
        """Parse the log using declarative format rules."""
        if not isinstance(log, str) or not log:
            return False, {}, "log must be a non-empty string"

        try:
            if self.definition.format_type == "json":
                parsed = json.loads(log)

                if not isinstance(parsed, dict):
                    return False, {}, "JSON parser requires an object"

                return True, parsed, ""

            if self.definition.format_type == "key_value":
                parsed = {}

                for token in log.split():
                    if "=" not in token:
                        continue

                    key, value = token.split("=", 1)
                    parsed[key] = value.strip('"')

                return True, parsed, ""

            if self.definition.format_type == "plain_text":
                return True, {"message": log}, ""

            return False, {}, (
                f"Unsupported format type: "
                f"{self.definition.format_type}"
            )

        except (ValueError, TypeError) as exc:
            return False, {}, str(exc)

    def normalize(
        self,
        parsed: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Apply declarative field mappings."""
        normalized = {}
        unmapped = {}

        for source_field, value in parsed.items():
            canonical_field = self.definition.mappings.get(source_field)

            if canonical_field:
                normalized[canonical_field] = value
            else:
                unmapped[source_field] = value

        if (
            self.definition.timestamp_field
            and self.definition.timestamp_field in parsed
        ):
            normalized["timestamp"] = parsed[
                self.definition.timestamp_field
            ]

        return normalized, unmapped