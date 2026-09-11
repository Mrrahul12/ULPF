"""Service for managing dynamically generated parsers."""

from backend.models.dynamic_parser import DynamicParserRecord
from backend.models.parser_approval import ApprovalStatus, ParserApproval
from backend.models.parser_definition import ParserDefinition
from backend.parsers.declarative import DeclarativeParser
from backend.parsers.registry import ParserRegistry, get_registry


class DynamicRegistryService:
    """Manage approved dynamically generated parsers."""

    def __init__(self, registry: ParserRegistry | None = None):
        self.registry = registry or get_registry()
        self.records: dict[str, DynamicParserRecord] = {}

    def register(
        self,
        definition: ParserDefinition,
        approval: ParserApproval,
        vendor: str | None = None,
        product: str | None = None,
        confidence: float = 0.0,
        source: str = "local_ai",
    ) -> DynamicParserRecord:
        """Register a parser only when human approval is present."""

        if approval.status != ApprovalStatus.APPROVED:
            raise ValueError(
                "Parser cannot be dynamically registered without "
                "human approval"
            )

        if not approval.reviewer or not approval.reviewer.strip():
            raise ValueError(
                "Approved parser must have a reviewer"
            )

        if approval.reviewed_at is None:
            raise ValueError(
                "Approved parser must have a reviewed_at timestamp"
            )

        parser = DeclarativeParser(definition)

        self.registry.register_approved(
            parser=parser,
            approval=approval,
        )

        record = DynamicParserRecord(
            parser_name=definition.parser_name,
            version=parser.version,
            vendor=vendor,
            product=product,
            source=source,
            confidence=confidence,
            approved_by=approval.reviewer,
            approved_at=approval.reviewed_at,
        )

        self.records[definition.parser_name] = record

        return record

    def get(self, parser_name: str) -> DynamicParserRecord | None:
        """Return metadata for a dynamic parser."""
        return self.records.get(parser_name)

    def get_parser(self, parser_name: str):
        """Return the registered parser instance if it exists and is active."""

        record = self.records.get(parser_name)

        if record is None or not record.active:
            return None

        return self.registry.get_parser(parser_name)

    def list_parsers(self) -> list[str]:
        """Return names of active dynamic parsers."""

        return [
            record.parser_name
            for record in self.records.values()
            if record.active
        ]

    
    def list_active(self) -> list[DynamicParserRecord]:
        """Return all active dynamic parsers."""
        return [
            record
            for record in self.records.values()
            if record.active
        ]

    def deactivate(self, parser_name: str) -> DynamicParserRecord:
        """Deactivate a dynamic parser."""

        record = self.records.get(parser_name)

        if record is None:
            raise KeyError(
                f"Dynamic parser not found: {parser_name}"
            )

        if not record.active:
            raise ValueError(
                f"Dynamic parser already inactive: {parser_name}"
            )

        record.active = False

        self.registry.unregister(parser_name)

        return record

_default_dynamic_registry_service: DynamicRegistryService | None = None


def get_dynamic_registry() -> DynamicRegistryService:
    """Return the application-wide dynamic registry service."""

    global _default_dynamic_registry_service

    if _default_dynamic_registry_service is None:
        _default_dynamic_registry_service = DynamicRegistryService()

    return _default_dynamic_registry_service


def reset_dynamic_registry() -> None:
    """Reset the application-wide dynamic registry service."""

    global _default_dynamic_registry_service

    if _default_dynamic_registry_service is not None:
        for parser_name in list(
            _default_dynamic_registry_service.records.keys()
        ):
            try:
                _default_dynamic_registry_service.registry.unregister(
                    parser_name
                )
            except KeyError:
                pass

    _default_dynamic_registry_service = None