"""
Generic Syslog Log Parser.

Parses standard Syslog format (RFC 3164, RFC 5424).

Sample Syslog logs:
RFC 3164: Jan 12 06:05:24 192.168.1.1 sshd[1234]: Failed password for user

RFC 5424: 2026-09-09T20:31:22.123456-07:00 hostname app-name[pid]: message

Syslog is the fallback parser - used when more specific parsers don't match.
"""

import re
import logging
from datetime import datetime
from typing import Dict, Any, Tuple
from backend.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class SyslogParser(BaseParser):
    """Parser for generic Syslog format."""
    
    def __init__(self):
        super().__init__(name="syslog", version="1.0")
    
    def detect(self, log: str) -> bool:
        """
        Detect Syslog format.
        
        Syslog logs typically follow RFC 3164 or RFC 5424 format.
        Look for timestamp patterns and syslog structure.
        
        Note: This is a low-confidence detection (last resort).
        More specific parsers (Cisco, Fortinet, etc.) take priority.
        """
        # Look for syslog-style timestamp
        # RFC 3164: Jan 12 06:05:24
        if re.match(r'^\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}', log):
            return True
        
        # RFC 5424: 2026-09-09T20:31:22Z
        if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', log):
            return True
        
        return False
    
    def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Parse Syslog log.
        
        Extracts timestamp, hostname, program, pid, and message.
        """
        try:
            parsed = {}
            
            # Try RFC 5424 format first (ISO 8601 timestamp)
            # Pattern: 2026-09-09T20:31:22.123456-07:00 hostname app[pid]: message
            rfc5424 = re.match(
                r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s]*)\s+(\S+)\s+([^\[\s]+)(?:\[(\d+)\])?\s*:\s*(.*)$',
                log
            )
            
            if rfc5424:
                parsed["timestamp"] = rfc5424.group(1)
                parsed["hostname"] = rfc5424.group(2)
                parsed["program"] = rfc5424.group(3)
                parsed["pid"] = rfc5424.group(4) or ""
                parsed["message"] = rfc5424.group(5)
                parsed["format"] = "RFC5424"
                return (True, parsed, "")
            
            # Try RFC 3164 format (BSD format)
            # Pattern: Jan 12 06:05:24 hostname program[pid]: message
            rfc3164 = re.match(
                r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^\[\s]+)(?:\[(\d+)\])?\s*:\s*(.*)$',
                log
            )
            
            if rfc3164:
                parsed["timestamp"] = rfc3164.group(1)
                parsed["hostname"] = rfc3164.group(2)
                parsed["program"] = rfc3164.group(3)
                parsed["pid"] = rfc3164.group(4) or ""
                parsed["message"] = rfc3164.group(5)
                parsed["format"] = "RFC3164"
                return (True, parsed, "")
            
            # If we get here, try a loose format
            # Just extract what looks like timestamp and message
            parts = log.split(maxsplit=3)
            if len(parts) >= 3:
                parsed["timestamp"] = parts[0]
                parsed["hostname"] = parts[1]
                parsed["message"] = " ".join(parts[2:])
                parsed["format"] = "LOOSE"
                return (True, parsed, "")
            
            # Last resort: store entire log as message
            parsed["message"] = log
            parsed["format"] = "UNKNOWN"
            return (True, parsed, "")
        
        except Exception as e:
            logger.error(f"Syslog parser error: {e}")
            return (False, {}, str(e))
    
    def normalize(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Map Syslog fields to canonical schema."""
        normalized = {}
        unmapped = {}
        
        # Timestamp
        if "timestamp" in parsed:
            normalized["timestamp"] = parsed.pop("timestamp")
        
        # Hostname becomes observer hostname
        if "hostname" in parsed:
            normalized["observer.hostname"] = parsed.pop("hostname")
        
        # Try to extract IP from message
        import re
        message = parsed.get("message", "")
        ip_pattern = r'(\d+\.\d+\.\d+\.\d+)'
        ips = re.findall(ip_pattern, message)
        
        if ips:
            if len(ips) >= 1:
                normalized["source.ip"] = ips[0]
            if len(ips) >= 2:
                normalized["destination.ip"] = ips[1]
        
        # Program name as category
        if "program" in parsed:
            parsed["program"] = parsed.pop("program")
            # Can be used to infer category
        
        # Everything else is unmapped
        unmapped = parsed
        
        return (normalized, unmapped)
    
    def get_info(self) -> Dict[str, Any]:
        """Get parser metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "vendor": "Generic",
            "product": "Syslog",
            "description": "Generic Syslog Log Parser (RFC 3164 / RFC 5424)"
        }
