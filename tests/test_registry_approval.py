import pytest

from backend.models.parser_approval import ApprovalStatus, ParserApproval
from backend.parsers.base import BaseParser
from backend.parsers.registry import ParserRegistry


class ApprovedMockParser(BaseParser):
    def detect(self, log: str) -> bool:
        return True

    def parse(self, log: str):
        return True, {"message": log}, ""

    def normalize(self, parsed):
        return parsed, {}


def make_approved_parser():
    approval = ParserApproval(
        parser_name="generated_parser",
        status=ApprovalStatus.APPROVED,
        reviewer="security_admin",
    )
    approval.reviewed_at = approval.created_at
    return approval


def test_approved_parser_can_be_registered():
    registry = ParserRegistry()
    parser = ApprovedMockParser("generated_parser")
    approval = make_approved_parser()

    registry.register_approved(parser, approval)

    assert registry.get_parser("generated_parser") == parser


def test_pending_parser_cannot_be_registered():
    registry = ParserRegistry()
    parser = ApprovedMockParser("generated_parser")

    approval = ParserApproval(
        parser_name="generated_parser",
        status=ApprovalStatus.PENDING,
    )

    with pytest.raises(ValueError, match="without human approval"):
        registry.register_approved(parser, approval)

    assert registry.get_parser("generated_parser") is None


def test_rejected_parser_cannot_be_registered():
    registry = ParserRegistry()
    parser = ApprovedMockParser("generated_parser")

    approval = ParserApproval(
        parser_name="generated_parser",
        status=ApprovalStatus.REJECTED,
        reviewer="security_admin",
    )

    with pytest.raises(ValueError, match="without human approval"):
        registry.register_approved(parser, approval)

    assert registry.get_parser("generated_parser") is None


def test_approved_parser_requires_reviewer():
    registry = ParserRegistry()
    parser = ApprovedMockParser("generated_parser")

    approval = ParserApproval(
        parser_name="generated_parser",
        status=ApprovalStatus.APPROVED,
    )

    with pytest.raises(ValueError, match="reviewer"):
        registry.register_approved(parser, approval)


def test_approved_parser_requires_review_timestamp():
    registry = ParserRegistry()
    parser = ApprovedMockParser("generated_parser")

    approval = ParserApproval(
        parser_name="generated_parser",
        status=ApprovalStatus.APPROVED,
        reviewer="security_admin",
    )

    with pytest.raises(ValueError, match="reviewed_at"):
        registry.register_approved(parser, approval)


def test_invalid_parser_type_is_rejected():
    registry = ParserRegistry()
    approval = make_approved_parser()

    with pytest.raises(TypeError, match="BaseParser"):
        registry.register_approved("not-a-parser", approval)


def test_invalid_approval_type_is_rejected():
    registry = ParserRegistry()
    parser = ApprovedMockParser("generated_parser")

    with pytest.raises(TypeError, match="ParserApproval"):
        registry.register_approved(parser, "not-an-approval")