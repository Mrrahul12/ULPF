"""
Fortinet FortiGate Firewall Log Parser.

Parses logs from Fortinet FortiGate security appliances.

Sample Fortinet log (key=value format):
date=2026-09-09 time=20:31:22 devname=FW01 devid=FGXXXXXXXX logid=0000000013
type=traffic subtype=allowed policyid=17 policyname="Allow-Traffic"
srcip=10.0.0.5 srcname=client.example.com srcport=443 srccountry=United States
dstip=192.168.1.20 dstname=server.example.com dstport=8443 dstcountry=United States
protocol=TCP/HTTPS action=accept duration=1234 sentbyte=5000 rcvdbyte=10000

Fortinet logs are predominantly key=value pairs, making parsing straightforward.
"""

import logging
from typing import Dict, Any, Tuple
from backend.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class FortinetParser(BaseParser):
    """Parser for Fortinet FortiGate logs."""
    
    def __init__(self):
        super().__init__(name="fortinet", version="1.0")
    
    def detect(self, log: str) -> bool:
        """
        Detect Fortinet logs by looking for devname= and srcip= patterns.
        
        Fortinet uses key=value format with distinctive fields like devname.
        """
        return "devname=" in log and "srcip=" in log
    
    def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Parse Fortinet key=value log format.
        
        Splits on whitespace and extracts key=value pairs.
        Handles quoted values like policy="allow-all".
        """
        try:
            parsed = {}
            
            # Parse key=value pairs
            # Handle quoted values like "policy name"
            i = 0
            while i < len(log):
                # Skip whitespace
                while i < len(log) and log[i].isspace():
                    i += 1
                
                if i >= len(log):
                    break
                
                # Find key=
                eq_pos = log.find('=', i)
                if eq_pos == -1:
                    break
                
                key = log[i:eq_pos].strip()
                i = eq_pos + 1
                
                # Extract value (handle quotes)
                if i < len(log) and log[i] == '"':
                    # Quoted value
                    i += 1
                    end_quote = log.find('"', i)
                    if end_quote == -1:
                        value = log[i:].strip()
                        i = len(log)
                    else:
                        value = log[i:end_quote]
                        i = end_quote + 1
                else:
                    # Unquoted value (until whitespace)
                    end = i
                    while end < len(log) and not log[end].isspace():
                        end += 1
                    value = log[i:end]
                    i = end
                
                if key:
                    parsed[key] = value.strip('"')
            
            return (True, parsed, "")
        except Exception as e:
            logger.error(f"Fortinet parser error: {e}")
            return (False, {}, str(e))
    
    def normalize(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Map Fortinet fields to canonical schema."""
        normalized = {}
        unmapped = {}
        
        # Map source IP/port
        if "srcip" in parsed:
            normalized["source.ip"] = parsed.pop("srcip")
        if "srcport" in parsed:
            try:
                normalized["source.port"] = int(parsed.pop("srcport"))
            except:
                pass
        if "srcname" in parsed:
            normalized["source.hostname"] = parsed.pop("srcname")
        
        # Map destination IP/port
        if "dstip" in parsed:
            normalized["destination.ip"] = parsed.pop("dstip")
        if "dstport" in parsed:
            try:
                normalized["destination.port"] = int(parsed.pop("dstport"))
            except:
                pass
        if "dstname" in parsed:
            normalized["destination.hostname"] = parsed.pop("dstname")
        
        # Map protocol
        if "protocol" in parsed:
            proto = parsed.pop("protocol")
            # Extract protocol name (e.g., "TCP/HTTPS" -> "TCP")
            normalized["network.protocol"] = proto.split("/")[0]
        
        # Map action
        if "action" in parsed:
            normalized["event.action"] = parsed.pop("action")
        
        # Map severity from log level if available
        if "type" in parsed:
            log_type = parsed.pop("type")
            if log_type == "traffic":
                normalized["event.category"] = "network"
            else:
                normalized["event.category"] = log_type
        
        # Add observer info
        normalized["observer.vendor"] = "Fortinet"
        normalized["observer.product"] = "FortiGate"
        if "devname" in parsed:
            normalized["observer.hostname"] = parsed.pop("devname")
        
        # Everything else is unmapped
        unmapped = parsed
        
        return (normalized, unmapped)
    
    def get_info(self) -> Dict[str, Any]:
        """Get parser metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "vendor": "Fortinet",
            "product": "FortiGate",
            "description": "Fortinet FortiGate Security Appliance Log Parser"
        }
