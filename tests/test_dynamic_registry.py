from backend.parsers.registry import reset_registry
from datetime import datetime, timezone

import pytest

from backend.core.approval_service import ApprovalService
from backend.core.dynamic_registry import DynamicRegistryService
from backend.core.parser_sandbox import ParserSandbox
from backend.core.parser_test_generator import ParserTestGenerator
from backend.core.parser_test_runner import ParserTestRunner
from backend.models.parser_approval import ParserApproval
from backend.models.parser_definition import ParserDefinition

def setup_function():
    reset_registry()
    
def build_approved_parser():
    raw_log = 'timestamp="2026-09-11T10:00:00Z" action=login src_ip=10.0.0.5'

    definition = ParserDefinition(
        parser_name="dynamic_vendor_parser",
        format_type="key_value",
        mappings={
            "action": "event_type",
            "src_ip": "source_ip",
        },
        timestamp_field="timestamp",
    )

    sandbox_result = ParserSandbox().run(
        definition=definition,
        raw_log=raw_log,
    )

    assert sandbox_result.success
    assert sandbox_result.safe

    test_cases = ParserTestGenerator().generate(
        definition=definition,
        raw_log=raw_log,
    )

    results = ParserTestRunner().run(
        definition=definition,
        test_cases=test_cases,
    )

    assert all(result["passed"] for result in results)

    approval = ParserApproval(
        parser_name=definition.parser_name,
    )

    approval = ApprovalService().approve(
        approval=approval,
        reviewer="security_admin",
        comment="Approved after sandbox validation",
    )

    return definition, approval


def test_register_approved_parser():
    definition, approval = build_approved_parser()

    service = DynamicRegistryService()

    record = service.register(
        definition=definition,
        approval=approval,
        vendor="ExampleVendor",
        product="ExampleFirewall",
        confidence=0.95,
    )

    assert record.parser_name == "dynamic_vendor_parser"
    assert record.vendor == "ExampleVendor"
    assert record.product == "ExampleFirewall"
    assert record.confidence == 0.95
    assert record.approved_by == "security_admin"
    assert record.active is True

    assert service.get("dynamic_vendor_parser") is not None
    assert len(service.list_active()) == 1


def test_pending_approval_is_blocked():
    definition = ParserDefinition(
        parser_name="blocked_dynamic_parser",
        format_type="plain_text",
        mappings={"message": "message"},
    )

    approval = ParserApproval(
        parser_name=definition.parser_name,
    )

    service = DynamicRegistryService()

    with pytest.raises(ValueError, match="human approval"):
        service.register(
            definition=definition,
            approval=approval,
        )


def test_rejected_approval_is_blocked():
    definition = ParserDefinition(
        parser_name="rejected_dynamic_parser",
        format_type="plain_text",
        mappings={"message": "message"},
    )

    approval = ParserApproval(
        parser_name=definition.parser_name,
        status="rejected",
        reviewer="security_admin",
        reviewed_at=datetime.now(timezone.utc),
    )

    service = DynamicRegistryService()

    with pytest.raises(ValueError, match="human approval"):
        service.register(
            definition=definition,
            approval=approval,
        )


def test_deactivate_dynamic_parser():
    definition, approval = build_approved_parser()

    service = DynamicRegistryService()

    service.register(
        definition=definition,
        approval=approval,
    )

    result = service.deactivate("dynamic_vendor_parser")

    assert result.active is False
    assert service.list_active() == []
    assert service.get("dynamic_vendor_parser").active is False


def test_deactivate_unknown_parser():
    service = DynamicRegistryService()

    with pytest.raises(
        KeyError,
        match="Dynamic parser not found",
    ):
        service.deactivate("does_not_exist")

def test_get_active_parser():
    definition, approval = build_approved_parser()

    service = DynamicRegistryService()

    service.register(
        definition=definition,
        approval=approval,
    )

    parser = service.get_parser("dynamic_vendor_parser")

    assert parser is not None
    assert parser.name == "dynamic_vendor_parser"


def test_get_inactive_parser_returns_none():
    definition, approval = build_approved_parser()

    service = DynamicRegistryService()

    service.register(
        definition=definition,
        approval=approval,
    )

    service.deactivate("dynamic_vendor_parser")

    assert service.get_parser("dynamic_vendor_parser") is None


def test_list_parsers():
    definition, approval = build_approved_parser()

    service = DynamicRegistryService()

    service.register(
        definition=definition,
        approval=approval,
    )

    assert service.list_parsers() == [
        "dynamic_vendor_parser"
    ]
