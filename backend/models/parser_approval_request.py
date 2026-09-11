"""Request model for human parser approval decisions."""

from pydantic import BaseModel


class ParserApprovalRequest(BaseModel):
    """Request containing reviewer information and optional comment."""

    parser_name: str
    reviewer: str
    comment: str = ""