from backend.core.parser_test_generator import ParserTestGenerator
from backend.models.parser_definition import ParserDefinition


def test_generator_creates_key_value_test():
    definition = ParserDefinition(
        parser_name="device_parser",
        format_type="key_value",
        mappings={
            "src_ip": "source_ip",
            "dst_ip": "destination_ip",
        },
    )

    generator = ParserTestGenerator()

    tests = generator.generate(
        definition,
        "src_ip=10.0.0.1 dst_ip=10.0.0.2",
    )

    assert len(tests) == 1
    assert tests[0].name == "basic_parser_test"
    assert tests[0].expected_fields == {
        "source_ip": "10.0.0.1",
        "destination_ip": "10.0.0.2",
    }


def test_generator_creates_plain_text_test():
    definition = ParserDefinition(
        parser_name="device_parser",
        format_type="plain_text",
        mappings={
            "message": "message",
        },
    )

    generator = ParserTestGenerator()

    tests = generator.generate(
        definition,
        "Firewall connection blocked",
    )

    assert len(tests) == 1
    assert tests[0].expected_fields == {
        "message": "Firewall connection blocked",
    }


def test_generator_creates_timestamp_test():
    definition = ParserDefinition(
        parser_name="device_parser",
        format_type="key_value",
        mappings={
            "src_ip": "source_ip",
        },
        timestamp_field="timestamp",
    )

    generator = ParserTestGenerator()

    tests = generator.generate(
        definition,
        "timestamp=2026-09-11T10:00:00Z src_ip=10.0.0.1",
    )

    assert tests[0].expected_fields == {
        "source_ip": "10.0.0.1",
        "timestamp": "2026-09-11T10:00:00Z",
    }