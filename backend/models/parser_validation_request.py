"""Request model for parser validation."""

from pydantic import BaseModel

from backend.models.parser_definition import ParserDefinition


class ParserValidationRequest(BaseModel):
    """Parser definition and sample log for automated validation."""

    definition: ParserDefinition
    raw_log: str