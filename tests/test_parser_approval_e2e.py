from backend.core.approval_service import ApprovalService
from backend.core.parser_factory import generate_parser_proposal
from backend.core.parser_test_generator import ParserTestGenerator
from backend.core.parser_test_runner import ParserTestRunner
from backend.core.parser_sandbox import ParserSandbox
from backend.models.parser_approval import ApprovalStatus, ParserApproval
from backend.models.parser_definition import ParserDefinition
from backend.parsers.declarative import DeclarativeParser
from backend.parsers.registry import ParserRegistry
from backend.core.local_ai_mock import DeterministicLocalAI


def build_definition_from_proposal(proposal):
    return ParserDefinition(
        parser_name=proposal.parser_name,
        format_type=proposal.format_type,
        mappings=proposal.mappings,
        timestamp_field=proposal.timestamp_field,
    )


def test_approved_parser_completes_full_registration_flow():
    raw_log = (
        "date=2026-09-11 time=12:30:00 "
        "devname=UNKNOWN-FW srcip=10.0.0.5 "
        "dstip=192.168.1.10 action=deny"
    )

    # 1. AI generates a parser proposal
    proposal = generate_parser_proposal(
        raw_log=raw_log,
        adapter=DeterministicLocalAI(),
    )

    assert proposal.parser_name
    assert proposal.format_type

    # 2. Convert proposal into safe declarative definition
    definition = build_definition_from_proposal(proposal)

    # 3. Sandbox validation
    sandbox = ParserSandbox()
    sandbox_result = sandbox.run(
        definition=definition,
        raw_log=raw_log,
    )

    assert sandbox_result.success is True
    assert sandbox_result.safe is True

    # 4. Automated parser tests
    generator = ParserTestGenerator()
    test_cases = generator.generate(
        definition=definition,
        raw_log=raw_log,
    )

    runner = ParserTestRunner()
    results = runner.run(
        definition=definition,
        test_cases=test_cases,
    )

    assert len(results) > 0
    assert all(result["passed"] for result in results)

    # 5. Create pending human approval
    approval = ParserApproval(
        parser_name=definition.parser_name,
    )

    assert approval.status == ApprovalStatus.PENDING

    # 6. Human approves
    service = ApprovalService()

    approved = service.approve(
        approval=approval,
        reviewer="security_admin",
        comment="Approved after sandbox and automated validation.",
    )

    assert approved.status == ApprovalStatus.APPROVED
    assert approved.reviewer == "security_admin"
    assert approved.reviewed_at is not None

    # 7. Convert safe declarative definition to BaseParser
    parser = DeclarativeParser(definition)

    # 8. Approval-gated registry registration
    registry = ParserRegistry()

    registry.register_approved(
        parser=parser,
        approval=approved,
    )

    # 9. Verify parser is now available
    registered = registry.get_parser(definition.parser_name)

    assert registered is parser
    assert definition.parser_name in registry


def test_rejected_parser_never_reaches_registry():
    raw_log = (
        "date=2026-09-11 time=12:30:00 "
        "devname=UNKNOWN-FW srcip=10.0.0.5 "
        "dstip=192.168.1.10 action=deny"
    )

    # AI proposal
    proposal = generate_parser_proposal(
        raw_log=raw_log,
        adapter=DeterministicLocalAI(),
    )

    definition = build_definition_from_proposal(proposal)

    # Sandbox must still be safe
    sandbox_result = ParserSandbox().run(
        definition=definition,
        raw_log=raw_log,
    )

    assert sandbox_result.success is True
    assert sandbox_result.safe is True

    # Human rejects
    approval = ParserApproval(
        parser_name=definition.parser_name,
    )

    service = ApprovalService()

    rejected = service.reject(
        approval=approval,
        reviewer="security_admin",
        comment="Rejected because field mapping requires review.",
    )

    assert rejected.status == ApprovalStatus.REJECTED

    # Create parser object
    parser = DeclarativeParser(definition)

    # Registry must block it
    registry = ParserRegistry()

    try:
        registry.register_approved(
            parser=parser,
            approval=rejected,
        )
        registered = True
    except ValueError:
        registered = False

    assert registered is False
    assert registry.get_parser(definition.parser_name) is None