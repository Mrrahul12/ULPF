"""Security checks for declarative parser definitions."""

from backend.models.parser_definition import ParserDefinition


class SandboxSecurityError(ValueError):
    """Raised when a parser definition violates sandbox security rules."""


_BLOCKED_TOKENS = {
    "__import__",
    "__builtins__",
    "eval",
    "exec",
    "compile",
    "open",
    "os.",
    "sys.",
    "subprocess",
    "socket",
    "requests",
    "urllib",
}


def validate_parser_security(
    definition: ParserDefinition,
) -> ParserDefinition:
    """
    Validate that a declarative parser definition contains
    no executable or system-level operations.
    """

    values = [
        definition.parser_name,
        definition.format_type,
        definition.timestamp_field or "",
    ]

    for source_field, canonical_field in definition.mappings.items():
        values.extend([source_field, canonical_field])

    for value in values:
        lowered = value.lower()

        for token in _BLOCKED_TOKENS:
            if token.lower() in lowered:
                raise SandboxSecurityError(
                    f"blocked token detected: {token}"
                )

    return definition