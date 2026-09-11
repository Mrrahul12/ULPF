"""Parser factory helpers for converting unknown-log evidence into proposals."""

from backend.models.parser_proposal import ParserProposal
from backend.core.local_ai import LocalAIAdapter
from backend.core.unknown_log_intelligence import analyze_unknown_log


def build_parser_evidence(raw_log: str) -> dict:
    """Build structured evidence for the parser factory."""

    analysis = analyze_unknown_log(raw_log)

    return analysis.model_dump()


def generate_parser_proposal(
    raw_log: str,
    adapter: LocalAIAdapter,
) -> ParserProposal:
    """
    Generate a parser proposal from unknown-log evidence.

    The adapter receives structured evidence rather than directly
    inspecting or modifying the parser registry.
    """

    evidence = build_parser_evidence(raw_log)

    return adapter.generate_parser_proposal(
        raw_log=raw_log,
        evidence=evidence,
    )