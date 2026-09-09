"""
Configuration and constants for ULPF backend.

This module centralizes all configuration settings, parser priorities,
and application constants.
"""

# ============================================================================
# PARSER DETECTION ORDER
# ============================================================================
# Order matters! Parsers are tried in this sequence to detect the source.
# More specific/reliable parsers should come first.
PARSER_DETECTION_ORDER = [
    "json",           # JSON is most reliable (valid JSON structure)
    "cisco",          # Cisco ASA has distinct %ASA- pattern
    "fortinet",       # Fortinet has key=value pattern with devname=
    "paloalto",       # Palo Alto has specific field patterns
    "syslog",         # Generic syslog (fallback, least specific)
]

# ============================================================================
# API CONFIGURATION
# ============================================================================
API_HOST = "0.0.0.0"
API_PORT = 8000
API_TITLE = "ULPF - Universal Log Pre-processing Framework"
API_VERSION = "0.1.0"
API_DESCRIPTION = "Phase 1: Canonical log normalization engine"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================================
# VALIDATION CONFIGURATION
# ============================================================================
# Valid port range for network logs
MIN_PORT = 0
MAX_PORT = 65535

# Required fields in canonical event
REQUIRED_FIELDS = [
    "event_id",
    "timestamp",
    "raw",
    "provenance"
]

# ============================================================================
# PARSER VERSIONS
# ============================================================================
# Version numbers for each parser (for provenance tracking)
PARSER_VERSIONS = {
    "cisco": "1.0",
    "fortinet": "1.0",
    "paloalto": "1.0",
    "syslog": "1.0",
    "json": "1.0",
}

# Mapping version (incremented when field mappings change)
MAPPING_VERSION = "1.0"

# ============================================================================
# DEFAULT CONFIDENCE
# ============================================================================
# For Phase 1, all deterministic parsers have confidence 1.0
# AI-generated parsers will use real confidence values later
DEFAULT_CONFIDENCE = 1.0

# ============================================================================
# FEATURE FLAGS
# ============================================================================
# Enable/disable specific features
ENABLE_VALIDATION = True
ENABLE_UNMAPPED_FIELDS = True  # Never lose unmapped fields
PRESERVE_RAW_MESSAGE = True     # Never lose raw message
