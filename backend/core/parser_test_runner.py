"""Run automatically generated parser tests safely."""

from backend.core.parser_sandbox import ParserSandbox
from backend.models.parser_definition import ParserDefinition
from backend.models.parser_test_case import ParserTestCase


class ParserTestRunner:
    """Execute parser test cases using the secure sandbox."""

    def __init__(self, sandbox: ParserSandbox | None = None):
        self.sandbox = sandbox or ParserSandbox()

    def run(
        self,
        definition: ParserDefinition,
        test_cases: list[ParserTestCase],
    ) -> list[dict]:
        """Run all test cases and return deterministic results."""

        results = []

        for test_case in test_cases:
            sandbox_result = self.sandbox.run(
                definition=definition,
                raw_log=test_case.raw_log,
            )

            passed = (
                sandbox_result.success
                and sandbox_result.safe
                and self._fields_match(
                    sandbox_result.parsed_fields,
                    test_case.expected_fields,
                )
            )

            results.append(
                {
                    "name": test_case.name,
                    "passed": passed,
                    "expected_fields": test_case.expected_fields,
                    "actual_fields": sandbox_result.parsed_fields,
                    "errors": sandbox_result.errors,
                }
            )

        return results

    @staticmethod
    def _fields_match(
        actual: dict,
        expected: dict,
    ) -> bool:
        """Check that all expected fields match parsed values."""

        for field, expected_value in expected.items():
            if actual.get(field) != expected_value:
                return False

        return True