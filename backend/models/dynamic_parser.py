"""Models for dynamically registered parsers."""

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class DynamicParserRecord(BaseModel):
    """Metadata for a dynamically registered parser."""

    parser_name: str
    version: str = "generated-1.0"
    vendor: str | None = None
    product: str | None = None
    source: str = "local_ai"

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    approved_by: str
    approved_at: datetime

    active: bool = True

    registered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )