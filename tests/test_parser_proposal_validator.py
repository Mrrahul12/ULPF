import pytest

from backend.core.parser_proposal_validator import (
    ParserProposalValidationError,
    validate_parser_proposal,
)
from backend.models.parser_proposal import ParserProposal


def test_valid_parser_proposal():
    proposal = ParserProposal(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "user": "user",
            "src": "source.ip",
        },
        confidence=0.85,
    )

    result = validate_parser_proposal(proposal)

    assert result is proposal


def test_invalid_parser_name_is_rejected():
    proposal = ParserProposal(
        parser_name="Device-X",
        format_type="key_value",
    )

    with pytest.raises(ParserProposalValidationError):
        validate_parser_proposal(proposal)


def test_short_parser_name_is_rejected():
    proposal = ParserProposal(
        parser_name="ab",
        format_type="key_value",
    )

    with pytest.raises(ParserProposalValidationError):
        validate_parser_proposal(proposal)


def test_invalid_format_is_rejected():
    proposal = ParserProposal(
        parser_name="device_x",
        format_type="javascript",
    )

    with pytest.raises(ParserProposalValidationError):
        validate_parser_proposal(proposal)


def test_empty_mapping_source_is_rejected():
    proposal = ParserProposal(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "": "source.ip",
        },
    )

    with pytest.raises(ParserProposalValidationError):
        validate_parser_proposal(proposal)


def test_empty_mapping_target_is_rejected():
    proposal = ParserProposal(
        parser_name="device_x",
        format_type="key_value",
        mappings={
            "src": "",
        },
    )

    with pytest.raises(ParserProposalValidationError):
        validate_parser_proposal(proposal)