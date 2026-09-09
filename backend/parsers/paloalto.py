"""
Palo Alto Networks Log Parser.

Parses logs from Palo Alto Networks security appliances.

Sample Palo Alto log (comma-separated fields):
1,2026/09/09 20:31:22,001001,TRAFFIC,drop,1,2026-09-09T20:31:22.123456-07:00,
FROOTP01,10.0.0.5,192.168.1.20,0.0.0.0,0.0.0.0,allow-internet,,,high-net-risk,
client-to-server,tcp,192,deny,443,8443,0,1,10,from-internal,Internal,
53,0,0,,0,,0,,,,,,,,,N/A,0,0,0,,0,0,,

Palo Alto uses both CSV and JSON formats. This parser handles CSV.
"""

import logging
import csv
from io import StringIO
from typing import Dict, Any, Tuple
from backend.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class PaloAltoParser(BaseParser):
    """Parser for Palo Alto Networks logs."""
    
    def __init__(self):
        super().__init__(name="paloalto", version="1.0")
        # Palo Alto CSV field order (standard format)
        self.csv_fields = [
            "type", "timestamp", "serial", "log_subtype", "action", "future_use",
            "receive_time", "hostname", "srcip", "dstip", "natsrcip", "natdstip",
            "rule", "srcuser", "dstuser", "app", "vsys", "from_zone", "to_zone",
            "inbound_if", "outbound_if", "logid", "time_generated", "packets",
            "bytes", "natsrcport", "natdstport", "srcport", "dstport", "flags",
            "protocol", "action2", "srcloc", "dstloc", "future_use2", "packets_sent",
            "packets_received", "session_duration", "reason", "dev_group_hierarchy1",
            "dev_group_hierarchy2", "dev_group_hierarchy3", "dev_group_hierarchy4",
            "vsys_name", "dvcname", "category", "future_use3", "sequence_number"
        ]
    
    def detect(self, log: str) -> bool:
        """
        Detect Palo Alto logs.
        
        Palo Alto logs typically start with 1, (log version).
        Or contain TRAFFIC, THREAT, etc. log types.
        """
        # Check for Palo Alto log format markers
        if log.startswith("1,"):
            return True
        if any(keyword in log for keyword in ["TRAFFIC,", "THREAT,", "CONFIG,"]):
            return True
        return False
    
    def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Parse Palo Alto CSV log format.
        """
        try:
            parsed = {}
            
            # Try to parse as CSV
            reader = csv.reader(StringIO(log))
            row = next(reader)
            
            # Map to field names (only if we have enough fields)
            if len(row) >= len(self.csv_fields):
                for i, field_name in enumerate(self.csv_fields):
                    if i < len(row):
                        parsed[field_name] = row[i].strip()
            else:
                # Fewer fields than expected, map what we can
                for i, val in enumerate(row):
                    if i < len(self.csv_fields):
                        parsed[self.csv_fields[i]] = val.strip()
                    else:
                        parsed[f"field_{i}"] = val.strip()
            
            return (True, parsed, "")
        except Exception as e:
            logger.error(f"Palo Alto parser error: {e}")
            return (False, {}, str(e))
    
    def normalize(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Map Palo Alto fields to canonical schema."""
        normalized = {}
        unmapped = {}
        
        # Map source
        if "srcip" in parsed:
            normalized["source.ip"] = parsed.pop("srcip")
        if "srcport" in parsed:
            try:
                normalized["source.port"] = int(parsed.pop("srcport"))
            except:
                pass
        
        # Map destination
        if "dstip" in parsed:
            normalized["destination.ip"] = parsed.pop("dstip")
        if "dstport" in parsed:
            try:
                normalized["destination.port"] = int(parsed.pop("dstport"))
            except:
                pass
        
        # Map protocol
        if "protocol" in parsed:
            proto_map = {"1": "icmp", "6": "tcp", "17": "udp"}
            proto = parsed.pop("protocol")
            normalized["network.protocol"] = proto_map.get(proto, proto)
        
        # Map action
        if "action" in parsed:
            normalized["event.action"] = parsed.pop("action")
        
        # Map category
        if "category" in parsed:
            normalized["event.category"] = parsed.pop("category")
        
        # Map severity
        if "severity" in parsed:
            normalized["event.severity"] = parsed.pop("severity")
        
        # Add observer info
        normalized["observer.vendor"] = "Palo Alto"
        normalized["observer.product"] = "PA-Series"
        if "hostname" in parsed:
            normalized["observer.hostname"] = parsed.pop("hostname")
        
        # Everything else is unmapped
        unmapped = parsed
        
        return (normalized, unmapped)
    
    def get_info(self) -> Dict[str, Any]:
        """Get parser metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "vendor": "Palo Alto",
            "product": "PA-Series",
            "description": "Palo Alto Networks Security Appliance Log Parser"
        }
