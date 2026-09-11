"""Models for automatically generated parser test cases."""

from typing import Dict

from pydantic import BaseModel, Field


class ParserTestCase(BaseModel):
    """One deterministic test case for a parser definition."""

    name: str
    raw_log: str
    expected_fields: Dict[str, object] = Field(default_factory=dict)
    description: str = ""