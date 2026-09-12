"""Air-gapped end-to-end tests for the complete ULPF parser lifecycle."""

import socket

import pytest

from backend.core.approval_service import ApprovalService
from backend.core.dynamic_registry import DynamicRegistryService
from backend.core.local_ai_mock import DeterministicLocalAI
from backend.core.parser_factory import generate_parser_proposal
from backend.core.parser_sandbox import ParserSandbox
from backend.core.parser_test_generator import ParserTestGenerator
from backend.core.parser_test_runner import ParserTestRunner
from backend.core.unknown_log_intelligence import analyze_unknown_log
from backend.models.parser_approval import ParserApproval
from backend.models.parser_definition import ParserDefinition
from backend.parsers.registry import ParserRegistry


UNKNOWN_VENDOR_LOG = (
    'timestamp="2026-09-12T10:15:30Z" '
    'src=192.168.10.20 '
    'dst=10.0.0.15 '
    'user=admin '
    'result=blocked'
)


def test_complete_parser_lifecycle_works_air_gapped(monkeypatch):
    """The complete parser lifecycle must work without network access."""

    def blocked_network_call(*args, **kwargs):
        raise AssertionError(
            "Network access attempted during air-gapped ULPF processing"
        )

    monkeypatch.setattr(
        socket,
        "create_connection",
        blocked_network_call,
    )

    monkeypatch.setattr(
        socket.socket,
        "connect",
        blocked_network_call,
    )

    # 1. Unknown log intelligence
    analysis = analyze_unknown_log(UNKNOWN_VENDOR_LOG)

    assert analysis.format_type == "key_value"
    assert analysis.timestamp_detected is True
    assert "src" in analysis.key_value_fields
    assert "dst" in analysis.key_value_fields

    # 2. Local AI parser proposal
    local_ai = DeterministicLocalAI()

    proposal = generate_parser_proposal(
        raw_log=UNKNOWN_VENDOR_LOG,
        adapter=local_ai,
    )

    assert proposal.source == "local_ai"
    assert proposal.format_type == "key_value"
    assert proposal.parser_name

    # 3. Convert proposal to safe declarative definition
    definition = ParserDefinition(
        parser_name=proposal.parser_name,
        format_type=proposal.format_type,
        mappings=proposal.mappings,
        timestamp_field=proposal.timestamp_field,
    )

    # 4. Sandbox validation
    sandbox = ParserSandbox()

    sandbox_result = sandbox.run(
        definition=definition,
        raw_log=UNKNOWN_VENDOR_LOG,
    )

    assert sandbox_result.success is True
    assert sandbox_result.safe is True

    # 5. Automated parser tests
    generator = ParserTestGenerator()

    test_cases = generator.generate(
        definition=definition,
        raw_log=UNKNOWN_VENDOR_LOG,
    )

    runner = ParserTestRunner()

    test_results = runner.run(
        definition=definition,
        test_cases=test_cases,
    )

    assert test_results
    assert all(result["passed"] for result in test_results)

    # 6. Human approval
    approval = ParserApproval(
        parser_name=definition.parser_name,
    )

    approval_service = ApprovalService()

    approval = approval_service.approve(
        approval=approval,
        reviewer="air_gapped_security_admin",
        comment="Approved during offline validation",
    )

    assert approval.status.value == "approved"
    assert approval.reviewer == "air_gapped_security_admin"
    assert approval.reviewed_at is not None

    # 7. Dynamic registration
    registry = ParserRegistry()

    dynamic_registry = DynamicRegistryService(
        registry=registry,
    )

    record = dynamic_registry.register(
        definition=definition,
        approval=approval,
        vendor=proposal.vendor,
        product=proposal.product,
        confidence=proposal.confidence,
        source=proposal.source,
    )

    assert record.active is True
    assert record.parser_name == definition.parser_name

    # 8. Retrieve dynamically registered parser
    parser = dynamic_registry.get_parser(
        definition.parser_name,
    )

    assert parser is not None

    # 9. Parse the same unknown-vendor log
    success, parsed, error = parser.parse(
        UNKNOWN_VENDOR_LOG,
    )

    assert success is True
    assert error == ""

    # 10. Normalize the event
    normalized, unmapped = parser.normalize(parsed)

    assert normalized["source.ip"] == "192.168.10.20"
    assert normalized["destination.ip"] == "10.0.0.15"
    assert normalized["user"] == "admin"
    assert normalized["event.action"] == "blocked"


def test_air_gapped_flow_does_not_require_external_ai():
    """The parser factory must work using only the local deterministic provider."""

    local_ai = DeterministicLocalAI()

    proposal = generate_parser_proposal(
        raw_log=UNKNOWN_VENDOR_LOG,
        adapter=local_ai,
    )

    assert proposal.source == "local_ai"
    assert proposal.parser_name
    assert proposal.mappings


def test_air_gapped_unknown_log_analysis_is_deterministic():
    """Unknown-log analysis must produce the same result repeatedly."""

    first = analyze_unknown_log(UNKNOWN_VENDOR_LOG)
    second = analyze_unknown_log(UNKNOWN_VENDOR_LOG)

    assert first.model_dump() == second.model_dump()