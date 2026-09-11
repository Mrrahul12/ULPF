from backend.models.parser_definition import ParserDefinition
from backend.core.approval_service import ApprovalService
from backend.core.dynamic_registry import DynamicRegistryService
from backend.core.local_ai_mock import DeterministicLocalAI
from backend.core.parser_factory import generate_parser_proposal
from backend.core.parser_sandbox import ParserSandbox
from backend.core.parser_test_generator import ParserTestGenerator
from backend.core.parser_test_runner import ParserTestRunner
from backend.models.parser_approval import ParserApproval

from backend.parsers.registry import get_registry, reset_registry


def build_definition_from_proposal(proposal):
    return ParserDefinition(
        parser_name=proposal.parser_name,
        format_type=proposal.format_type,
        mappings=proposal.mappings,
        timestamp_field=proposal.timestamp_field,
    )

def test_unknown_log_to_dynamic_parser_e2e():
    raw_log = (
        'timestamp="2026-09-11T10:00:00Z" '
        'action=login '
        'src_ip=10.0.0.5 '
        'status=success'
    )

    # 1. AI generates proposal
    proposal = generate_parser_proposal(
        raw_log=raw_log,
        adapter=DeterministicLocalAI(),
    )

    assert proposal.parser_name
    assert proposal.confidence > 0

    # 2. Convert proposal to safe definition
    definition = ParserDefinition(
        parser_name=proposal.parser_name,
        format_type=proposal.format_type,
        mappings=proposal.mappings,
        timestamp_field=proposal.timestamp_field,
    )

    # 3. Sandbox validation
    sandbox_result = ParserSandbox().run(
        definition=definition,
        raw_log=raw_log,
    )

    assert sandbox_result.success
    assert sandbox_result.safe

    # 4. Automated parser tests
    test_cases = ParserTestGenerator().generate(
        definition=definition,
        raw_log=raw_log,
    )

    results = ParserTestRunner().run(
        definition=definition,
        test_cases=test_cases,
    )

    assert results
    assert all(result["passed"] for result in results)

    # 5. Human approval
    approval = ParserApproval(
        parser_name=definition.parser_name,
    )

    approval = ApprovalService().approve(
        approval=approval,
        reviewer="security_admin",
        comment="Approved after automated validation",
    )

    assert approval.status.value == "approved"

    # 6. Dynamic registry
    registry = DynamicRegistryService()

    record = registry.register(
        definition=definition,
        approval=approval,
        vendor=proposal.vendor,
        product=proposal.product,
        confidence=proposal.confidence,
        source=proposal.source,
    )

    assert record.active is True

    # 7. Retrieve parser
    parser = registry.get_parser(definition.parser_name)

    assert parser is not None

    # 8. Parse the same unknown log
    success, parsed, error = parser.parse(raw_log)

    assert success is True
    assert error == ""

    assert parsed["action"] == "login"
    assert parsed["src_ip"] == "10.0.0.5"

def test_dynamic_parser_is_visible_in_global_registry():
    reset_registry()

    raw_log = (
        "timestamp=2026-09-11T10:00:00Z "
        "action=login "
        "src_ip=10.0.0.10"
    )

    proposal = generate_parser_proposal(
        raw_log=raw_log,
        adapter=DeterministicLocalAI(),
    )

    definition = build_definition_from_proposal(proposal)

    approval = ParserApproval(
        parser_name=definition.parser_name,
    )

    approval = ApprovalService().approve(
        approval=approval,
        reviewer="security_admin",
    )

    service = DynamicRegistryService(
        registry=get_registry(),
    )

    service.register(
        definition=definition,
        approval=approval,
        vendor=proposal.vendor,
        product=proposal.product,
        confidence=proposal.confidence,
        source=proposal.source,
    )

    global_registry = get_registry()

    parser = global_registry.get_parser(
        definition.parser_name
    )

    assert parser is not None
    assert parser.name == definition.parser_name

    success, parsed, error = parser.parse(raw_log)

    assert success is True
    assert error == ""
    assert parsed["action"] == "login"
    assert parsed["src_ip"] == "10.0.0.10"

    reset_registry()    