"""Service for generating and running parser validation tests."""

from backend.core.parser_test_generator import ParserTestGenerator
from backend.core.parser_test_runner import ParserTestRunner
from backend.models.parser_definition import ParserDefinition


class ParserValidationService:
    """Coordinate parser test generation and execution."""

    def __init__(
        self,
        generator: ParserTestGenerator | None = None,
        runner: ParserTestRunner | None = None,
    ):
        self.generator = generator or ParserTestGenerator()
        self.runner = runner or ParserTestRunner()

    def validate(
        self,
        definition: ParserDefinition,
        raw_log: str,
    ) -> dict:
        """Generate tests and execute them against the parser."""

        test_cases = self.generator.generate(
            definition=definition,
            raw_log=raw_log,
        )

        results = self.runner.run(
            definition=definition,
            test_cases=test_cases,
        )

        passed = all(
            result["passed"]
            for result in results
        )

        return {
            "passed": passed,
            "total_tests": len(results),
            "passed_tests": sum(
                1
                for result in results
                if result["passed"]
            ),
            "failed_tests": sum(
                1
                for result in results
                if not result["passed"]
            ),
            "results": results,
        }