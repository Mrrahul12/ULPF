"""Models for parser sandbox validation results."""

from typing import Dict, List

from pydantic import BaseModel, Field


class SandboxResult(BaseModel):
    """
    Result of testing a parser proposal inside the sandbox.

    This model records validation results only.
    It does not activate or register a parser.
    """

    success: bool = False

    safe: bool = False

    parser_name: str

    format_type: str

    parsed_fields: Dict[str, object] = Field(
        default_factory=dict,
    )

    errors: List[str] = Field(
        default_factory=list,
    )

    warnings: List[str] = Field(
        default_factory=list,
    )

    execution_time_ms: float = Field(
        default=0.0,
        ge=0.0,
    )