"""
Tests for canonical event models.

Verifies that Pydantic models validate and serialize correctly.
"""

import pytest
import json
from datetime import datetime
from backend.models.event import (
    CanonicalEvent,
    SourceInfo,
    DestinationInfo,
    NetworkInfo,
    EventInfo,
    ObserverInfo,
    RawData,
    ProvenanceInfo,
    EventResponse,
    ParseError,
)


class TestSourceInfo:
    """Test SourceInfo model."""
    
    def test_create_minimal_source(self):
        """Test creating a source with only IP."""
        source = SourceInfo(ip="10.0.0.5")
        assert source.ip == "10.0.0.5"
        assert source.port is None
        assert source.hostname is None
    
    def test_create_full_source(self):
        """Test creating a complete source."""
        source = SourceInfo(
            ip="10.0.0.5",
            port=443,
            hostname="client.example.com"
        )
        assert source.ip == "10.0.0.5"
        assert source.port == 443
        assert source.hostname == "client.example.com"
    
    def test_source_json_serialization(self):
        """Test that source serializes to JSON."""
        source = SourceInfo(ip="10.0.0.5", port=443)
        json_str = source.model_dump_json()
        data = json.loads(json_str)
        
        assert data["ip"] == "10.0.0.5"
        assert data["port"] == 443


class TestDestinationInfo:
    """Test DestinationInfo model."""
    
    def test_create_destination(self):
        """Test creating a destination."""
        dest = DestinationInfo(
            ip="192.168.1.20",
            port=8443,
            hostname="server.example.com"
        )
        assert dest.ip == "192.168.1.20"
        assert dest.port == 8443


class TestNetworkInfo:
    """Test NetworkInfo model."""
    
    def test_network_protocol(self):
        """Test network protocol field."""
        network = NetworkInfo(protocol="TCP")
        assert network.protocol == "TCP"


class TestEventInfo:
    """Test EventInfo model."""
    
    def test_event_with_all_fields(self):
        """Test event with action, severity, and category."""
        event = EventInfo(
            action="deny",
            severity="high",
            category="network"
        )
        assert event.action == "deny"
        assert event.severity == "high"
        assert event.category == "network"


class TestObserverInfo:
    """Test ObserverInfo model."""
    
    def test_observer_creation(self):
        """Test creating observer info."""
        observer = ObserverInfo(
            vendor="Fortinet",
            product="FortiGate",
            hostname="FW01"
        )
        assert observer.vendor == "Fortinet"
        assert observer.product == "FortiGate"


class TestRawData:
    """Test RawData model."""
    
    def test_raw_data_required(self):
        """Test that raw message is required."""
        with pytest.raises(ValueError):
            RawData()
    
    def test_raw_data_creation(self):
        """Test creating raw data with message."""
        raw = RawData(message="date=2026-09-09 devname=FW01")
        assert raw.message == "date=2026-09-09 devname=FW01"


class TestProvenanceInfo:
    """Test ProvenanceInfo model."""
    
    def test_provenance_with_defaults(self):
        """Test provenance with required parser field only."""
        prov = ProvenanceInfo(parser="fortinet")
        assert prov.parser == "fortinet"
        assert prov.parser_version == "1.0"
        assert prov.mapping_version == "1.0"
        assert prov.confidence == 1.0
        assert isinstance(prov.processed_at, datetime)
    
    def test_provenance_with_custom_values(self):
        """Test provenance with custom confidence (for AI parsers)."""
        prov = ProvenanceInfo(
            parser="fortinet",
            confidence=0.85,
            parser_version="2.0"
        )
        assert prov.confidence == 0.85
        assert prov.parser_version == "2.0"


class TestCanonicalEvent:
    """Test CanonicalEvent model (the main schema)."""
    
    def test_create_minimal_event(self):
        """Test creating minimal canonical event."""
        event = CanonicalEvent(
            timestamp=datetime(2026, 9, 9, 20, 31, 22),
            raw=RawData(message="raw log"),
            provenance=ProvenanceInfo(parser="fortinet")
        )
        
        assert event.timestamp == datetime(2026, 9, 9, 20, 31, 22)
        assert event.raw.message == "raw log"
        assert event.provenance.parser == "fortinet"
        assert event.event_id is not None  # Should have auto-generated UUID
    
    def test_create_full_event(self):
        """Test creating a complete canonical event."""
        event = CanonicalEvent(
            timestamp=datetime(2026, 9, 9, 20, 31, 22),
            source=SourceInfo(ip="10.0.0.5", port=443),
            destination=DestinationInfo(ip="192.168.1.20", port=8443),
            network=NetworkInfo(protocol="TCP"),
            event=EventInfo(action="deny", severity="high"),
            observer=ObserverInfo(vendor="Fortinet", product="FortiGate"),
            raw=RawData(message="date=2026-09-09 devname=FW01 srcip=10.0.0.5"),
            unmapped={"devname": "FW01", "session_id": "12345"},
            provenance=ProvenanceInfo(parser="fortinet", confidence=1.0)
        )
        
        assert event.source.ip == "10.0.0.5"
        assert event.destination.port == 8443
        assert event.event.action == "deny"
        assert event.observer.vendor == "Fortinet"
        assert event.raw.message.startswith("date=")
        assert event.unmapped["devname"] == "FW01"
    
    def test_event_json_serialization(self):
        """Test that canonical event serializes to JSON."""
        event = CanonicalEvent(
            timestamp=datetime(2026, 9, 9, 20, 31, 22),
            raw=RawData(message="test log"),
            provenance=ProvenanceInfo(parser="fortinet")
        )
        
        json_str = event.model_dump_json()
        data = json.loads(json_str)
        
        assert data["raw"]["message"] == "test log"
        assert data["provenance"]["parser"] == "fortinet"
        assert "event_id" in data
    
    def test_event_raw_data_is_preserved(self):
        """CRITICAL TEST: Verify raw message is never lost."""
        original_message = "date=2026-09-09 devname=FW01 srcip=10.0.0.5 dstip=192.168.1.20"
        
        event = CanonicalEvent(
            timestamp=datetime(2026, 9, 9),
            raw=RawData(message=original_message),
            provenance=ProvenanceInfo(parser="fortinet")
        )
        
        # Raw data must be preserved exactly
        assert event.raw.message == original_message
        
        # Serialize and deserialize
        json_str = event.model_dump_json()
        data = json.loads(json_str)
        assert data["raw"]["message"] == original_message
    
    def test_event_unmapped_fields_preserved(self):
        """Test that unmapped fields are preserved."""
        event = CanonicalEvent(
            timestamp=datetime(2026, 9, 9),
            raw=RawData(message="test"),
            unmapped={
                "session_id": "98231",
                "policy_id": "policy_17",
                "unknown_field": "unknown_value"
            },
            provenance=ProvenanceInfo(parser="fortinet")
        )
        
        assert event.unmapped["session_id"] == "98231"
        assert len(event.unmapped) == 3
        
        # Verify unmapped survives serialization
        json_str = event.model_dump_json()
        data = json.loads(json_str)
        assert data["unmapped"]["session_id"] == "98231"
    
    def test_event_auto_generates_uuid(self):
        """Test that event automatically generates unique IDs."""
        event1 = CanonicalEvent(
            timestamp=datetime(2026, 9, 9),
            raw=RawData(message="log1"),
            provenance=ProvenanceInfo(parser="fortinet")
        )
        
        event2 = CanonicalEvent(
            timestamp=datetime(2026, 9, 9),
            raw=RawData(message="log2"),
            provenance=ProvenanceInfo(parser="fortinet")
        )
        
        assert event1.event_id != event2.event_id
    
    def test_event_strict_schema(self):
        """Test that extra fields are not allowed in canonical event."""
        with pytest.raises(ValueError):
            CanonicalEvent(
                timestamp=datetime(2026, 9, 9),
                raw=RawData(message="test"),
                provenance=ProvenanceInfo(parser="fortinet"),
                extra_field="not allowed"  # Should raise error
            )


class TestParseError:
    """Test ParseError model."""
    
    def test_create_parse_error(self):
        """Test creating a parse error response."""
        error = ParseError(
            status="unknown_source",
            message="No parser found for this log"
        )
        assert error.accepted is False
        assert error.status == "unknown_source"
    
    def test_error_json_serialization(self):
        """Test that error serializes to JSON."""
        error = ParseError(
            status="parse_failure",
            message="Failed to parse log",
            raw_message="malformed input"
        )
        json_str = error.model_dump_json()
        data = json.loads(json_str)
        
        assert data["accepted"] is False
        assert data["status"] == "parse_failure"


class TestEventResponse:
    """Test EventResponse model (API response wrapper)."""
    
    def test_success_response(self):
        """Test a successful event response."""
        event = CanonicalEvent(
            timestamp=datetime(2026, 9, 9),
            raw=RawData(message="test"),
            provenance=ProvenanceInfo(parser="fortinet")
        )
        
        response = EventResponse(accepted=True, event=event)
        assert response.accepted is True
        assert response.event is not None
        assert response.error is None
    
    def test_error_response(self):
        """Test an error event response."""
        error = ParseError(
            status="unknown_source",
            message="Could not detect source"
        )
        
        response = EventResponse(accepted=False, error=error)
        assert response.accepted is False
        assert response.event is None
        assert response.error is not None
    
    def test_response_json_serialization(self):
        """Test response serialization."""
        event = CanonicalEvent(
            timestamp=datetime(2026, 9, 9),
            raw=RawData(message="test"),
            provenance=ProvenanceInfo(parser="fortinet")
        )
        
        response = EventResponse(accepted=True, event=event)
        json_str = response.model_dump_json()
        data = json.loads(json_str)
        
        assert data["accepted"] is True
        assert "event" in data


# Integration test showing full event lifecycle
class TestCanonicalEventIntegration:
    """Integration tests for canonical event."""
    
    def test_full_event_lifecycle(self):
        """Test creating, validating, and serializing an event."""
        # 1. Create event
        event = CanonicalEvent(
            timestamp=datetime(2026, 9, 9, 20, 31, 22),
            source=SourceInfo(ip="10.0.0.5", port=443),
            destination=DestinationInfo(ip="192.168.1.20", port=8443),
            network=NetworkInfo(protocol="TCP"),
            event=EventInfo(action="deny", severity="high", category="network"),
            observer=ObserverInfo(vendor="Fortinet", product="FortiGate"),
            raw=RawData(message="date=2026-09-09 time=20:31:22 devname=FW01 srcip=10.0.0.5"),
            unmapped={"devname": "FW01", "time": "20:31:22"},
            provenance=ProvenanceInfo(parser="fortinet", confidence=1.0)
        )
        
        # 2. Serialize to JSON
        json_str = event.model_dump_json()
        assert isinstance(json_str, str)
        
        # 3. Deserialize from JSON
        data = json.loads(json_str)
        restored_event = CanonicalEvent(**data)
        
        # 4. Verify all data is preserved
        assert restored_event.source.ip == "10.0.0.5"
        assert restored_event.event.action == "deny"
        assert restored_event.raw.message.startswith("date=")
        assert restored_event.unmapped["devname"] == "FW01"
        assert restored_event.provenance.parser == "fortinet"
