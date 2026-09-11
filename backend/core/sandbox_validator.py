"""Validation of parser proposals using sandbox execution."""

from backend.models.parser_definition import ParserDefinition
from backend.models.sandbox_result import SandboxResult
from backend.core.parser_sandbox import ParserSandbox


class SandboxValidator:
    """Validate parser definitions against representative sample logs."""

    def __init__(self, sandbox: ParserSandbox | None = None):
        self.sandbox = sandbox or ParserSandbox()

    def validate(
        self,
        definition: ParserDefinition,
        raw_log: str,
        expected_fields: list[str],
    ) -> SandboxResult:
        """Run the sandbox and verify expected fields are produced."""

        result = self.sandbox.run(
            definition=definition,
            raw_log=raw_log,
        )

        if not result.success:
            return result

        missing_fields = [
            field
            for field in expected_fields
            if field not in result.parsed_fields
        ]

        if missing_fields:
            result.success = False
            result.errors.extend(
                [
                    f"Missing expected field: {field}"
                    for field in missing_fields
                ]
            )

        return result