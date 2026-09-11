"""Safe declarative parser sandbox."""

import re
import time
from backend.core.sandbox_security import (
    SandboxSecurityError,
    validate_parser_security,
)
from backend.models.parser_definition import ParserDefinition
from backend.models.sandbox_result import SandboxResult


class ParserSandbox:
    """Execute declarative parser definitions without arbitrary code execution."""

    def run(
        self,
        definition: ParserDefinition,
        raw_log: str,
    ) -> SandboxResult:
        """Apply a parser definition to one sample log."""

        start = time.perf_counter()

        if not isinstance(raw_log, str) or not raw_log:
            return SandboxResult(
                success=False,
                safe=True,
                parser_name=definition.parser_name,
                format_type=definition.format_type,
                errors=["raw_log must be a non-empty string"],
                execution_time_ms=self._elapsed_ms(start),
            )

        try:
            validate_parser_security(definition)

            parsed_fields = self._parse(definition, raw_log)

            return SandboxResult(
                success=True,
                safe=True,
                parser_name=definition.parser_name,
                format_type=definition.format_type,
                parsed_fields=parsed_fields,
                execution_time_ms=self._elapsed_ms(start),
            )

        except SandboxSecurityError as exc:
            return SandboxResult(
                success=False,
                safe=False,
                parser_name=definition.parser_name,
                format_type=definition.format_type,
                errors=[str(exc)],
                execution_time_ms=self._elapsed_ms(start),
            )

        except Exception as exc:
            return SandboxResult(
                success=False,
                safe=True,
                parser_name=definition.parser_name,
                format_type=definition.format_type,
                errors=[str(exc)],
                execution_time_ms=self._elapsed_ms(start),
            )

    def _parse(
        self,
        definition: ParserDefinition,
        raw_log: str,
    ) -> dict:
        if definition.format_type == "key_value":
            source_fields = self._extract_key_values(raw_log)

        elif definition.format_type == "json":
            source_fields = self._extract_json(raw_log)

        elif definition.format_type == "plain_text":
            source_fields = {
                "message": raw_log,
            }

        else:
            raise ValueError(
                f"Unsupported format type: {definition.format_type}"
            )

        result = {}

        for source_field, canonical_field in definition.mappings.items():
            if source_field in source_fields:
                result[canonical_field] = source_fields[source_field]

        if definition.timestamp_field:
            if definition.timestamp_field in source_fields:
                result["timestamp"] = source_fields[
                    definition.timestamp_field
                ]

        return result

    @staticmethod
    def _extract_key_values(raw_log: str) -> dict:
        pattern = re.compile(
            r"\b([A-Za-z_][A-Za-z0-9_.-]*)=([^\s]+)"
        )

        return {
            match.group(1): match.group(2)
            for match in pattern.finditer(raw_log)
        }

    @staticmethod
    def _extract_json(raw_log: str) -> dict:
        import json

        value = json.loads(raw_log)

        if not isinstance(value, dict):
            raise ValueError("JSON parser requires a JSON object")

        return value

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        return (time.perf_counter() - start) * 1000