"""
Generic JSON Log Parser.

Parses structured JSON logs from any source.

JSON is the most reliable format for parsing because it's machine-readable
and self-describing.

Sample JSON log:
{
  "timestamp": "2026-09-09T20:31:22Z",
  "source_ip": "10.0.0.5",
  "source_port": 443,
  "destination_ip": "192.168.1.20",
  "destination_port": 8443,
  "action": "deny",
  "severity": "high"
}

JSON is tried first in detection order because it's highest confidence.
"""

import json
import logging
from typing import Dict, Any, Tuple
from backend.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class JSONParser(BaseParser):
    """Parser for structured JSON logs."""
    
    def __init__(self):
        super().__init__(name="json", version="1.0")
    
    def detect(self, log: str) -> bool:
        """
        Detect JSON format by attempting to parse as JSON.
        
        JSON is tried first in detection order - it's the most reliable.
        """
        try:
            json.loads(log)
            return True
        except (json.JSONDecodeError, ValueError, TypeError):
            return False
    
    def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Parse JSON log.
        
        Simply loads the JSON string and returns the parsed dictionary.
        """
        try:
            data = json.loads(log)
            if not isinstance(data, dict):
                # If JSON is not a dict (e.g., array), wrap it
                data = {"data": data}
            return (True, data, "")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parser error: {e}")
            return (False, {}, str(e))
        except Exception as e:
            logger.error(f"JSON parser unexpected error: {e}")
            return (False, {}, str(e))
    
    def normalize(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Map JSON fields to canonical schema.
        
        Handles various common JSON field naming conventions:
        - src_ip, srcip, source_ip, sourceIp, etc.
        - dst_ip, dstip, destination_ip, destinationIp, etc.
        - src_port, srcport, source_port, sourcePort, etc.
        - dst_port, dstport, destination_port, destinationPort, etc.
        """
        normalized = {}
        unmapped = {}
        
        # Make a copy so we can modify it
        remaining = parsed.copy()
        
        # ===== SOURCE IP MAPPING =====
        src_ip_keys = ["src_ip", "srcip", "source_ip", "sourceip", "source.ip",
                          "src", "source", "client_ip", "clientip", "client.ip",
                          "sourceIp", "srcIp"]
        for key in src_ip_keys:
            if key in remaining:
                normalized["source.ip"] = remaining.pop(key)
                break
        
        # ===== DESTINATION IP MAPPING =====
        dst_ip_keys = ["dst_ip", "dstip", "destination_ip", "destinationip",
                          "destination.ip", "dst", "destination", "server_ip",
                          "serverip", "server.ip", "target_ip", "targetip",
                          "destinationIp", "dstIp"]
        for key in dst_ip_keys:
            if key in remaining:
                normalized["destination.ip"] = remaining.pop(key)
                break
        
        # ===== SOURCE PORT MAPPING =====
        src_port_keys = ["src_port", "srcport", "source_port", "sourceport",
                        "source.port", "sport", "sourcePort", "srcPort"]
        for key in src_port_keys:
            if key in remaining:
                try:
                    normalized["source.port"] = int(remaining.pop(key))
                except (ValueError, TypeError):
                    pass
                break
        
        # ===== DESTINATION PORT MAPPING =====
        dst_port_keys = ["dst_port", "dstport", "destination_port", "destinationport",
                        "destination.port", "dport", "port", "destinationPort", "dstPort"]
        for key in dst_port_keys:
            if key in remaining:
                try:
                    normalized["destination.port"] = int(remaining.pop(key))
                except (ValueError, TypeError):
                    pass
                break
        
        # ===== PROTOCOL MAPPING =====
        proto_keys = ["protocol", "proto", "network_protocol", "networkprotocol"]
        for key in proto_keys:
            if key in remaining:
                normalized["network.protocol"] = remaining.pop(key)
                break
        
        # ===== ACTION MAPPING =====
        action_keys = ["action", "event_action", "eventaction", "event.action"]
        for key in action_keys:
            if key in remaining:
                normalized["event.action"] = remaining.pop(key)
                break
        
        # ===== SEVERITY MAPPING =====
        severity_keys = ["severity", "level", "severity_level", "event_severity", "eventseverity"]
        for key in severity_keys:
            if key in remaining:
                normalized["event.severity"] = remaining.pop(key)
                break
        
        # ===== CATEGORY MAPPING =====
        category_keys = ["category", "event_category", "eventcategory", "event.category", "type"]
        for key in category_keys:
            if key in remaining:
                normalized["event.category"] = remaining.pop(key)
                break
        
        # ===== TIMESTAMP MAPPING =====
        ts_keys = ["timestamp", "time", "datetime", "date", "ts", "@timestamp"]
        for key in ts_keys:
            if key in remaining:
                normalized["timestamp"] = remaining.pop(key)
                break
        
        # ===== HOSTNAME MAPPING =====
        hostname_keys = ["hostname", "host", "server_name", "servername",
                        "device_name", "devicename", "name"]
        for key in hostname_keys:
            if key in remaining:
                normalized["observer.hostname"] = remaining.pop(key)
                break
        
        # ===== VENDOR MAPPING =====
        vendor_keys = ["vendor", "source_vendor", "sourcevendor", "device_vendor"]
        for key in vendor_keys:
            if key in remaining:
                normalized["observer.vendor"] = remaining.pop(key)
                break
        
        # ===== PRODUCT MAPPING =====
        product_keys = ["product", "device_type", "devicetype", "appliance"]
        for key in product_keys:
            if key in remaining:
                normalized["observer.product"] = remaining.pop(key)
                break
        
        # Everything else is unmapped
        unmapped = remaining
        
        return (normalized, unmapped)
    
    def get_info(self) -> Dict[str, Any]:
        """Get parser metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "vendor": "Generic",
            "product": "JSON",
            "description": "Generic Structured JSON Log Parser"
        }
