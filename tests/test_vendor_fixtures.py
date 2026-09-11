"""
Fixture-based regression tests for vendor parsers.
"""

import json
import pytest
from pathlib import Path

from backend.parsers.cisco_asa import CiscoASAParser
from backend.parsers.fortinet import FortinetParser
from backend.parsers.paloalto import PaloAltoParser
from backend.parsers.syslog import SyslogParser
from backend.parsers.json_parser import JSONParser


ROOT = Path(__file__).resolve().parents[1]
DEMO_DATA = ROOT / "demo_data"


class TestCiscoASAFixtures:

    def test_security_fixture(self):
        parser = CiscoASAParser()
        fixture = DEMO_DATA / "cisco_asa" / "security.log"

        logs = fixture.read_text(encoding="utf-8").splitlines()

        assert len(logs) >= 3

        for log in logs:
            assert parser.detect(log) is True

            success, parsed, error = parser.parse(log)

            assert success is True, error
            assert isinstance(parsed, dict)
            assert len(parsed) > 0

            normalized, unmapped = parser.normalize(parsed)

            assert isinstance(normalized, dict)
            assert isinstance(unmapped, dict)


class TestFortinetFixtures:

    def test_traffic_fixture(self):
        parser = FortinetParser()
        fixture = DEMO_DATA / "fortinet" / "traffic.log"

        logs = fixture.read_text(encoding="utf-8").splitlines()

        assert len(logs) >= 2

        for log in logs:
            assert parser.detect(log) is True

            success, parsed, error = parser.parse(log)

            assert success is True, error
            assert parsed["devname"] == "FW01"

            normalized, unmapped = parser.normalize(parsed)

            assert normalized["observer.vendor"] == "Fortinet"
            assert normalized["observer.hostname"] == "FW01"
            assert "source.ip" in normalized
            assert "destination.ip" in normalized


class TestPaloAltoFixtures:

    def test_traffic_fixture(self):
        parser = PaloAltoParser()
        fixture = DEMO_DATA / "paloalto" / "traffic.log"

        logs = fixture.read_text(encoding="utf-8").splitlines()

        assert len(logs) >= 2

        for log in logs:
            assert parser.detect(log) is True

            success, parsed, error = parser.parse(log)

            assert success is True, error
            assert isinstance(parsed, dict)
            assert len(parsed) > 0

            normalized, unmapped = parser.normalize(parsed)

            assert normalized["observer.vendor"] == "Palo Alto"


class TestSyslogFixtures:

    def test_rfc5424_fixture(self):
        parser = SyslogParser()
        fixture = DEMO_DATA / "syslog" / "rfc5424.log"

        logs = fixture.read_text(encoding="utf-8").splitlines()

        assert len(logs) >= 2

        for log in logs:
            assert parser.detect(log) is True

            success, parsed, error = parser.parse(log)

            assert success is True, error
            assert parsed["hostname"] == "fw01"
            assert "message" in parsed

            normalized, unmapped = parser.normalize(parsed)

            assert isinstance(normalized, dict)

    def test_rfc3164_fixture(self):
        parser = SyslogParser()
        fixture = DEMO_DATA / "syslog" / "rfc3164.log"

        logs = fixture.read_text(encoding="utf-8").splitlines()

        assert len(logs) >= 2

        for log in logs:
            assert parser.detect(log) is True

            success, parsed, error = parser.parse(log)

            assert success is True, error
            assert parsed["hostname"] == "fw01"
            assert "message" in parsed

            normalized, unmapped = parser.normalize(parsed)

            assert isinstance(normalized, dict)


class TestJSONFixtures:

    def test_events_fixture(self):
        parser = JSONParser()
        fixture = DEMO_DATA / "json" / "events.json"

        events = json.loads(
            fixture.read_text(encoding="utf-8")
        )

        assert isinstance(events, list)
        assert len(events) >= 2

        for event in events:
            log = json.dumps(event)

            assert parser.detect(log) is True

            success, parsed, error = parser.parse(log)

            assert success is True, error

            normalized, unmapped = parser.normalize(parsed)

            assert normalized["source.ip"] == event["src_ip"]
            assert normalized["destination.ip"] == event["dst_ip"]
            assert normalized["event.action"] == event["action"]

class TestEdgeCaseFixtures:
    """Verify parsers handle malformed input safely."""

    def test_cisco_malformed_fixture(self):
        parser = CiscoASAParser()
        fixture = DEMO_DATA / "edge_cases" / "cisco_malformed.log"

        logs = fixture.read_text(encoding="utf-8").splitlines()

        for log in logs:
            try:
                detected = parser.detect(log)
                assert isinstance(detected, bool)

                success, parsed, error = parser.parse(log)

                assert isinstance(success, bool)
                assert isinstance(parsed, dict)
            except Exception as exc:
                pytest.fail(f"Cisco parser crashed on malformed input: {exc}")

    def test_fortinet_incomplete_fixture(self):
        parser = FortinetParser()
        fixture = DEMO_DATA / "edge_cases" / "fortinet_incomplete.log"

        logs = fixture.read_text(encoding="utf-8").splitlines()

        for log in logs:
            try:
                detected = parser.detect(log)
                assert isinstance(detected, bool)

                success, parsed, error = parser.parse(log)

                assert isinstance(success, bool)
                assert isinstance(parsed, dict)
            except Exception as exc:
                pytest.fail(f"Fortinet parser crashed on malformed input: {exc}")

    def test_paloalto_malformed_fixture(self):
        parser = PaloAltoParser()
        fixture = DEMO_DATA / "edge_cases" / "paloalto_malformed.log"

        logs = fixture.read_text(encoding="utf-8").splitlines()

        for log in logs:
            try:
                detected = parser.detect(log)
                assert isinstance(detected, bool)

                success, parsed, error = parser.parse(log)

                assert isinstance(success, bool)
                assert isinstance(parsed, dict)
            except Exception as exc:
                pytest.fail(f"Palo Alto parser crashed on malformed input: {exc}")

    def test_json_malformed_fixture(self):
        parser = JSONParser()
        fixture = DEMO_DATA / "edge_cases" / "json_malformed.log"

        logs = fixture.read_text(encoding="utf-8").splitlines()

        for log in logs:
            try:
                detected = parser.detect(log)
                assert detected is False

                success, parsed, error = parser.parse(log)

                assert success is False
                assert isinstance(parsed, dict)
            except Exception as exc:
                pytest.fail(f"JSON parser crashed on malformed input: {exc}")

    def test_syslog_malformed_fixture(self):
        parser = SyslogParser()
        fixture = DEMO_DATA / "edge_cases" / "syslog_malformed.log"

        logs = fixture.read_text(encoding="utf-8").splitlines()

        for log in logs:
            try:
                detected = parser.detect(log)
                assert isinstance(detected, bool)

                success, parsed, error = parser.parse(log)

                assert isinstance(success, bool)
                assert isinstance(parsed, dict)
            except Exception as exc:
                pytest.fail(f"Syslog parser crashed on malformed input: {exc}")

    def test_empty_fixture(self):
        fixture = DEMO_DATA / "edge_cases" / "empty.log"
        log = fixture.read_text(encoding="utf-8")

        assert log.strip() == ""

        parsers = [
            CiscoASAParser(),
            FortinetParser(),
            PaloAltoParser(),
            SyslogParser(),
            JSONParser(),
        ]

        for parser in parsers:
            try:
                detected = parser.detect(log)
                assert isinstance(detected, bool)

                success, parsed, error = parser.parse(log)

                assert isinstance(success, bool)
                assert isinstance(parsed, dict)
            except Exception as exc:
                pytest.fail(
                    f"{parser.__class__.__name__} crashed on empty input: {exc}"
                )            