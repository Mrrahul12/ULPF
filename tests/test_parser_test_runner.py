from backend.core.parser_test_generator import ParserTestGenerator
from backend.core.parser_test_runner import ParserTestRunner
from backend.models.parser_definition import ParserDefinition


def test_runner_passes_valid_parser():
    definition = ParserDefinition(
        parser_name="device_parser",
        format_type="key_value",
        mappings={
            "src_ip": "source_ip",
        },
    )

    generator = ParserTestGenerator()

    test_cases = generator.generate(
        definition,
        "src_ip=10.0.0.1",
    )

    results = ParserTestRunner().run(
        definition,
        test_cases,
    )

    assert len(results) == 1
    assert results[0]["passed"] is True
    assert results[0]["actual_fields"]["source_ip"] == "10.0.0.1"


def test_runner_detects_wrong_expected_value():
    definition = ParserDefinition(
        parser_name="device_parser",
        format_type="key_value",
        mappings={
            "src_ip": "source_ip",
        },
    )

    generator = ParserTestGenerator()

    test_cases = generator.generate(
        definition,
        "src_ip=10.0.0.1",
    )

    test_cases[0].expected_fields["source_ip"] = "192.168.1.1"

    results = ParserTestRunner().run(
        definition,
        test_cases,
    )

    assert results[0]["passed"] is False


def test_runner_rejects_unsafe_parser():
    definition = ParserDefinition(
        parser_name="device_parser",
        format_type="plain_text",
        mappings={
            "__import__('os').system('whoami')": "message",
        },
    )

    generator = ParserTestGenerator()

    test_cases = generator.generate(
        definition,
        "normal log",
    )

    results = ParserTestRunner().run(
        definition,
        test_cases,
    )

    assert results[0]["passed"] is False
    assert results[0]["errors"]