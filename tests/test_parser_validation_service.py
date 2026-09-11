from backend.core.parser_validation_service import (
    ParserValidationService,
)
from backend.models.parser_definition import ParserDefinition


def test_validation_service_passes_valid_parser():
    definition = ParserDefinition(
        parser_name="device_parser",
        format_type="key_value",
        mappings={
            "src_ip": "source_ip",
        },
    )

    result = ParserValidationService().validate(
        definition,
        "src_ip=10.0.0.1",
    )

    assert result["passed"] is True
    assert result["total_tests"] == 1
    assert result["passed_tests"] == 1
    assert result["failed_tests"] == 0


def test_validation_service_rejects_unsafe_parser():
    definition = ParserDefinition(
        parser_name="device_parser",
        format_type="plain_text",
        mappings={
            "__import__('os').system('whoami')": "message",
        },
    )

    result = ParserValidationService().validate(
        definition,
        "normal log",
    )

    assert result["passed"] is False
    assert result["total_tests"] == 1
    assert result["failed_tests"] == 1


def test_validation_service_returns_test_results():
    definition = ParserDefinition(
        parser_name="device_parser",
        format_type="key_value",
        mappings={
            "src_ip": "source_ip",
        },
    )

    result = ParserValidationService().validate(
        definition,
        "src_ip=10.0.0.1",
    )

    assert len(result["results"]) == 1
    assert result["results"][0]["name"] == "basic_parser_test"
    assert result["results"][0]["passed"] is True