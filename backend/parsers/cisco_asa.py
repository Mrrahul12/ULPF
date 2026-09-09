"""
Cisco ASA Firewall Log Parser.

Parses firewall logs from Cisco ASA devices.

Sample Cisco ASA log:
%ASA-6-302013: Built inbound TCP connection 12345 for outside:192.168.1.100/80 
(192.168.1.100/80) to inside:10.0.0.5/443 (10.0.0.5/443)

This is a simplified parser for demonstration.
Real-world Cisco parsing would be more complex.
"""

import re
import logging
from typing import Dict, Any, Tuple
from datetime import datetime
from backend.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class CiscoASAParser(BaseParser):
    """Parser for Cisco ASA firewall logs."""
    
    def __init__(self):
        super().__init__(name="cisco", version="1.0")
    
    def detect(self, log: str) -> bool:
        """
        Detect Cisco ASA logs by looking for %ASA- pattern.
        
        This is the most distinctive pattern in Cisco ASA logs.
        """
        return "%ASA-" in log
    
    def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Parse Cisco ASA log.
        
        Extracts:
        - Severity level (6 in %ASA-6-)
        - Message code (302013)
        - Description
        - Any IP/port information
        """
        try:
            parsed = {"raw_log": log}
            
            # Extract severity and message ID
            # Pattern: %ASA-SEVERITY-MSGID: Description
            match = re.match(r'%ASA-(\d+)-(\d+):\s*(.*)', log)
            if match:
                parsed["severity"] = match.group(1)
                parsed["message_id"] = match.group(2)
                parsed["description"] = match.group(3)
            
            # Try to extract IP addresses from description
            ip_pattern = r'(\d+\.\d+\.\d+\.\d+)'
            ips = re.findall(ip_pattern, log)
            if ips:
                parsed["source_ip"] = ips[0]
                if len(ips) > 1:
                    parsed["destination_ip"] = ips[1]
            
            # Try to extract ports
            port_pattern = r'/(\d+)\s'
            ports = re.findall(port_pattern, log)
            if ports:
                parsed["source_port"] = ports[0]
                if len(ports) > 1:
                    parsed["destination_port"] = ports[1]
            
            return (True, parsed, "")
        except Exception as e:
            logger.error(f"Cisco parser error: {e}")
            return (False, {}, str(e))
    
    def normalize(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Map Cisco fields to canonical."""
        normalized = {}
        unmapped = {}
        
        # Map severity to event severity
        severity_map = {
            "0": "emergency", "1": "alert", "2": "critical", "3": "error",
            "4": "warning", "5": "notice", "6": "info", "7": "debug"
        }
        if "severity" in parsed:
            normalized["event.severity"] = severity_map.get(parsed["severity"], "unknown")
        
        # Map IP addresses
        if "source_ip" in parsed:
            normalized["source.ip"] = parsed.pop("source_ip")
        if "destination_ip" in parsed:
            normalized["destination.ip"] = parsed.pop("destination_ip")
        
        # Map ports
        if "source_port" in parsed:
            try:
                normalized["source.port"] = int(parsed.pop("source_port"))
            except:
                pass
        if "destination_port" in parsed:
            try:
                normalized["destination.port"] = int(parsed.pop("destination_port"))
            except:
                pass
        
        # Add observer info
        normalized["observer.vendor"] = "Cisco"
        normalized["observer.product"] = "ASA"
        
        # Unmapped fields
        for key in ["severity", "message_id", "description", "raw_log"]:
            if key in parsed:
                unmapped[key] = parsed.pop(key)
        unmapped.update(parsed)
        
        return (normalized, unmapped)
    
    def get_info(self) -> Dict[str, Any]:
        """Get parser metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "vendor": "Cisco",
            "product": "ASA",
            "description": "Cisco ASA Firewall Log Parser"
        }
