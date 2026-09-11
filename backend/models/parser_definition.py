"""Safe declarative parser definitions."""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ParserDefinition(BaseModel):
    """
    Declarative parser definition used by the sandbox.

    This contains parser configuration only.
    It does not contain executable Python code.
    """

    parser_name: str

    format_type: str

    mappings: Dict[str, str] = Field(
        default_factory=dict,
    )

    timestamp_field: Optional[str] = None