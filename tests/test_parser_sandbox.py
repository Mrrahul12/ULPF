from backend.core.parser_sandbox import ParserSandbox
from backend.models.parser_definition import ParserDefinition


def test_sandbox_parses_key_value_log():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "user": "user",
            "src": "source.ip",
            "result": "event.action",
        },
    )

    sandbox = ParserSandbox()

    result = sandbox.run(
        definition,
        "user=admin src=10.0.0.5 result=failed",
    )

    assert result.success is True
    assert result.safe is True
    assert result.parsed_fields["user"] == "admin"
    assert result.parsed_fields["source.ip"] == "10.0.0.5"
    assert result.parsed_fields["event.action"] == "failed"
    assert result.execution_time_ms >= 0


def test_sandbox_supports_json():
    definition = ParserDefinition(
        parser_name="json_device",
        format_type="json",
        mappings={
            "user": "user",
            "src": "source.ip",
        },
    )

    sandbox = ParserSandbox()

    result = sandbox.run(
        definition,
        '{"user": "admin", "src": "10.0.0.5"}',
    )

    assert result.success is True
    assert result.parsed_fields["user"] == "admin"
    assert result.parsed_fields["source.ip"] == "10.0.0.5"


def test_sandbox_supports_plain_text():
    definition = ParserDefinition(
        parser_name="text_device",
        format_type="plain_text",
        mappings={
            "message": "event.message",
        },
    )

    sandbox = ParserSandbox()

    result = sandbox.run(
        definition,
        "authentication failure",
    )

    assert result.success is True
    assert result.parsed_fields["event.message"] == (
        "authentication failure"
    )


def test_sandbox_rejects_invalid_json():
    definition = ParserDefinition(
        parser_name="json_device",
        format_type="json",
    )

    sandbox = ParserSandbox()

    result = sandbox.run(
        definition,
        '{"invalid"',
    )

    assert result.success is False
    assert result.safe is True
    assert len(result.errors) == 1


def test_sandbox_rejects_empty_log():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
    )

    sandbox = ParserSandbox()

    result = sandbox.run(
        definition,
        "",
    )

    assert result.success is False
    assert result.safe is True
    assert "non-empty string" in result.errors[0]


def test_sandbox_does_not_execute_python_code():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="plain_text",
        mappings={
            "__import__('os').system('whoami')": "message",
        },
    )

    sandbox = ParserSandbox()

    result = sandbox.run(
        definition,
        "authentication failure",
    )

    assert result.success is False
    assert result.safe is False
    assert result.parsed_fields == {}
    assert result.errors
    assert "blocked token" in result.errors[0].lower()

def test_sandbox_rejects_unsafe_definition():
    definition = ParserDefinition(
        parser_name="unsafe_parser",
        format_type="key_value",
        mappings={
            "__import__('os').system('whoami')": "message"
        },
    )

    result = ParserSandbox().run(
        definition,
        "message=test",
    )

    assert result.success is False
    assert result.safe is False
    assert result.errors
    assert "blocked token" in result.errors[0].lower()


def test_sandbox_allows_safe_definition():
    definition = ParserDefinition(
        parser_name="safe_parser",
        format_type="key_value",
        mappings={
            "src_ip": "source_ip",
        },
    )

    result = ParserSandbox().run(
        definition,
        "src_ip=10.0.0.1",
    )

    assert result.success is True
    assert result.safe is True
    assert result.parsed_fields["source_ip"] == "10.0.0.1"