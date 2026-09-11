"""Models for human approval of parser proposals."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    """Possible human approval states."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ParserApproval(BaseModel):
    """Record of a human decision for a parser proposal."""

    parser_name: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer: str | None = None
    comment: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: datetime | None = None