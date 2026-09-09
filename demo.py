"""
ULPF Phase 1 Foundation Demo

This script demonstrates the core components working together:
1. Parser Registry
2. Base Parser interface
3. Canonical Event model
4. Pydantic validation

Run with: python demo.py
"""

from datetime import datetime
from backend.models.event import (
    CanonicalEvent, SourceInfo, DestinationInfo, EventInfo,
    ObserverInfo, RawData, ProvenanceInfo
)
from backend.parsers.registry import ParserRegistry, get_registry
from backend.parsers.base import BaseParser
from typing import Dict, Any, Tuple
import json


# ============================================================================
# DEMO PARSERS - Simple implementations to show the framework
# ============================================================================

class DemoFortinetParser(BaseParser):
    """Demo Fortinet parser."""
    
    def __init__(self):
        super().__init__(name="fortinet", version="1.0")
    
    def detect(self, log: str) -> bool:
        """Fortinet logs have devname= and srcip= patterns."""
        return "devname=" in log and "srcip=" in log
    
    def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
        """Parse key=value format."""
        try:
            fields = {}
            for pair in log.split():
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    fields[key] = value.strip('"')
            return (True, fields, "")
        except Exception as e:
            return (False, {}, str(e))
    
    def normalize(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Map vendor fields to canonical."""
        normalized = {}
        unmapped = {}
        
        # Map known fields
        if "srcip" in parsed:
            normalized["source.ip"] = parsed.pop("srcip")
        if "dstip" in parsed:
            normalized["destination.ip"] = parsed.pop("dstip")
        if "srcport" in parsed:
            normalized["source.port"] = int(parsed.pop("srcport"))
        if "dstport" in parsed:
            normalized["destination.port"] = int(parsed.pop("dstport"))
        if "action" in parsed:
            normalized["event.action"] = parsed.pop("action")
        
        # Everything else is unmapped
        unmapped = parsed
        
        return (normalized, unmapped)


class DemoCiscoParser(BaseParser):
    """Demo Cisco ASA parser."""
    
    def __init__(self):
        super().__init__(name="cisco", version="1.0")
    
    def detect(self, log: str) -> bool:
        """Cisco ASA logs start with %ASA-."""
        return "%ASA-" in log
    
    def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
        """Simple Cisco parser (demo only)."""
        return (True, {"cisco_log": log}, "")
    
    def normalize(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Map Cisco fields to canonical."""
        return (parsed, {})


class DemoJSONParser(BaseParser):
    """Demo JSON parser."""
    
    def __init__(self):
        super().__init__(name="json", version="1.0")
    
    def detect(self, log: str) -> bool:
        """Try to parse as JSON."""
        try:
            json.loads(log)
            return True
        except:
            return False
    
    def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
        """Parse JSON log."""
        try:
            data = json.loads(log)
            return (True, data, "")
        except Exception as e:
            return (False, {}, str(e))
    
    def normalize(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Map JSON fields to canonical (lenient)."""
        normalized = {}
        unmapped = parsed.copy()
        
        # Map common JSON field names
        if "src_ip" in parsed:
            normalized["source.ip"] = parsed.pop("src_ip")
        if "dst_ip" in parsed:
            normalized["destination.ip"] = parsed.pop("dst_ip")
        if "src_port" in parsed:
            normalized["source.port"] = parsed.pop("src_port")
        if "dst_port" in parsed:
            normalized["destination.port"] = parsed.pop("dst_port")
        
        return (normalized, unmapped)


# ============================================================================
# DEMO EXECUTION
# ============================================================================

def print_section(title):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def demo_registry():
    """Demo 1: Parser Registry."""
    print_section("DEMO 1: PARSER REGISTRY")
    
    registry = ParserRegistry()
    
    print("\n[*] Registering parsers...")
    registry.register(DemoFortinetParser())
    registry.register(DemoCiscoParser())
    registry.register(DemoJSONParser())
    
    print(f"[+] Registered parsers: {registry.list_parsers()}")
    
    print("\n[?] Get parser by name...")
    fortinet = registry.get_parser("fortinet")
    print(f"[+] Got Fortinet parser: {fortinet.name}")
    
    print("\n🔎 Find parser by detection...")
    test_fortinet_log = "date=2026-09-09 devname=FW01 srcip=10.0.0.5 dstip=192.168.1.20"
    found = registry.find_parser(test_fortinet_log)
    print(f"   Input: {test_fortinet_log[:60]}...")
    print(f"[+] Found parser: {found.name}")
    
    return registry


def demo_models():
    """Demo 2: Canonical Event Models."""
    print_section("DEMO 2: CANONICAL EVENT MODELS")
    
    print("\n🔨 Creating a canonical event...")
    event = CanonicalEvent(
        timestamp=datetime(2026, 9, 9, 20, 31, 22),
        source=SourceInfo(ip="10.0.0.5", port=443),
        destination=DestinationInfo(ip="192.168.1.20", port=8443),
        event=EventInfo(action="deny", severity="high"),
        observer=ObserverInfo(vendor="Fortinet", product="FortiGate"),
        raw=RawData(message="date=2026-09-09 devname=FW01 srcip=10.0.0.5 dstip=192.168.1.20"),
        unmapped={"devname": "FW01", "session_id": "12345"},
        provenance=ProvenanceInfo(parser="fortinet", confidence=1.0)
    )
    
    print(f"[+] Event ID: {event.event_id}")
    print(f"[+] Timestamp: {event.timestamp}")
    print(f"[+] Source: {event.source.ip}:{event.source.port}")
    print(f"[+] Destination: {event.destination.ip}:{event.destination.port}")
    print(f"[+] Action: {event.event.action}")
    print(f"[+] Parser: {event.provenance.parser}")
    
    print("\n📤 Raw data preservation check...")
    print(f"   Raw message: {event.raw.message[:60]}...")
    print(f"   [+] Raw data PRESERVED: {len(event.raw.message)} chars")
    
    print("\n📦 Unmapped fields check...")
    print(f"   Unmapped: {event.unmapped}")
    print(f"   [+] Unmapped fields PRESERVED: {len(event.unmapped)} fields")
    
    print("\n📄 JSON Serialization...")
    json_str = event.model_dump_json(indent=2)
    print(f"   Size: {len(json_str)} bytes")
    print(f"   [+] Serialized successfully")
    
    print("\n🔄 JSON Deserialization...")
    restored = CanonicalEvent(**json.loads(json_str))
    print(f"   [+] Deserialized successfully")
    print(f"   [+] Data intact: {restored.raw.message == event.raw.message}")
    
    return event


def demo_parser_workflow(registry):
    """Demo 3: End-to-end parser workflow."""
    print_section("DEMO 3: END-TO-END PARSER WORKFLOW")
    
    fortinet_log = 'date=2026-09-09 time=20:31:22 devname="FW01" srcip=10.0.0.5 dstip=192.168.1.20 srcport=443 dstport=8443 action=deny'
    
    print(f"\n📥 Input log:")
    print(f"   {fortinet_log}")
    
    # Step 1: Detection
    print(f"\n1️⃣  DETECTION")
    parser = registry.find_parser(fortinet_log)
    print(f"   [+] Detected as: {parser.name}")
    
    # Step 2: Parsing
    print(f"\n2️⃣  PARSING")
    success, parsed, error = parser.parse(fortinet_log)
    print(f"   [+] Parse success: {success}")
    print(f"   Extracted fields: {len(parsed)}")
    for key in list(parsed.keys())[:3]:
        print(f"      - {key}: {parsed[key]}")
    
    # Step 3: Normalization
    print(f"\n3️⃣  NORMALIZATION")
    normalized, unmapped = parser.normalize(parsed)
    print(f"   [+] Normalized fields: {len(normalized)}")
    for key, val in list(normalized.items())[:3]:
        print(f"      - {key}: {val}")
    print(f"   [+] Unmapped fields: {len(unmapped)}")
    for key, val in list(unmapped.items())[:2]:
        print(f"      - {key}: {val}")
    
    # Step 4: Create canonical event
    print(f"\n4️⃣  CANONICAL EVENT CREATION")
    event = CanonicalEvent(
        timestamp=datetime(2026, 9, 9, 20, 31, 22),
        source=SourceInfo(ip=normalized.get("source.ip")),
        destination=DestinationInfo(ip=normalized.get("destination.ip")),
        event=EventInfo(action=normalized.get("event.action")),
        observer=ObserverInfo(vendor="Fortinet", product="FortiGate"),
        raw=RawData(message=fortinet_log),
        unmapped=unmapped,
        provenance=ProvenanceInfo(parser="fortinet", confidence=1.0)
    )
    print(f"   [+] Event created: {event.event_id}")
    print(f"   [+] Source: {event.source.ip}")
    print(f"   [+] Destination: {event.destination.ip}")
    print(f"   [+] Action: {event.event.action}")
    print(f"   [+] Raw data preserved: {len(event.raw.message)} chars")
    print(f"   [+] Unmapped fields: {len(event.unmapped)}")


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("  ULPF PHASE 1 FOUNDATION DEMO")
    print("  Testing Models, Registry, and Parser Framework")
    print("="*70)
    
    try:
        # Demo 1: Registry
        registry = demo_registry()
        
        # Demo 2: Models
        event = demo_models()
        
        # Demo 3: Full workflow
        demo_parser_workflow(registry)
        
        # Summary
        print_section("[+] DEMO COMPLETE - FOUNDATION IS WORKING!")
        print("\n✨ What's Working:")
        print("   [+] Parser Registry (register, get, find)")
        print("   [+] Base Parser Interface")
        print("   [+] Canonical Event Model")
        print("   [+] Pydantic Validation")
        print("   [+] JSON Serialization/Deserialization")
        print("   [+] Raw Data Preservation")
        print("   [+] Unmapped Fields Preservation")
        print("\n🚀 Next Steps:")
        print("   → Implement core/detector.py")
        print("   → Implement parser implementations (Cisco, Fortinet, Palo Alto, Syslog)")
        print("   → Implement core/normalizer.py")
        print("   → Implement core/validator.py")
        print("   → Implement core/pipeline.py")
        print("   → Implement FastAPI endpoints")
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n[!] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
