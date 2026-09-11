"""Service for enforcing human parser approval decisions."""

from datetime import datetime, timezone

from backend.models.parser_approval import (
    ApprovalStatus,
    ParserApproval,
)


class ApprovalService:
    """Manage human approval decisions for parser proposals."""

    def approve(
        self,
        approval: ParserApproval,
        reviewer: str,
        comment: str = "",
    ) -> ParserApproval:
        self._validate_reviewer(reviewer)

        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Cannot approve parser in {approval.status.value} state"
            )

        approval.status = ApprovalStatus.APPROVED
        approval.reviewer = reviewer
        approval.comment = comment
        approval.reviewed_at = datetime.now(timezone.utc)

        return approval

    def reject(
        self,
        approval: ParserApproval,
        reviewer: str,
        comment: str = "",
    ) -> ParserApproval:
        self._validate_reviewer(reviewer)

        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Cannot reject parser in {approval.status.value} state"
            )

        approval.status = ApprovalStatus.REJECTED
        approval.reviewer = reviewer
        approval.comment = comment
        approval.reviewed_at = datetime.now(timezone.utc)

        return approval

    @staticmethod
    def _validate_reviewer(reviewer: str) -> None:
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError("reviewer is required")