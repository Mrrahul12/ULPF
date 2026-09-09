"""
Source Detector for ULPF.

Determines which vendor/source a log comes from by trying each parser's
detect() method in priority order.

WHAT?
A detector identifies the source of a log using parser fingerprints.

WHY?
First step in the pipeline: we need to know which parser to use.
Detection order matters: JSON is more reliable than syslog patterns.

HOW?
1. Load PARSER_DETECTION_ORDER from config (priority list)
2. For each parser in order:
   - Try parser.detect(log)
   - If True, return that parser's name
3. If no match, return "unknown"
"""

import logging
from typing import Optional
from backend.config import PARSER_DETECTION_ORDER
from backend.parsers.registry import get_registry

logger = logging.getLogger(__name__)


class SourceDetector:
    """
    Detects the source/vendor of a log using registered parsers.
    
    Uses deterministic fingerprinting based on parser detection order.
    """
    
    def __init__(self):
        """Initialize the detector with the global registry."""
        self.registry = get_registry()
    
    def detect(self, log: str) -> str:
        """
        Detect the source type of a log.
        
        Tries each parser in PARSER_DETECTION_ORDER until one matches.
        
        Args:
            log: Raw log message
            
        Returns:
            Source type name ('cisco', 'fortinet', 'json', etc.) or 'unknown'
            
        Example:
            >>> detector = SourceDetector()
            >>> source = detector.detect("date=2026-09-09 devname=FW01 srcip=10.0.0.5")
            >>> source
            'fortinet'
        """
        if not log or not isinstance(log, str):
            logger.warning(f"Invalid log input: {type(log)}")
            return "unknown"
        
        log = log.strip()
        if not log:
            logger.warning("Empty log message")
            return "unknown"
        
        # Try each parser in priority order
        for parser_name in PARSER_DETECTION_ORDER:
            parser = self.registry.get_parser(parser_name)
            
            if parser is None:
                logger.debug(f"Parser '{parser_name}' not registered, skipping")
                continue
            
            try:
                if parser.detect(log):
                    logger.debug(f"Detected source: {parser_name}")
                    return parser_name
            except Exception as e:
                logger.warning(f"Error in {parser_name}.detect(): {e}")
                continue
        
        logger.warning(f"Could not detect source for log: {log[:100]}...")
        return "unknown"
    
    def detect_with_confidence(self, log: str) -> tuple[str, float]:
        """
        Detect source and return confidence level.
        
        For now, returns 1.0 if detected, 0.0 if unknown.
        Future: AI can return partial confidence.
        
        Args:
            log: Raw log message
            
        Returns:
            Tuple of (source_type, confidence)
            
        Example:
            >>> source, conf = detector.detect_with_confidence(log)
            >>> if conf == 1.0:
            ...     print(f"Certain: {source}")
            >>> elif conf > 0.7:
            ...     print(f"Likely: {source} ({conf})")
            >>> else:
            ...     print("Unknown source")
        """
        source = self.detect(log)
        confidence = 1.0 if source != "unknown" else 0.0
        return (source, confidence)
    
    def list_detectable_sources(self) -> list[str]:
        """
        List all sources that can be detected.
        
        Returns:
            List of detectable source types in priority order
        """
        return [
            name for name in PARSER_DETECTION_ORDER 
            if self.registry.get_parser(name) is not None
        ]
