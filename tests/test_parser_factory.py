from backend.core.local_ai_mock import DeterministicLocalAI
from backend.core.parser_factory import (
    build_parser_evidence,
    generate_parser_proposal,
)


def test_build_parser_evidence():
    raw_log = (
        "2026-09-11T10:30:22Z "
        "DEVICE_X login "
        "user=admin src=10.0.0.5 result=failed"
    )

    evidence = build_parser_evidence(raw_log)

    assert evidence["is_unknown"] is True
    assert evidence["format_type"] == "key_value"
    assert evidence["timestamp_detected"] is True
    assert "user" in evidence["key_value_fields"]
    assert "src" in evidence["key_value_fields"]
    assert "10.0.0.5" in evidence["ip_addresses"]


def test_generate_parser_proposal_from_evidence():
    raw_log = (
        "2026-09-11T10:30:22Z "
        "DEVICE_X login "
        "user=admin src=10.0.0.5 result=failed"
    )

    adapter = DeterministicLocalAI()

    proposal = generate_parser_proposal(
        raw_log=raw_log,
        adapter=adapter,
    )

    assert proposal.parser_name == "unknown_device"
    assert proposal.format_type == "key_value"
    assert proposal.timestamp_field == "timestamp"
    assert proposal.mappings["user"] == "user"
    assert proposal.mappings["src"] == "source.ip"
    assert proposal.mappings["result"] == "event.action"


def test_factory_does_not_register_parser():
    raw_log = "DEVICE_X user=admin src=10.0.0.5"

    adapter = DeterministicLocalAI()

    proposal = generate_parser_proposal(
        raw_log=raw_log,
        adapter=adapter,
    )

    # Proposal generation must only suggest a parser.
    # It must not modify the parser registry.
    assert proposal.parser_name == "unknown_device"