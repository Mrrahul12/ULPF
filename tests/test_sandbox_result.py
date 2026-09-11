import pytest
from pydantic import ValidationError

from backend.models.sandbox_result import SandboxResult


def test_sandbox_result_minimal():
    result = SandboxResult(
        parser_name="device_x",
        format_type="key_value",
    )

    assert result.success is False
    assert result.safe is False
    assert result.parser_name == "device_x"
    assert result.format_type == "key_value"
    assert result.parsed_fields == {}
    assert result.errors == []
    assert result.warnings == []
    assert result.execution_time_ms == 0.0


def test_sandbox_result_success():
    result = SandboxResult(
        success=True,
        safe=True,
        parser_name="device_x",
        format_type="key_value",
        parsed_fields={
            "user": "admin",
            "source.ip": "10.0.0.5",
        },
        execution_time_ms=2.5,
    )

    assert result.success is True
    assert result.safe is True
    assert result.parsed_fields["user"] == "admin"
    assert result.execution_time_ms == 2.5


def test_sandbox_result_rejects_negative_execution_time():
    with pytest.raises(ValidationError):
        SandboxResult(
            parser_name="device_x",
            format_type="key_value",
            execution_time_ms=-1.0,
        )


def test_sandbox_result_serializes():
    result = SandboxResult(
        success=True,
        safe=True,
        parser_name="device_x",
        format_type="json",
    )

    data = result.model_dump()

    assert data["success"] is True
    assert data["safe"] is True
    assert data["parser_name"] == "device_x"