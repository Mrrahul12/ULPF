"""
Base parser interface for ULPF.

All parsers must implement this abstract base class.
This ensures vendor-specific parsing logic stays isolated from the core pipeline.

Key principle:
The pipeline should NOT contain vendor-specific if/else logic.
Instead, it delegates to parser implementations via this interface.

This design enables:
- Plug-and-play parser registration
- Future AI-generated parser integration
- Clean separation of concerns
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from datetime import datetime


class BaseParser(ABC):
    """
    Abstract base class that all vendor parsers must inherit from.
    
    A parser's job is to:
    1. DETECT: Identify if a log belongs to its vendor
    2. PARSE: Extract vendor-specific fields
    3. NORMALIZE: Map vendor fields → canonical fields
    
    Example flow:
    
    Raw input: "date=2026-09-09 time=20:31:22 devname=FW01 srcip=10.0.0.5 ..."
                      ↓
                FortietParser.detect()  → True (recognizes devname=, srcip=)
                      ↓
                FortinetParser.parse()  → {"date": "...", "devname": "FW01", ...}
                      ↓
                FortinetParser.normalize() → {"source.ip": "10.0.0.5", ...}
                      ↓
                Return to pipeline for validation/provenance
    """
    
    def __init__(self, name: str, version: str = "1.0"):
        """
        Initialize the parser.
        
        Args:
            name: Parser identifier (e.g., 'cisco', 'fortinet')
            version: Parser version for provenance tracking
        """
        self.name = name
        self.version = version
    
    @abstractmethod
    def detect(self, log: str) -> bool:
        """
        Detect if this log belongs to this parser's vendor format.
        
        Implementation notes:
        - Must NOT raise exceptions; return True/False only
        - Should be fast (detection is called for every log)
        - Can use fingerprinting, regex patterns, or schema validation
        - Should prefer high-confidence patterns
        
        Args:
            log: Raw log message as string
            
        Returns:
            True if this parser should handle the log, False otherwise
            
        Example (Fortinet):
            >>> parser = FortinetParser()
            >>> parser.detect("date=2026-09-09 devname=FW01 srcip=10.0.0.5")
            True
            >>> parser.detect("2026-09-09 SomeOtherLog")
            False
        """
        pass
    
    @abstractmethod
    def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Extract vendor-specific fields from the log.
        
        This extracts raw fields as they appear in the vendor format.
        It does NOT normalize them yet.
        
        Implementation notes:
        - Return parsed fields as a dictionary
        - Include ALL fields extracted, even if they don't map canonically
        - Timestamps should be extracted as-is (preserving vendor format)
        - Numeric fields can be strings (normalizer will convert types)
        - If parsing fails, return (False, {}, error_message)
        
        Args:
            log: Raw log message as string
            
        Returns:
            Tuple of (success: bool, parsed_dict: dict, error_message: str)
            - success: True if parsing succeeded
            - parsed_dict: Extracted vendor-specific fields
            - error_message: Empty string if success, error description if failed
            
        Example (Fortinet):
            >>> parser = FortinetParser()
            >>> success, data, err = parser.parse("date=2026-09-09 devname=FW01 srcip=10.0.0.5")
            >>> success
            True
            >>> data
            {
                "date": "2026-09-09",
                "devname": "FW01",
                "srcip": "10.0.0.5"
            }
        """
        pass
    
    @abstractmethod
    def normalize(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Map vendor-specific fields to canonical representation.
        
        This is where "srcip" → "source.ip", "dstip" → "destination.ip", etc.
        
        Implementation notes:
        - Take parsed_dict from parse()
        - Apply vendor-specific mapping rules
        - Convert types as needed (string port → int, timestamp → datetime)
        - Unmapped fields should be returned separately, NOT discarded
        - If a required field is missing, note it in error handling
        
        Returns:
            Tuple of (normalized_dict, unmapped_dict)
            - normalized_dict: Canonical field names with normalized values
            - unmapped_dict: Fields that don't have canonical mappings
            
        Example (Fortinet):
            Input (from parse()):
            {
                "date": "2026-09-09",
                "time": "20:31:22",
                "devname": "FW01",
                "srcip": "10.0.0.5",
                "dstip": "192.168.1.20",
                "srcport": "443",
                "dstport": "8443",
                "action": "deny"
            }
            
            Output normalized_dict:
            {
                "timestamp": datetime(2026, 9, 9, 20, 31, 22),
                "source.ip": "10.0.0.5",
                "destination.ip": "192.168.1.20",
                "source.port": 443,
                "destination.port": 8443,
                "event.action": "deny",
                "observer.vendor": "Fortinet",
                "observer.product": "FortiGate"
            }
            
            Output unmapped_dict:
            {
                "date": "2026-09-09",
                "time": "20:31:22",
                "devname": "FW01"
            }
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get parser metadata for listing/debugging.
        
        Returns:
            Dictionary with parser info
            
        Example:
            >>> parser.get_info()
            {
                "name": "fortinet",
                "version": "1.0",
                "vendor": "Fortinet",
                "product": "FortiGate",
                "description": "Parser for Fortinet FortiGate firewall logs"
            }
        """
        return {
            "name": self.name,
            "version": self.version
        }
