"""Local structural analysis for logs not recognized by registered parsers."""

import json
import re
from typing import List

from pydantic import BaseModel, Field


class UnknownLogAnalysis(BaseModel):
    """Structural intelligence extracted from an unknown log."""

    is_unknown: bool = True
    format_type: str = "unknown"

    timestamp_detected: bool = False

    key_value_fields: List[str] = Field(default_factory=list)
    ip_addresses: List[str] = Field(default_factory=list)
    ports: List[int] = Field(default_factory=list)

    vendor_hints: List[str] = Field(default_factory=list)

    confidence: float = 0.0


_IP_PATTERN = re.compile(
    r"\b(?:"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\."
    r"){3}"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)


_KEY_VALUE_PATTERN = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_.-]*)="
)

_ISO_TIMESTAMP_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}"
    r"(?:[T ]\d{2}:\d{2}:\d{2})"
)

_COMMON_TIMESTAMP_PATTERN = re.compile(
    r"\b\d{4}/\d{2}/\d{2}"
    r"(?:[ T]\d{2}:\d{2}:\d{2})?"
)

_IP_PORT_PATTERN = re.compile(
    r"\b("
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\."
    r"){3}"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r":(\d{1,5})\b"
)


def _detect_timestamp(log: str) -> bool:
    return bool(
        _ISO_TIMESTAMP_PATTERN.search(log)
        or _COMMON_TIMESTAMP_PATTERN.search(log)
    )


def _extract_ips(log: str) -> list[str]:
    return list(
        dict.fromkeys(
            match.group(0)
            for match in _IP_PATTERN.finditer(log)
        )
    )


def _extract_key_value_fields(log: str) -> list[str]:
    return list(dict.fromkeys(_KEY_VALUE_PATTERN.findall(log)))


def _extract_ports(log: str) -> list[int]:
    ports: list[int] = []

    for match in _IP_PORT_PATTERN.finditer(log):
        port = int(match.group(2))

        if 0 <= port <= 65535:
            ports.append(port)

    return list(dict.fromkeys(ports))


def _detect_format(log: str) -> str:
    stripped = log.strip()

    if not stripped:
        return "empty"

    try:
        json.loads(stripped)
        return "json"
    except (json.JSONDecodeError, TypeError):
        pass

    if _KEY_VALUE_PATTERN.search(stripped):
        return "key_value"

    return "plain_text"


def _detect_vendor_hints(log: str) -> list[str]:
    """Extract conservative device/vendor-like tokens.

    This is intentionally heuristic. Step 23 will perform deeper
    parser/vendor inference using the collected evidence.
    """

    hints: list[str] = []

    known_tokens = (
        "fortinet",
        "fortigate",
        "cisco",
        "asa",
        "paloalto",
        "pan-os",
        "checkpoint",
        "juniper",
        "sophos",
    )

    lowered = log.lower()

    for token in known_tokens:
        if token in lowered:
            hints.append(token)

    return hints


def _calculate_confidence(
    format_type: str,
    timestamp_detected: bool,
    key_value_fields: list[str],
    ip_addresses: list[str],
) -> float:
    score = 0.0

    if format_type == "json":
        score += 0.60
    elif format_type == "key_value":
        score += 0.45
    elif format_type == "plain_text":
        score += 0.10

    if timestamp_detected:
        score += 0.15

    if key_value_fields:
        score += min(len(key_value_fields) * 0.05, 0.15)

    if ip_addresses:
        score += 0.10

    return min(score, 1.0)


def analyze_unknown_log(raw_log: str) -> UnknownLogAnalysis:
    """Analyze an unrecognized log locally without calling external AI."""

    if not isinstance(raw_log, str) or not raw_log.strip():
        return UnknownLogAnalysis(
            is_unknown=True,
            format_type="empty",
            confidence=0.0,
        )

    log = raw_log.strip()

    format_type = _detect_format(log)
    timestamp_detected = _detect_timestamp(log)
    key_value_fields = _extract_key_value_fields(log)
    ip_addresses = _extract_ips(log)
    ports = _extract_ports(log)
    vendor_hints = _detect_vendor_hints(log)

    confidence = _calculate_confidence(
        format_type=format_type,
        timestamp_detected=timestamp_detected,
        key_value_fields=key_value_fields,
        ip_addresses=ip_addresses,
    )

    return UnknownLogAnalysis(
        is_unknown=True,
        format_type=format_type,
        timestamp_detected=timestamp_detected,
        key_value_fields=key_value_fields,
        ip_addresses=ip_addresses,
        ports=ports,
        vendor_hints=vendor_hints,
        confidence=confidence,
    )