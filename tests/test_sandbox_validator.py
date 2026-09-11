from backend.core.parser_sandbox import ParserSandbox
from backend.core.sandbox_validator import SandboxValidator
from backend.models.parser_definition import ParserDefinition


def test_validator_accepts_expected_fields():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "user": "user",
            "src": "source.ip",
            "result": "event.action",
        },
    )

    validator = SandboxValidator()

    result = validator.validate(
        definition=definition,
        raw_log="user=admin src=10.0.0.5 result=failed",
        expected_fields=[
            "user",
            "source.ip",
            "event.action",
        ],
    )

    assert result.success is True
    assert result.safe is True
    assert result.errors == []


def test_validator_detects_missing_field():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "user": "user",
            "src": "source.ip",
        },
    )

    validator = SandboxValidator()

    result = validator.validate(
        definition=definition,
        raw_log="user=admin src=10.0.0.5",
        expected_fields=[
            "user",
            "source.ip",
            "event.action",
        ],
    )

    assert result.success is False
    assert result.safe is True
    assert "Missing expected field: event.action" in result.errors


def test_validator_preserves_sandbox_failure():
    definition = ParserDefinition(
        parser_name="json_device",
        format_type="json",
    )

    validator = SandboxValidator()

    result = validator.validate(
        definition=definition,
        raw_log='{"invalid"',
        expected_fields=[],
    )

    assert result.success is False
    assert result.safe is True
    assert len(result.errors) == 1


def test_validator_accepts_custom_sandbox():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
    )

    sandbox = ParserSandbox()
    validator = SandboxValidator(sandbox=sandbox)

    result = validator.validate(
        definition=definition,
        raw_log="user=admin",
        expected_fields=[],
    )

    assert result.success is True
    assert result.safe is True