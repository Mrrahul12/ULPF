"""Request model for dynamic parser registration."""

from backend.models.parser_approval import ParserApproval
from backend.models.parser_definition import ParserDefinition
from pydantic import BaseModel, Field


class DynamicParserRegistrationRequest(BaseModel):
    definition: ParserDefinition
    approval: ParserApproval

    vendor: str | None = None
    product: str | None = None

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    source: str = "local_ai"