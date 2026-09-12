"""
ULPF Phase 1 Foundation Demo

This script demonstrates the core components working together:
1. Parser Registry
2. Base Parser interface
3. Canonical Event model
4. Pydantic validation

Run with: python demo.py
"""
from backend.core.approval_service import ApprovalService
from backend.core.dynamic_registry import DynamicRegistryService
from backend.core.local_ai_mock import DeterministicLocalAI
from backend.core.parser_factory import generate_parser_proposal
from backend.core.parser_sandbox import ParserSandbox
from backend.core.parser_test_generator import ParserTestGenerator
from backend.core.parser_test_runner import ParserTestRunner
from backend.core.unknown_log_intelligence import analyze_unknown_log
from backend.models.parser_approval import ParserApproval
from backend.models.parser_definition import ParserDefinition
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

def demo_unknown_vendor_hero():
    """Demo 4: Unknown vendor automatic parser onboarding."""

    print_section("DEMO 4: UNKNOWN VENDOR HERO DEMO")

    unknown_log = (
        'timestamp="2026-09-12T10:15:30Z" '
        'src=192.168.10.20 '
        'dst=10.0.0.15 '
        'user=admin '
        'result=blocked'
    )

    # ------------------------------------------------------------
    # 1. UNKNOWN VENDOR LOG
    # ------------------------------------------------------------
    print("\n📥 UNKNOWN VENDOR LOG")
    print(f"   {unknown_log}")

    # ------------------------------------------------------------
    # 2. UNKNOWN LOG INTELLIGENCE
    # ------------------------------------------------------------
    print("\n1️⃣  UNKNOWN LOG INTELLIGENCE")

    analysis = analyze_unknown_log(unknown_log)

    print(f"   Format: {analysis.format_type}")
    print(f"   Timestamp detected: {analysis.timestamp_detected}")
    print(f"   Fields: {analysis.key_value_fields}")
    print(f"   Vendor hint: {analysis.vendor_hints}")
    print(f"   Confidence: {analysis.confidence:.2f}")

    # ------------------------------------------------------------
    # 3. LOCAL AI
    # ------------------------------------------------------------
    print("\n2️⃣  LOCAL AI PARSER PROPOSAL")

    local_ai = DeterministicLocalAI()

    proposal = generate_parser_proposal(
        raw_log=unknown_log,
        adapter=local_ai,
    )

    print(f"   Parser: {proposal.parser_name}")
    print(f"   Vendor: {proposal.vendor}")
    print(f"   Format: {proposal.format_type}")
    print(f"   Mappings: {proposal.mappings}")
    print(f"   Source: {proposal.source}")
    print(f"   Confidence: {proposal.confidence:.2f}")

    # ------------------------------------------------------------
    # 4. SAFE PARSER DEFINITION
    # ------------------------------------------------------------
    print("\n3️⃣  SAFE PARSER DEFINITION")

    definition = ParserDefinition(
        parser_name=proposal.parser_name,
        format_type=proposal.format_type,
        mappings=proposal.mappings,
        timestamp_field=proposal.timestamp_field,
    )

    print(f"   Parser definition created: {definition.parser_name}")

    # ------------------------------------------------------------
    # 5. SANDBOX
    # ------------------------------------------------------------
    print("\n4️⃣  SANDBOX + SECURITY VALIDATION")

    sandbox = ParserSandbox()

    sandbox_result = sandbox.run(
        definition=definition,
        raw_log=unknown_log,
    )

    print(f"   Safe: {sandbox_result.safe}")
    print(f"   Success: {sandbox_result.success}")
    print(f"   Parsed fields: {sandbox_result.parsed_fields}")

    if not sandbox_result.success or not sandbox_result.safe:
        raise RuntimeError("Sandbox validation failed")

    # ------------------------------------------------------------
    # 6. AUTOMATED TESTS
    # ------------------------------------------------------------
    print("\n5️⃣  AUTOMATED PARSER TESTS")

    generator = ParserTestGenerator()

    test_cases = generator.generate(
        definition=definition,
        raw_log=unknown_log,
    )

    runner = ParserTestRunner()

    test_results = runner.run(
        definition=definition,
        test_cases=test_cases,
    )

    for result in test_results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"   [{status}] {result['name']}")

    if not test_results or not all(
        result["passed"] for result in test_results
    ):
        raise RuntimeError("Automated parser tests failed")

    # ------------------------------------------------------------
    # 7. HUMAN APPROVAL
    # ------------------------------------------------------------
    print("\n6️⃣  HUMAN APPROVAL GATE")

    approval = ParserApproval(
        parser_name=definition.parser_name,
    )

    approval_service = ApprovalService()

    approval = approval_service.approve(
        approval=approval,
        reviewer="sih_security_admin",
        comment="Approved after sandbox and automated validation",
    )

    print(f"   Status: {approval.status.value}")
    print(f"   Reviewer: {approval.reviewer}")

    # ------------------------------------------------------------
    # 8. DYNAMIC REGISTRATION
    # ------------------------------------------------------------
    print("\n7️⃣  DYNAMIC PARSER REGISTRATION")

    registry = ParserRegistry()

    dynamic_registry = DynamicRegistryService(
        registry=registry,
    )

    record = dynamic_registry.register(
        definition=definition,
        approval=approval,
        vendor=proposal.vendor,
        product=proposal.product,
        confidence=proposal.confidence,
        source=proposal.source,
    )

    print(f"   Parser registered: {record.parser_name}")
    print(f"   Version: {record.version}")
    print(f"   Active: {record.active}")
    print(f"   Approved by: {record.approved_by}")

    # ------------------------------------------------------------
    # 9. PARSE AGAIN
    # ------------------------------------------------------------
    print("\n8️⃣  PARSE WITH NEWLY REGISTERED PARSER")

    parser = dynamic_registry.get_parser(
        definition.parser_name,
    )

    if parser is None:
        raise RuntimeError("Registered parser could not be retrieved")

    success, parsed, error = parser.parse(unknown_log)

    print(f"   Parse success: {success}")
    print(f"   Parsed: {parsed}")

    if not success:
        raise RuntimeError(error)

    # ------------------------------------------------------------
    # 10. NORMALIZATION
    # ------------------------------------------------------------
    print("\n9️⃣  NORMALIZED EVENT")

    normalized, unmapped = parser.normalize(parsed)

    for field, value in normalized.items():
        print(f"   {field:<20} = {value}")

    if unmapped:
        print("\n   Unmapped fields:")
        for field, value in unmapped.items():
            print(f"   {field:<20} = {value}")

    # ------------------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------------------
    print()
    print("=" * 70)
    print("  ✅ UNKNOWN VENDOR SUCCESSFULLY ONBOARDED")
    print("=" * 70)

    print("""
    Unknown Vendor Log
            ↓
    Unknown Log Intelligence
            ↓
    Local AI Proposal
            ↓
    Security + Sandbox
            ↓
    Automated Tests
            ↓
    Human Approval
            ↓
    Dynamic Registry
            ↓
    Normalized Event
    """)

    print("🚀 ULPF UNKNOWN VENDOR HERO DEMO COMPLETE")

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

        # Demo 4: Unknown Vendor Hero Demo
        demo_unknown_vendor_hero()
        
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
        print("   →Step 30: Production Dashboard")
        print("   → Step 31: SIEM / Data Lake Integration")
        print("   → Step 32: Production / Remote Deployment")
        print("   →  Final SIH Demo + Documentation")
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n[!] ERROR: {e}")
        import traceback
        traceback.print_exc()



if __name__ == "__main__":
    main()
