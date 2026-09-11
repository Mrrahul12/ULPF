"""Generate deterministic test cases for parser definitions."""

from backend.models.parser_definition import ParserDefinition
from backend.models.parser_test_case import ParserTestCase


class ParserTestGenerator:
    """Generate safe, deterministic parser test cases."""

    def generate(
        self,
        definition: ParserDefinition,
        raw_log: str,
    ) -> list[ParserTestCase]:
        """Generate test cases from a parser definition and sample log."""

        expected_fields = self._expected_fields(
            definition,
            raw_log,
        )

        return [
            ParserTestCase(
                name="basic_parser_test",
                raw_log=raw_log,
                expected_fields=expected_fields,
                description="Verify parser extracts expected fields.",
            )
        ]

    @staticmethod
    def _expected_fields(
        definition: ParserDefinition,
        raw_log: str,
    ) -> dict:
        """Build expected canonical fields from the sample log."""

        if definition.format_type == "plain_text":
            source_fields = {
                "message": raw_log,
            }

        elif definition.format_type == "key_value":
            source_fields = {}

            for token in raw_log.split():
                if "=" not in token:
                    continue

                key, value = token.split("=", 1)
                source_fields[key] = value

        elif definition.format_type == "json":
            import json

            value = json.loads(raw_log)

            if not isinstance(value, dict):
                raise ValueError(
                    "JSON parser requires a JSON object"
                )

            source_fields = value

        else:
            raise ValueError(
                f"Unsupported format type: {definition.format_type}"
            )

        expected = {}

        for source_field, canonical_field in definition.mappings.items():
            if source_field in source_fields:
                expected[canonical_field] = source_fields[source_field]

        if (
            definition.timestamp_field
            and definition.timestamp_field in source_fields
        ):
            expected["timestamp"] = source_fields[
                definition.timestamp_field
            ]

        return expected