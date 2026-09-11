from datetime import datetime, timezone

import pytest

from backend.models.dynamic_parser import DynamicParserRecord


def test_dynamic_parser_record_creation():
    approved_at = datetime.now(timezone.utc)

    record = DynamicParserRecord(
        parser_name="fortinet_generated",
        approved_by="security_admin",
        approved_at=approved_at,
    )

    assert record.parser_name == "fortinet_generated"
    assert record.approved_by == "security_admin"


def test_default_version():
    record = DynamicParserRecord(
        parser_name="test_parser",
        approved_by="admin",
        approved_at=datetime.now(timezone.utc),
    )

    assert record.version == "generated-1.0"


def test_default_source():
    record = DynamicParserRecord(
        parser_name="test_parser",
        approved_by="admin",
        approved_at=datetime.now(timezone.utc),
    )

    assert record.source == "local_ai"


def test_confidence_range():
    record = DynamicParserRecord(
        parser_name="test_parser",
        approved_by="admin",
        approved_at=datetime.now(timezone.utc),
        confidence=0.85,
    )

    assert record.confidence == 0.85


def test_invalid_confidence_rejected():
    with pytest.raises(ValueError):
        DynamicParserRecord(
            parser_name="test_parser",
            approved_by="admin",
            approved_at=datetime.now(timezone.utc),
            confidence=1.5,
        )


def test_active_defaults_to_true():
    record = DynamicParserRecord(
        parser_name="test_parser",
        approved_by="admin",
        approved_at=datetime.now(timezone.utc),
    )

    assert record.active is True


def test_registered_at_created_automatically():
    record = DynamicParserRecord(
        parser_name="test_parser",
        approved_by="admin",
        approved_at=datetime.now(timezone.utc),
    )

    assert record.registered_at is not None
    assert record.registered_at.tzinfo is not None