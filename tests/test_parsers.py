"""
Tests for vendor-specific parsers.

Tests Cisco ASA, Fortinet, Palo Alto, Syslog, and JSON parsers.
"""

import pytest
import json
from backend.parsers.cisco_asa import CiscoASAParser
from backend.parsers.fortinet import FortinetParser
from backend.parsers.paloalto import PaloAltoParser
from backend.parsers.syslog import SyslogParser
from backend.parsers.json_parser import JSONParser


class TestCiscoASAParser:
    """Test Cisco ASA parser."""
    
    def setup_method(self):
        self.parser = CiscoASAParser()
    
    def test_detect_cisco_log(self):
        """Test detecting Cisco logs."""
        log = "%ASA-6-302013: Built inbound TCP connection"
        assert self.parser.detect(log) is True
    
    def test_reject_non_cisco_log(self):
        """Test rejecting non-Cisco logs."""
        log = "date=2026-09-09 devname=FW01"
        assert self.parser.detect(log) is False
    
    def test_parse_cisco_log(self):
        """Test parsing Cisco log."""
        log = "%ASA-6-302013: Built inbound TCP connection 12345 for outside:192.168.1.100/80 to inside:10.0.0.5/443"
        
        success, parsed, error = self.parser.parse(log)
        
        assert success is True
        assert parsed["severity"] == "6"
        assert parsed["message_id"] == "302013"
        assert "192.168.1.100" in parsed.get("source_ip", "")
        assert "10.0.0.5" in parsed.get("destination_ip", "")
    
    def test_normalize_cisco_log(self):
        """Test normalizing Cisco fields."""
        parsed = {
            "severity": "6",
            "message_id": "302013",
            "source_ip": "192.168.1.100",
            "source_port": "80",
            "destination_ip": "10.0.0.5",
            "destination_port": "443"
        }
        
        normalized, unmapped = self.parser.normalize(parsed)
        
        assert normalized["source.ip"] == "192.168.1.100"
        assert normalized["destination.ip"] == "10.0.0.5"
        assert normalized["source.port"] == 80
        assert normalized["destination.port"] == 443
        assert normalized["observer.vendor"] == "Cisco"


class TestFortinetParser:
    """Test Fortinet FortiGate parser."""
    
    def setup_method(self):
        self.parser = FortinetParser()
    
    def test_detect_fortinet_log(self):
        """Test detecting Fortinet logs."""
        log = "date=2026-09-09 devname=FW01 srcip=10.0.0.5 dstip=192.168.1.20"
        assert self.parser.detect(log) is True
    
    def test_reject_non_fortinet_log(self):
        """Test rejecting non-Fortinet logs."""
        log = "%ASA-6-302013: Built inbound"
        assert self.parser.detect(log) is False
    
    def test_parse_fortinet_kv_log(self):
        """Test parsing Fortinet key=value log."""
        log = 'date=2026-09-09 time=20:31:22 devname="FW01" srcip=10.0.0.5 dstip=192.168.1.20 srcport=443 dstport=8443 action=deny'
        
        success, parsed, error = self.parser.parse(log)
        
        assert success is True
        assert parsed["date"] == "2026-09-09"
        assert parsed["devname"] == "FW01"
        assert parsed["srcip"] == "10.0.0.5"
        assert parsed["dstip"] == "192.168.1.20"
        assert parsed["action"] == "deny"
    
    def test_normalize_fortinet_log(self):
        """Test normalizing Fortinet fields."""
        parsed = {
            "srcip": "10.0.0.5",
            "dstip": "192.168.1.20",
            "srcport": "443",
            "dstport": "8443",
            "action": "deny",
            "protocol": "TCP/HTTPS",
            "devname": "FW01"
        }
        
        normalized, unmapped = self.parser.normalize(parsed)
        
        assert normalized["source.ip"] == "10.0.0.5"
        assert normalized["destination.ip"] == "192.168.1.20"
        assert normalized["source.port"] == 443
        assert normalized["destination.port"] == 8443
        assert normalized["event.action"] == "deny"
        assert normalized["network.protocol"] == "TCP"
        assert normalized["observer.vendor"] == "Fortinet"


class TestPaloAltoParser:
    """Test Palo Alto parser."""
    
    def setup_method(self):
        self.parser = PaloAltoParser()
    
    def test_detect_paloalto_log(self):
        """Test detecting Palo Alto logs."""
        log = "1,2026/09/09 20:31:22,001001,TRAFFIC,drop,1,2026-09-09T20:31:22.123456-07:00"
        assert self.parser.detect(log) is True
    
    def test_detect_paloalto_traffic_keyword(self):
        """Test detecting Palo Alto by TRAFFIC keyword."""
        log = "some,fields,TRAFFIC,more fields"
        assert self.parser.detect(log) is True
    
    def test_reject_non_paloalto_log(self):
        """Test rejecting non-Palo Alto logs."""
        log = "date=2026-09-09 devname=FW01"
        assert self.parser.detect(log) is False
    
    def test_parse_paloalto_csv_log(self):
        """Test parsing Palo Alto CSV log."""
        # Simplified Palo Alto CSV (first few fields)
        log = "1,2026/09/09 20:31:22,001001,TRAFFIC,drop,1,2026-09-09T20:31:22Z,FW01,10.0.0.5,192.168.1.20"
        
        success, parsed, error = self.parser.parse(log)
        
        assert success is True
        # Check that some fields were extracted
        assert len(parsed) > 0
    
    def test_normalize_paloalto_log(self):
        """Test normalizing Palo Alto fields."""
        parsed = {
            "srcip": "10.0.0.5",
            "dstip": "192.168.1.20",
            "srcport": "443",
            "dstport": "8443",
            "action": "drop",
            "protocol": "6",  # TCP
            "hostname": "PA01"
        }
        
        normalized, unmapped = self.parser.normalize(parsed)
        
        assert normalized["source.ip"] == "10.0.0.5"
        assert normalized["destination.ip"] == "192.168.1.20"
        assert normalized["network.protocol"] == "tcp"
        assert normalized["observer.vendor"] == "Palo Alto"


class TestSyslogParser:
    """Test Syslog parser."""
    
    def setup_method(self):
        self.parser = SyslogParser()
    
    def test_detect_rfc5424_syslog(self):
        """Test detecting RFC 5424 syslog."""
        log = "2026-09-09T20:31:22.123456-07:00 fw01 firewall[1234]: message"
        assert self.parser.detect(log) is True
    
    def test_detect_rfc3164_syslog(self):
        """Test detecting RFC 3164 syslog."""
        log = "Sep 09 20:31:22 fw01 firewall[1234]: message"
        assert self.parser.detect(log) is True
    
    def test_reject_non_syslog_log(self):
        """Test rejecting non-syslog logs."""
        log = "devname=FW01 action=deny"
        assert self.parser.detect(log) is False
    
    def test_parse_rfc5424_syslog(self):
        """Test parsing RFC 5424 syslog."""
        log = "2026-09-09T20:31:22.123456-07:00 fw01 firewall[1234]: Connection denied from 10.0.0.5"
        
        success, parsed, error = self.parser.parse(log)
        
        assert success is True
        assert parsed["hostname"] == "fw01"
        assert parsed["program"] == "firewall"
        assert parsed["pid"] == "1234"
        assert "Connection denied" in parsed["message"]
    
    def test_parse_rfc3164_syslog(self):
        """Test parsing RFC 3164 syslog."""
        log = "Sep 09 20:31:22 fw01 firewall[1234]: Connection denied"
        
        success, parsed, error = self.parser.parse(log)
        
        assert success is True
        assert parsed["hostname"] == "fw01"
        assert parsed["program"] == "firewall"
        assert parsed["pid"] == "1234"


class TestJSONParser:
    """Test JSON parser."""
    
    def setup_method(self):
        self.parser = JSONParser()
    
    def test_detect_valid_json(self):
        """Test detecting valid JSON."""
        log = '{"timestamp": "2026-09-09T20:31:22", "message": "test"}'
        assert self.parser.detect(log) is True
    
    def test_reject_invalid_json(self):
        """Test rejecting invalid JSON."""
        log = '{invalid json}'
        assert self.parser.detect(log) is False
    
    def test_parse_json_log(self):
        """Test parsing JSON log."""
        log = '{"src_ip": "10.0.0.5", "dst_ip": "192.168.1.20", "action": "deny"}'
        
        success, parsed, error = self.parser.parse(log)
        
        assert success is True
        assert parsed["src_ip"] == "10.0.0.5"
        assert parsed["dst_ip"] == "192.168.1.20"
    
    def test_normalize_json_various_field_names(self):
        """Test that JSON parser handles various field name conventions."""
        test_cases = [
            ({"src_ip": "10.0.0.5"}, "src_ip"),
            ({"srcip": "10.0.0.5"}, "srcip"),
            ({"source_ip": "10.0.0.5"}, "source_ip"),
            ({"sourceIp": "10.0.0.5"}, "sourceIp"),
            ({"source.ip": "10.0.0.5"}, "source.ip"),
        ]
        
        for parsed, key in test_cases:
            normalized, _ = self.parser.normalize(parsed)
            assert normalized.get("source.ip") == "10.0.0.5", f"Failed for key: {key}"
    
    def test_normalize_json_destination(self):
        """Test normalizing destination fields."""
        parsed = {
            "dst_ip": "192.168.1.20",
            "dstport": 8443,
            "destination_ip": "override",  # This should be overridden
        }
        
        normalized, _ = self.parser.normalize(parsed)
        
        # dst_ip is checked first, so it should win
        assert normalized.get("destination.ip") == "192.168.1.20"
        assert normalized.get("destination.port") == 8443
    
    def test_normalize_json_complex_log(self):
        """Test normalizing complex JSON log."""
        log = json.dumps({
            "timestamp": "2026-09-09T20:31:22Z",
            "src_ip": "10.0.0.5",
            "src_port": 443,
            "dst_ip": "192.168.1.20",
            "dst_port": 8443,
            "protocol": "TCP",
            "action": "deny",
            "severity": "high",
            "category": "network",
            "hostname": "fw01",
            "vendor": "Fortinet",
            "custom_field": "custom_value"
        })
        
        success, parsed, error = self.parser.parse(log)
        assert success is True
        
        normalized, unmapped = self.parser.normalize(parsed)
        
        # Check normalized fields
        assert normalized["source.ip"] == "10.0.0.5"
        assert normalized["source.port"] == 443
        assert normalized["destination.ip"] == "192.168.1.20"
        assert normalized["destination.port"] == 8443
        assert normalized["event.action"] == "deny"
        
        # Check that custom field is unmapped
        assert unmapped["custom_field"] == "custom_value"


class TestParserIntegration:
    """Integration tests for parsers working with real logs."""
    
    def test_full_fortinet_workflow(self):
        """Test complete workflow with Fortinet log."""
        parser = FortinetParser()
        
        # Full Fortinet log
        log = 'date=2026-09-09 time=20:31:22 devname="FW01" srcip=10.0.0.5 dstip=192.168.1.20 srcport=443 dstport=8443 action=deny protocol="TCP/HTTPS" type=traffic'
        
        # Detect
        assert parser.detect(log) is True
        
        # Parse
        success, parsed, error = parser.parse(log)
        assert success is True
        
        # Normalize
        normalized, unmapped = parser.normalize(parsed)
        
        # Verify workflow
        assert normalized["source.ip"] == "10.0.0.5"
        assert normalized["destination.ip"] == "192.168.1.20"
        assert normalized["event.action"] == "deny"
        assert "devname" not in unmapped  # devname is mapped to observer.hostname
        assert normalized["observer.hostname"] == "FW01"
        assert "date" in unmapped  # date/time are unmapped
        assert "time" in unmapped
    
    def test_full_json_workflow(self):
        """Test complete workflow with JSON log."""
        parser = JSONParser()
        
        # Full JSON log
        log = json.dumps({
            "timestamp": "2026-09-09T20:31:22Z",
            "source_ip": "10.0.0.5",
            "source_port": 443,
            "destination_ip": "192.168.1.20",
            "destination_port": 8443,
            "action": "deny",
            "extra_field": "extra_value"
        })
        
        # Detect
        assert parser.detect(log) is True
        
        # Parse
        success, parsed, error = parser.parse(log)
        assert success is True
        
        # Normalize
        normalized, unmapped = parser.normalize(parsed)
        
        # Verify workflow
        assert normalized["source.ip"] == "10.0.0.5"
        assert normalized["destination.ip"] == "192.168.1.20"
        assert unmapped["extra_field"] == "extra_value"
