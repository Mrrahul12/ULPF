from backend.models.parser_definition import ParserDefinition
from backend.parsers.declarative import DeclarativeParser


def test_declarative_key_value_parser():
    definition = ParserDefinition(
        parser_name="generated_fortinet",
        format_type="key_value",
        mappings={
            "srcip": "source.ip",
            "dstip": "destination.ip",
            "action": "event.action",
        },
    )

    parser = DeclarativeParser(definition)

    log = "srcip=10.0.0.5 dstip=192.168.1.10 action=deny"

    assert parser.detect(log) is True

    success, parsed, error = parser.parse(log)

    assert success is True
    assert error == ""
    assert parsed["srcip"] == "10.0.0.5"

    normalized, unmapped = parser.normalize(parsed)

    assert normalized["source.ip"] == "10.0.0.5"
    assert normalized["destination.ip"] == "192.168.1.10"
    assert normalized["event.action"] == "deny"
    assert "srcip" not in unmapped


def test_declarative_json_parser():
    definition = ParserDefinition(
        parser_name="generated_json",
        format_type="json",
        mappings={
            "src_ip": "source.ip",
        },
    )

    parser = DeclarativeParser(definition)

    log = '{"src_ip": "10.0.0.5", "action": "allow"}'

    assert parser.detect(log) is True

    success, parsed, error = parser.parse(log)

    assert success is True
    assert error == ""

    normalized, unmapped = parser.normalize(parsed)

    assert normalized["source.ip"] == "10.0.0.5"
    assert unmapped["action"] == "allow"


def test_declarative_plain_text_parser():
    definition = ParserDefinition(
        parser_name="generated_plain",
        format_type="plain_text",
        mappings={
            "message": "message",
        },
    )

    parser = DeclarativeParser(definition)

    log = "Unknown vendor firewall event"

    assert parser.detect(log) is True

    success, parsed, error = parser.parse(log)

    assert success is True
    assert error == ""

    normalized, unmapped = parser.normalize(parsed)

    assert normalized["message"] == log
    assert unmapped == {}


def test_declarative_parser_rejects_invalid_log():
    definition = ParserDefinition(
        parser_name="generated_json",
        format_type="json",
    )

    parser = DeclarativeParser(definition)

    assert parser.detect("") is False

    success, parsed, error = parser.parse("not-json")

    assert success is False
    assert parsed == {}
    assert error != ""