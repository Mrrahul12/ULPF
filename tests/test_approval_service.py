import pytest

from backend.core.approval_service import ApprovalService
from backend.models.parser_approval import (
    ApprovalStatus,
    ParserApproval,
)


def test_pending_parser_can_be_approved():
    service = ApprovalService()

    approval = ParserApproval(
        parser_name="device_parser",
    )

    result = service.approve(
        approval,
        reviewer="security_admin",
        comment="Validation passed.",
    )

    assert result.status == ApprovalStatus.APPROVED
    assert result.reviewer == "security_admin"
    assert result.comment == "Validation passed."
    assert result.reviewed_at is not None


def test_pending_parser_can_be_rejected():
    service = ApprovalService()

    approval = ParserApproval(
        parser_name="device_parser",
    )

    result = service.reject(
        approval,
        reviewer="security_admin",
        comment="Incorrect mapping.",
    )

    assert result.status == ApprovalStatus.REJECTED
    assert result.reviewer == "security_admin"
    assert result.comment == "Incorrect mapping."
    assert result.reviewed_at is not None


def test_rejected_parser_cannot_be_approved():
    service = ApprovalService()

    approval = ParserApproval(
        parser_name="device_parser",
        status=ApprovalStatus.REJECTED,
    )

    with pytest.raises(ValueError):
        service.approve(
            approval,
            reviewer="security_admin",
        )


def test_approved_parser_cannot_be_rejected():
    service = ApprovalService()

    approval = ParserApproval(
        parser_name="device_parser",
        status=ApprovalStatus.APPROVED,
    )

    with pytest.raises(ValueError):
        service.reject(
            approval,
            reviewer="security_admin",
        )


def test_reviewer_is_required():
    service = ApprovalService()

    approval = ParserApproval(
        parser_name="device_parser",
    )

    with pytest.raises(ValueError):
        service.approve(approval, reviewer="")