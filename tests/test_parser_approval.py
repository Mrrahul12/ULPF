from datetime import datetime, timezone

from backend.models.parser_approval import (
    ApprovalStatus,
    ParserApproval,
)


def test_parser_approval_defaults_to_pending():
    approval = ParserApproval(
        parser_name="device_parser",
    )

    assert approval.parser_name == "device_parser"
    assert approval.status == ApprovalStatus.PENDING
    assert approval.reviewer is None
    assert approval.comment == ""
    assert approval.reviewed_at is None
    assert approval.created_at.tzinfo is not None


def test_parser_approval_can_be_approved():
    approval = ParserApproval(
        parser_name="device_parser",
        status=ApprovalStatus.APPROVED,
        reviewer="security_admin",
        comment="Parser passed validation.",
        reviewed_at=datetime.now(timezone.utc),
    )

    assert approval.status == ApprovalStatus.APPROVED
    assert approval.reviewer == "security_admin"
    assert approval.comment == "Parser passed validation."
    assert approval.reviewed_at is not None


def test_parser_approval_can_be_rejected():
    approval = ParserApproval(
        parser_name="device_parser",
        status=ApprovalStatus.REJECTED,
        reviewer="security_admin",
        comment="Incorrect field mapping.",
        reviewed_at=datetime.now(timezone.utc),
    )

    assert approval.status == ApprovalStatus.REJECTED
    assert approval.reviewer == "security_admin"
    assert approval.comment == "Incorrect field mapping."