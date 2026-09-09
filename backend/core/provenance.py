"""Provenance construction for processed events."""

from backend.config import DEFAULT_CONFIDENCE, MAPPING_VERSION, PARSER_VERSIONS
from backend.models.event import ProvenanceInfo


def build_provenance(parser_name: str, parser_version: str | None = None) -> ProvenanceInfo:
    """Create consistent provenance metadata for a deterministic parser."""
    return ProvenanceInfo(
        parser=parser_name,
        parser_version=parser_version or PARSER_VERSIONS.get(parser_name, "1.0"),
        mapping_version=MAPPING_VERSION,
        confidence=DEFAULT_CONFIDENCE,
    )
