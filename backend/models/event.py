"""
Canonical event models using Pydantic v2.

This module defines the data structures for representing a normalized,
vendor-agnostic log event. All events conform to this schema.

Key principles:
- Type safety via Pydantic validation
- Easy JSON serialization
- Never lose raw data (raw.message always present)
- Never lose unmapped fields
- Full provenance tracking
"""

from datetime import datetime
from typing import Optional, Any, Dict
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict


class SourceInfo(BaseModel):
    """
    Source (origin) of the network event.
    
    Typically represents the client/initiator in a connection.
    """
    model_config = ConfigDict(extra='allow')  # Allow extra fields if vendor provides them
    
    ip: Optional[str] = Field(
        default=None,
        description="Source IP address"
    )
    port: Optional[int] = Field(
        default=None,
        description="Source port number"
    )
    hostname: Optional[str] = Field(
        default=None,
        description="Source hostname (if resolvable)"
    )


class DestinationInfo(BaseModel):
    """
    Destination (target) of the network event.
    
    Typically represents the server/receiver in a connection.
    """
    model_config = ConfigDict(extra='allow')
    
    ip: Optional[str] = Field(
        default=None,
        description="Destination IP address"
    )
    port: Optional[int] = Field(
        default=None,
        description="Destination port number"
    )
    hostname: Optional[str] = Field(
        default=None,
        description="Destination hostname (if resolvable)"
    )


class NetworkInfo(BaseModel):
    """
    Network layer information.
    """
    model_config = ConfigDict(extra='allow')
    
    protocol: Optional[str] = Field(
        default=None,
        description="Network protocol (TCP, UDP, ICMP, etc.)"
    )


class EventInfo(BaseModel):
    """
    High-level event information.
    """
    model_config = ConfigDict(extra='allow')
    
    action: Optional[str] = Field(
        default=None,
        description="Event action (allow, deny, drop, etc.)"
    )
    severity: Optional[str] = Field(
        default=None,
        description="Event severity level (critical, high, medium, low, info)"
    )
    category: Optional[str] = Field(
        default=None,
        description="Event category (network, security, authentication, etc.)"
    )


class ObserverInfo(BaseModel):
    """
    Information about the device/system that generated the log.
    
    Typically a firewall, IPS, VPN gateway, or other security appliance.
    """
    model_config = ConfigDict(extra='allow')
    
    vendor: Optional[str] = Field(
        default=None,
        description="Vendor name (Cisco, Fortinet, Palo Alto, etc.)"
    )
    product: Optional[str] = Field(
        default=None,
        description="Product name (ASA, FortiGate, Panorama, etc.)"
    )
    hostname: Optional[str] = Field(
        default=None,
        description="Hostname of the observer device"
    )


class RawData(BaseModel):
    """
    Preservation of the original, unmodified log message.
    
    CRITICAL: This must ALWAYS be populated. Raw data must NEVER be lost.
    """
    model_config = ConfigDict(extra='allow')
    
    message: str = Field(
        ...,  # Required field
        description="The exact original log message, unmodified"
    )


class ProvenanceInfo(BaseModel):
    """
    Metadata about how this event was processed.
    
    Enables traceability, debugging, and future AI confidence tracking.
    Design allows extension without breaking existing data.
    """
    model_config = ConfigDict(extra='allow')
    
    parser: str = Field(
        ...,
        description="Name of the parser that processed this event"
    )
    parser_version: str = Field(
        default="1.0",
        description="Version of the parser used"
    )
    mapping_version: str = Field(
        default="1.0",
        description="Version of the field mappings used"
    )
    confidence: float = Field(
        default=1.0,
        description="Confidence score (1.0 = deterministic, <1.0 = AI-inferred)"
    )
    processed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the event was processed"
    )


class CanonicalEvent(BaseModel):
    """
    Canonical representation of a normalized log event.
    
    This is the core data structure of ULPF Phase 1.
    
    Key properties:
    - Vendor-agnostic: works across all supported sources
    - Lossless: never discards original data
    - Traceable: full provenance tracking
    - Type-safe: all fields validated by Pydantic
    - Serializable: converts cleanly to JSON
    
    Example:
    {
        "event_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2026-09-09T20:31:22Z",
        "source": {
            "ip": "10.0.0.5",
            "port": 443,
            "hostname": null
        },
        "destination": {
            "ip": "192.168.1.20",
            "port": 8443,
            "hostname": null
        },
        "network": {
            "protocol": "TCP"
        },
        "event": {
            "action": "deny",
            "severity": "high",
            "category": "network"
        },
        "observer": {
            "vendor": "Fortinet",
            "product": "FortiGate",
            "hostname": "FW01"
        },
        "raw": {
            "message": "date=2026-09-09 time=20:31:22 devname=FW01 ..."
        },
        "unmapped": {
            "sessionid": "98231",
            "policy_id": "17"
        },
        "provenance": {
            "parser": "fortinet",
            "parser_version": "1.0",
            "mapping_version": "1.0",
            "confidence": 1.0,
            "processed_at": "2026-09-09T20:31:22Z"
        }
    }
    """
    model_config = ConfigDict(extra='forbid')  # Strict schema for canonical events
    
    # Core identification
    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this event"
    )
    
    # Timestamp
    timestamp: datetime = Field(
        ...,
        description="Event timestamp (normalized to ISO 8601)"
    )
    
    # Network information
    source: SourceInfo = Field(
        default_factory=SourceInfo,
        description="Source address information"
    )
    destination: DestinationInfo = Field(
        default_factory=DestinationInfo,
        description="Destination address information"
    )
    network: NetworkInfo = Field(
        default_factory=NetworkInfo,
        description="Network layer details"
    )
    
    # Event details
    event: EventInfo = Field(
        default_factory=EventInfo,
        description="High-level event information"
    )
    
    # Observer information
    observer: ObserverInfo = Field(
        default_factory=ObserverInfo,
        description="Information about the device that generated the log"
    )
    
    # Data preservation
    raw: RawData = Field(
        ...,
        description="Original, unmodified log message (MUST always be present)"
    )
    
    unmapped: Dict[str, Any] = Field(
        default_factory=dict,
        description="Vendor-specific fields that don't have canonical mappings"
    )
    
    # Processing metadata
    provenance: ProvenanceInfo = Field(
        ...,
        description="Metadata about processing (parser, version, confidence, etc.)"
    )


class ParseError(BaseModel):
    """
    Error response when log processing fails.
    """
    accepted: bool = Field(default=False)
    status: str = Field(description="Error status code")
    message: str = Field(description="Human-readable error message")
    raw_message: Optional[str] = Field(default=None, description="The raw input that failed")


class EventResponse(BaseModel):
    """
    API response for event processing.
    """
    accepted: bool = Field(description="Whether the event was successfully processed")
    event: Optional[CanonicalEvent] = Field(default=None, description="The processed event")
    error: Optional[ParseError] = Field(default=None, description="Error details if processing failed")
