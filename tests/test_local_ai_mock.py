from backend.core.local_ai_mock import DeterministicLocalAI


def test_deterministic_local_ai_generates_key_value_proposal():
    adapter = DeterministicLocalAI()

    evidence = {
        "format_type": "key_value",
        "timestamp_detected": True,
        "key_value_fields": ["user", "src", "result"],
        "ip_addresses": ["10.0.0.5"],
        "vendor_hints": [],
        "confidence": 0.85,
    }

    proposal = adapter.generate_parser_proposal(
        raw_log="timestamp=2026-09-11 user=admin src=10.0.0.5 result=failed",
        evidence=evidence,
    )

    assert proposal.parser_name == "unknown_device"
    assert proposal.format_type == "key_value"
    assert proposal.mappings["user"] == "user"
    assert proposal.mappings["src"] == "source.ip"
    assert proposal.mappings["result"] == "event.action"
    assert proposal.timestamp_field == "timestamp"
    assert proposal.confidence == 0.85
    assert proposal.source == "local_ai"


def test_deterministic_local_ai_uses_vendor_hint():
    adapter = DeterministicLocalAI()

    evidence = {
        "format_type": "key_value",
        "timestamp_detected": True,
        "key_value_fields": ["user", "src"],
        "ip_addresses": ["10.0.0.5"],
        "vendor_hints": ["fortinet"],
        "confidence": 0.9,
    }

    proposal = adapter.generate_parser_proposal(
        raw_log="Fortinet user=admin src=10.0.0.5",
        evidence=evidence,
    )

    assert proposal.parser_name == "fortinet_unknown"
    assert proposal.vendor == "fortinet"
    assert "Vendor hint detected: fortinet" in proposal.reasoning


def test_deterministic_local_ai_handles_plain_text():
    adapter = DeterministicLocalAI()

    evidence = {
        "format_type": "plain_text",
        "timestamp_detected": False,
        "key_value_fields": [],
        "ip_addresses": [],
        "vendor_hints": [],
        "confidence": 0.1,
    }

    proposal = adapter.generate_parser_proposal(
        raw_log="DEVICE_X authentication failure",
        evidence=evidence,
    )

    assert proposal.parser_name == "unknown_device"
    assert proposal.format_type == "plain_text"
    assert proposal.mappings == {}
    assert proposal.timestamp_field is None
    assert proposal.confidence == 0.1