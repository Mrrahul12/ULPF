import pytest
from pydantic import ValidationError

from backend.models.parser_definition import ParserDefinition


def test_parser_definition_minimal():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
    )

    assert definition.parser_name == "device_x"
    assert definition.format_type == "key_value"
    assert definition.mappings == {}
    assert definition.timestamp_field is None


def test_parser_definition_with_mappings():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "user": "user",
            "src": "source.ip",
            "result": "event.action",
        },
        timestamp_field="timestamp",
    )

    assert definition.mappings["src"] == "source.ip"
    assert definition.mappings["user"] == "user"
    assert definition.timestamp_field == "timestamp"


def test_parser_definition_serializes():
    definition = ParserDefinition(
        parser_name="device_x",
        format_type="json",
        mappings={
            "message": "event.message",
        },
    )

    data = definition.model_dump()

    assert data["parser_name"] == "device_x"
    assert data["format_type"] == "json"
    assert data["mappings"]["message"] == "event.message"


def test_parser_definition_rejects_missing_parser_name():
    with pytest.raises(ValidationError):
        ParserDefinition(
            format_type="json",
        )