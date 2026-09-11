from backend.core.unknown_log_intelligence import (
    analyze_unknown_log,
)


def test_analyze_key_value_unknown_log():
    raw = (
        "2026-09-11T10:30:22Z "
        "DEVICE_X EVENT login "
        "user=admin src=10.0.0.5 result=failed"
    )

    analysis = analyze_unknown_log(raw)

    assert analysis.is_unknown is True
    assert analysis.format_type == "key_value"
    assert analysis.timestamp_detected is True
    assert "user" in analysis.key_value_fields
    assert "src" in analysis.key_value_fields
    assert "result" in analysis.key_value_fields
    assert "10.0.0.5" in analysis.ip_addresses


def test_analyze_json_like_unknown_log():
    raw = (
        '{"event":"login",'
        '"user":"admin",'
        '"source":"10.0.0.5",'
        '"result":"failed"}'
    )

    analysis = analyze_unknown_log(raw)

    assert analysis.is_unknown is True
    assert analysis.format_type == "json"
    assert analysis.timestamp_detected is False
    assert "10.0.0.5" in analysis.ip_addresses


def test_analyze_plain_text_unknown_log():
    raw = "DEVICE_X authentication failure for admin"

    analysis = analyze_unknown_log(raw)

    assert analysis.is_unknown is True
    assert analysis.format_type == "plain_text"
    assert analysis.key_value_fields == []
    assert analysis.ip_addresses == []


def test_detect_common_indicators():
    raw = (
        "2026-09-11 10:30:22 DEVICE_X "
        "connection from 10.0.0.5:443 "
        "to 192.168.1.20:8443"
    )

    analysis = analyze_unknown_log(raw)

    assert analysis.timestamp_detected is True
    assert "10.0.0.5" in analysis.ip_addresses
    assert "192.168.1.20" in analysis.ip_addresses
    assert 443 in analysis.ports
    assert 8443 in analysis.ports


def test_empty_log_rejected():
    analysis = analyze_unknown_log("")

    assert analysis.is_unknown is True
    assert analysis.format_type == "empty"
    assert analysis.confidence == 0.0