"""
Tests for Source Detector.

Verifies that the detector correctly identifies log sources.
"""

import pytest
from backend.core.detector import SourceDetector
from backend.parsers.registry import get_registry, reset_registry
from backend.parsers.cisco_asa import CiscoASAParser
from backend.parsers.fortinet import FortinetParser
from backend.parsers.paloalto import PaloAltoParser
from backend.parsers.syslog import SyslogParser
from backend.parsers.json_parser import JSONParser


@pytest.fixture
def detector():
    """Set up detector with all parsers registered."""
    reset_registry()
    registry = get_registry()
    
    # Register all parsers
    registry.register(JSONParser())
    registry.register(CiscoASAParser())
    registry.register(FortinetParser())
    registry.register(PaloAltoParser())
    registry.register(SyslogParser())
    
    return SourceDetector()


class TestSourceDetection:
    """Test source detection for each log format."""
    
    def test_detect_fortinet_log(self, detector):
        """Test detecting Fortinet logs."""
        log = "date=2026-09-09 devname=FW01 srcip=10.0.0.5 dstip=192.168.1.20"
        source = detector.detect(log)
        assert source == "fortinet"
    
    def test_detect_cisco_log(self, detector):
        """Test detecting Cisco ASA logs."""
        log = "%ASA-6-302013: Built inbound TCP connection 12345 for outside:10.0.0.5/443 to inside:192.168.1.20/8443"
        source = detector.detect(log)
        assert source == "cisco"
    
    def test_detect_json_log(self, detector):
        """Test detecting JSON logs."""
        log = '{"timestamp": "2026-09-09T20:31:22", "src_ip": "10.0.0.5", "dst_ip": "192.168.1.20"}'
        source = detector.detect(log)
        assert source == "json"
    
    def test_detect_syslog_rfc5424(self, detector):
        """Test detecting RFC 5424 syslog logs."""
        log = "2026-09-09T20:31:22.123456-07:00 fw01 firewall[1234]: Connection denied"
        source = detector.detect(log)
        assert source == "syslog"
    
    def test_detect_syslog_rfc3164(self, detector):
        """Test detecting RFC 3164 syslog logs."""
        log = "Sep 09 20:31:22 fw01 firewall[1234]: Connection denied"
        source = detector.detect(log)
        assert source == "syslog"
    
    def test_detect_unknown_source(self, detector):
        """Test that unknown logs return 'unknown'."""
        log = "This is some random text that doesn't match any format"
        source = detector.detect(log)
        assert source == "unknown"
    
    def test_detect_empty_log(self, detector):
        """Test that empty log returns 'unknown'."""
        source = detector.detect("")
        assert source == "unknown"
    
    def test_detect_none_log(self, detector):
        """Test that None returns 'unknown'."""
        source = detector.detect(None)
        assert source == "unknown"
    
    def test_detect_whitespace_only(self, detector):
        """Test that whitespace-only log returns 'unknown'."""
        source = detector.detect("   \n\t  ")
        assert source == "unknown"
    
    def test_detect_with_confidence(self, detector):
        """Test confidence scoring."""
        fortinet_log = "date=2026-09-09 devname=FW01 srcip=10.0.0.5 dstip=192.168.1.20"
        source, conf = detector.detect_with_confidence(fortinet_log)
        
        assert source == "fortinet"
        assert conf == 1.0
    
    def test_detect_unknown_with_confidence(self, detector):
        """Test confidence for unknown source."""
        source, conf = detector.detect_with_confidence("unknown text")
        
        assert source == "unknown"
        assert conf == 0.0
    
    def test_list_detectable_sources(self, detector):
        """Test listing all detectable sources."""
        sources = detector.list_detectable_sources()
        
        # Should have JSON, Cisco, Fortinet, Palo Alto, Syslog
        assert "json" in sources
        assert "cisco" in sources
        assert "fortinet" in sources
        assert "paloalto" in sources
        assert "syslog" in sources
    
    def test_detection_order_respects_priority(self, detector):
        """Test that JSON is tried before other parsers."""
        # JSON is first in priority, so a valid JSON should always be detected as JSON
        # even if it could potentially match other patterns
        json_log = '{"message": "this contains devname=FW01"}'
        source = detector.detect(json_log)
        
        # Should be detected as JSON (highest priority), not fortinet
        assert source == "json"
