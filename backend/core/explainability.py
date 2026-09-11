"""Human-readable explanations for ULPF field provenance."""

from typing import Any, Dict, List

from backend.models.event import FieldExplanation, ProvenanceInfo


def _format_confidence(confidence: float) -> str:
    """Convert a confidence score into a readable percentage."""
    return f"{confidence * 100:.0f}%"


def _build_explanation(
    field: str,
    value: Any,
    source_field: str | None,
    parser: str,
    parser_version: str,
    method: str,
    confidence: float,
) -> str:
    """Build a human-readable explanation for one canonical field."""

    confidence_text = _format_confidence(confidence)

    if method == "deterministic":
        if source_field:
            return (
                f"Field '{field}' was mapped deterministically "
                f"from source field '{source_field}' using parser "
                f"'{parser}' version {parser_version}. "
                f"Confidence: {confidence_text}."
            )

        return (
            f"Field '{field}' was mapped deterministically "
            f"by parser '{parser}' version {parser_version}. "
            f"Confidence: {confidence_text}."
        )

    if method == "inferred":
        if source_field:
            return (
                f"Field '{field}' was inferred from source field "
                f"'{source_field}' using parser '{parser}' "
                f"version {parser_version}. "
                f"Confidence: {confidence_text}."
            )

        return (
            f"Field '{field}' was inferred by parser '{parser}' "
            f"version {parser_version}. "
            f"Confidence: {confidence_text}."
        )

    if method == "ai":
        if source_field:
            return (
                f"Field '{field}' was mapped using AI from source "
                f"field '{source_field}' using parser '{parser}' "
                f"version {parser_version}. "
                f"Confidence: {confidence_text}."
            )

        return (
            f"Field '{field}' was mapped using AI by parser "
            f"'{parser}' version {parser_version}. "
            f"Confidence: {confidence_text}."
        )

    return (
        f"Field '{field}' was processed using method '{method}' "
        f"by parser '{parser}' version {parser_version}. "
        f"Confidence: {confidence_text}."
    )


def explain_field(
    provenance: ProvenanceInfo,
    field: str,
) -> FieldExplanation:
    """
    Explain how one canonical field was produced.

    Raises:
        KeyError: If the requested field has no provenance entry.
    """

    if field not in provenance.fields:
        raise KeyError(
            f"No provenance information available for field '{field}'"
        )

    field_provenance = provenance.fields[field]

    explanation = _build_explanation(
        field=field,
        value=field_provenance.value,
        source_field=field_provenance.source_field,
        parser=provenance.parser,
        parser_version=provenance.parser_version,
        method=field_provenance.method,
        confidence=field_provenance.confidence,
    )

    return FieldExplanation(
        field=field,
        value=field_provenance.value,
        source_field=field_provenance.source_field,
        parser=provenance.parser,
        parser_version=provenance.parser_version,
        method=field_provenance.method,
        confidence=field_provenance.confidence,
        explanation=explanation,
    )


def explain_event(
    provenance: ProvenanceInfo,
) -> List[FieldExplanation]:
    """
    Explain every canonical field with available provenance.
    """

    return [
        explain_field(provenance, field)
        for field in provenance.fields
    ]