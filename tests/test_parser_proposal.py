import pytest
from pydantic import ValidationError

from backend.models.parser_proposal import ParserProposal


def test_parser_proposal_minimal():
    proposal = ParserProposal(
        parser_name="device_x",
        format_type="key_value",
    )

    assert proposal.parser_name == "device_x"
    assert proposal.format_type == "key_value"
    assert proposal.confidence == 0.0
    assert proposal.source == "local_ai"


def test_parser_proposal_with_mappings():
    proposal = ParserProposal(
        parser_name="device_x",
        vendor="DeviceX",
        product="SecureBox",
        format_type="key_value",
        mappings={
            "user": "user",
            "src": "source.ip",
            "result": "event.action",
        },
        timestamp_field="timestamp",
        confidence=0.82,
        reasoning=[
            "Key-value structure detected",
            "Source IP field detected",
        ],
    )

    assert proposal.vendor == "DeviceX"
    assert proposal.product == "SecureBox"
    assert proposal.mappings["src"] == "source.ip"
    assert proposal.timestamp_field == "timestamp"
    assert proposal.confidence == 0.82
    assert len(proposal.reasoning) == 2


def test_parser_proposal_rejects_confidence_above_one():
    with pytest.raises(ValidationError):
        ParserProposal(
            parser_name="device_x",
            format_type="key_value",
            confidence=1.5,
        )


def test_parser_proposal_rejects_negative_confidence():
    with pytest.raises(ValidationError):
        ParserProposal(
            parser_name="device_x",
            format_type="key_value",
            confidence=-0.1,
        )


def test_parser_proposal_serializes_to_dict():
    proposal = ParserProposal(
        parser_name="device_x",
        format_type="key_value",
        confidence=0.8,
    )

    data = proposal.model_dump()

    assert data["parser_name"] == "device_x"
    assert data["format_type"] == "key_value"
    assert data["confidence"] == 0.8
    assert data["source"] == "local_ai"