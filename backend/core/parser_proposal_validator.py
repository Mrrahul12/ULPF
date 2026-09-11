"""Validation helpers for parser proposals."""

import re

from backend.models.parser_proposal import ParserProposal


class ParserProposalValidationError(ValueError):
    """Raised when a parser proposal violates safety rules."""


_VALID_NAME_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{2,63}$"
)

_ALLOWED_FORMATS = {
    "json",
    "key_value",
    "plain_text",
    "unknown",
}


def validate_parser_proposal(
    proposal: ParserProposal,
) -> ParserProposal:
    """
    Validate a parser proposal before it is used downstream.

    Validation is intentionally strict because the proposal may
    originate from an AI-generated response.
    """

    if not isinstance(proposal, ParserProposal):
        raise ParserProposalValidationError(
            "proposal must be a ParserProposal"
        )

    if not _VALID_NAME_PATTERN.fullmatch(proposal.parser_name):
        raise ParserProposalValidationError(
            "invalid parser_name"
        )

    if proposal.format_type not in _ALLOWED_FORMATS:
        raise ParserProposalValidationError(
            f"unsupported format_type: {proposal.format_type}"
        )

    for source_field, canonical_field in proposal.mappings.items():
        if not source_field.strip():
            raise ParserProposalValidationError(
                "mapping source field cannot be empty"
            )

        if not canonical_field.strip():
            raise ParserProposalValidationError(
                "mapping canonical field cannot be empty"
            )

    if not 0.0 <= proposal.confidence <= 1.0:
        raise ParserProposalValidationError(
            "confidence must be between 0 and 1"
        )

    return proposal