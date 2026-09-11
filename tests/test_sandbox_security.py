import pytest

from backend.core.sandbox_security import (
    SandboxSecurityError,
    validate_parser_security,
)
from backend.models.parser_definition import ParserDefinition


def test_safe_parser_definition_is_allowed():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "user": "user",
            "src": "source.ip",
        },
    )

    result = validate_parser_security(definition)

    assert result is definition


def test_python_import_is_blocked():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "__import__('os')": "event.message",
        },
    )

    with pytest.raises(SandboxSecurityError):
        validate_parser_security(definition)


def test_exec_is_blocked():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "exec": "event.message",
        },
    )

    with pytest.raises(SandboxSecurityError):
        validate_parser_security(definition)


def test_file_access_is_blocked():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "open": "event.message",
        },
    )

    with pytest.raises(SandboxSecurityError):
        validate_parser_security(definition)


def test_subprocess_is_blocked():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "subprocess": "event.message",
        },
    )

    with pytest.raises(SandboxSecurityError):
        validate_parser_security(definition)


def test_network_access_is_blocked():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "requests": "event.message",
        },
    )

    with pytest.raises(SandboxSecurityError):
        validate_parser_security(definition)