"""Deterministic local provider for parser-factory development."""

from backend.core.local_ai import LocalAIAdapter
from backend.models.parser_proposal import ParserProposal


class DeterministicLocalAI(LocalAIAdapter):
    """
    Deterministic local AI implementation used for development and testing.

    It converts structural evidence into a predictable parser proposal.
    No external model or network connection is required.
    """

    def generate_parser_proposal(
        self,
        raw_log: str,
        evidence: dict,
    ) -> ParserProposal:
        """Generate a deterministic parser proposal from structural evidence."""

        format_type = evidence.get("format_type", "unknown")
        vendor_hints = evidence.get("vendor_hints", [])

        vendor = vendor_hints[0] if vendor_hints else None

        if vendor:
            parser_name = f"{vendor}_unknown"
        else:
            parser_name = "unknown_device"

        mappings = {}

        for field in evidence.get("key_value_fields", []):
            if field == "src":
                mappings[field] = "source.ip"
            elif field == "dst":
                mappings[field] = "destination.ip"
            elif field == "user":
                mappings[field] = "user"
            elif field == "result":
                mappings[field] = "event.action"

        timestamp_field = None

        if evidence.get("timestamp_detected"):
            timestamp_field = "timestamp"

        reasoning = [
            f"Detected format: {format_type}",
        ]

        if evidence.get("timestamp_detected"):
            reasoning.append("Timestamp structure detected")

        if evidence.get("key_value_fields"):
            reasoning.append(
                "Key-value fields detected: "
                + ", ".join(evidence["key_value_fields"])
            )

        if evidence.get("ip_addresses"):
            reasoning.append("IP address indicators detected")

        if vendor:
            reasoning.append(f"Vendor hint detected: {vendor}")

        confidence = float(evidence.get("confidence", 0.0))

        return ParserProposal(
            parser_name=parser_name,
            vendor=vendor,
            format_type=format_type,
            mappings=mappings,
            timestamp_field=timestamp_field,
            confidence=confidence,
            reasoning=reasoning,
            source="local_ai",
        )