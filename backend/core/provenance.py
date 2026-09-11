"""Provenance construction for processed ULPF events."""

from typing import Any, Dict

from backend.config import DEFAULT_CONFIDENCE, MAPPING_VERSION, PARSER_VERSIONS
from backend.models.event import FieldProvenance, ProvenanceInfo


def _values_match(
    source_value: Any,
    normalized_value: Any,
) -> bool:
    """
    Determine whether a parser value corresponds to a normalized value.

    Handles common normalization transformations such as:
    - string -> integer
    - whitespace differences
    - protocol transformations such as TCP/HTTPS -> TCP
    """

    if source_value == normalized_value:
        return True

    # Handle numeric conversion.
    try:
        if str(source_value).strip() == str(normalized_value).strip():
            return True
    except Exception:
        pass

    # Handle protocol values such as:
    # TCP/HTTPS -> TCP
    if isinstance(source_value, str) and isinstance(normalized_value, str):
        source = source_value.strip().lower()
        normalized = normalized_value.strip().lower()

        if source.split("/")[0] == normalized:
            return True

    return False


def _find_source_field(
    canonical_field: str,
    normalized_value: Any,
    parsed_fields: Dict[str, Any],
) -> tuple[str | None, str]:
    """
    Find the original parser field responsible for a canonical field.

    Supports:
    - direct value matches
    - type conversions
    - known parser mappings
    - deterministic categorical mappings
    - inferred fields
    """

    # Direct/value-based deterministic mapping.
    for parsed_field, parsed_value in parsed_fields.items():
        if _values_match(parsed_value, normalized_value):
            return parsed_field, "deterministic"

    # Known deterministic mappings where the normalized value
    # is intentionally different from the parser value.
    deterministic_mappings = {
        "event.severity": {
            "severity": {
                "0": "emergency",
                "1": "alert",
                "2": "critical",
                "3": "error",
                "4": "warning",
                "5": "notice",
                "6": "info",
                "7": "debug",
            }
        },
    }

    field_mapping = deterministic_mappings.get(canonical_field, {})

    for source_field, value_mapping in field_mapping.items():
        if source_field in parsed_fields:
            source_value = str(parsed_fields[source_field])
            expected_value = value_mapping.get(source_value)

            if expected_value == normalized_value:
                return source_field, "deterministic"

    # Known inferred fields.
    inferred_sources = {
        "source.ip": {"message"},
        "destination.ip": {"message"},
    }

    if canonical_field in inferred_sources:
        for source_field in inferred_sources[canonical_field]:
            if source_field in parsed_fields:
                return source_field, "inferred"

    return None, "inferred"


def build_field_provenance(
    parsed_fields: Dict[str, Any],
    normalized_fields: Dict[str, Any],
) -> Dict[str, FieldProvenance]:
    """
    Build field-level provenance for normalized canonical fields.

    The original parser output is preserved and compared against the
    normalized values. This allows provenance to survive common
    transformations such as type conversion and protocol extraction.
    """

    provenance: Dict[str, FieldProvenance] = {}

    for canonical_field, normalized_value in normalized_fields.items():
        source_field, method = _find_source_field(
            canonical_field,
            normalized_value,
            parsed_fields,
        )

        provenance[canonical_field] = FieldProvenance(
            source_field=source_field,
            value=normalized_value,
            confidence=DEFAULT_CONFIDENCE,
            method=method,
        )

    return provenance


def build_provenance(
    parser_name: str,
    parser_version: str | None = None,
    fields: Dict[str, FieldProvenance] | None = None,
) -> ProvenanceInfo:
    """Create consistent event and field-level provenance metadata."""

    return ProvenanceInfo(
        parser=parser_name,
        parser_version=parser_version or PARSER_VERSIONS.get(parser_name, "1.0"),
        mapping_version=MAPPING_VERSION,
        confidence=DEFAULT_CONFIDENCE,
        fields=fields or {},
    )