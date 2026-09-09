"""
Parser Registry for ULPF.

The registry is a central place where all parsers are registered and retrieved.
It enables:
- Clean separation: pipeline doesn't hardcode vendor logic
- Plug-and-play: new parsers can be added without modifying core code
- Future AI: generated parsers can self-register

WHAT is a registry?
A dictionary/map that stores parser instances, indexed by parser name.

WHY do we need it?
If we put vendor logic in the pipeline (if vendor == "cisco" then... else if 
vendor == "fortinet" then...), then:
- Adding a new vendor requires editing the pipeline
- The code becomes unmaintainable
- It's impossible to load dynamic/generated parsers

The registry decouples the pipeline from vendor-specific logic.

HOW does it work?
1. Each parser registers itself: registry.register(FortinetParser())
2. Pipeline detects source: source_type = detector.detect(log)
3. Pipeline gets parser: parser = registry.get_parser(source_type)
4. Pipeline uses parser: event = parser.parse(log)

The registry also enables:
- find_parser(log) → Try each parser's detect() to find a match
- list_parsers() → List all registered parsers (for API)
"""

from typing import Dict, Optional, List
from backend.parsers.base import BaseParser


class ParserRegistry:
    """
    Central registry for all log parsers.
    
    Manages parser registration, retrieval, and discovery.
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._parsers: Dict[str, BaseParser] = {}
    
    def register(self, parser: BaseParser) -> None:
        """
        Register a new parser.
        
        Args:
            parser: An instance of a class that inherits from BaseParser
            
        Raises:
            ValueError: If parser name is already registered
            TypeError: If parser doesn't inherit from BaseParser
            
        Example:
            >>> registry = ParserRegistry()
            >>> registry.register(FortinetParser())
            >>> registry.register(CiscoASAParser())
        """
        if not isinstance(parser, BaseParser):
            raise TypeError(
                f"Parser must inherit from BaseParser, got {type(parser).__name__}"
            )
        
        if parser.name in self._parsers:
            raise ValueError(
                f"Parser '{parser.name}' is already registered. "
                f"Use update() to replace an existing parser."
            )
        
        self._parsers[parser.name] = parser
    
    def update(self, parser: BaseParser) -> None:
        """
        Register or update a parser (overwrites if exists).
        
        Args:
            parser: An instance of a class that inherits from BaseParser
            
        Example:
            >>> registry.update(FortinetParser())  # Creates or replaces
        """
        if not isinstance(parser, BaseParser):
            raise TypeError(
                f"Parser must inherit from BaseParser, got {type(parser).__name__}"
            )
        self._parsers[parser.name] = parser
    
    def get_parser(self, name: str) -> Optional[BaseParser]:
        """
        Get a parser by name.
        
        Args:
            name: Parser name (e.g., 'fortinet', 'cisco')
            
        Returns:
            Parser instance, or None if not found
            
        Example:
            >>> parser = registry.get_parser('fortinet')
            >>> if parser:
            ...     event = parser.parse(log)
        """
        return self._parsers.get(name)
    
    def find_parser(self, log: str) -> Optional[BaseParser]:
        """
        Find a parser that can handle the given log.
        
        Tries each registered parser's detect() method until one returns True.
        Detection order depends on registration order.
        
        Args:
            log: Raw log message
            
        Returns:
            First parser that detects the log, or None if no match
            
        Implementation notes:
        - This is called AFTER source detection by the pipeline
        - For better control, use detector.detect() which respects priority order
        - This method is useful for fallback/exploration
        
        Example:
            >>> parser = registry.find_parser("date=2026-09-09 devname=FW01")
            >>> if parser:
            ...     print(f"Found parser: {parser.name}")
        """
        for parser in self._parsers.values():
            try:
                if parser.detect(log):
                    return parser
            except Exception:
                # If a parser's detect() raises an exception, skip it
                continue
        
        return None
    
    def list_parsers(self) -> List[str]:
        """
        List all registered parser names.
        
        Returns:
            List of parser names
            
        Example:
            >>> registry.list_parsers()
            ['cisco', 'fortinet', 'paloalto', 'syslog', 'json']
        """
        return list(self._parsers.keys())
    
    def get_parser_info(self, name: str) -> Optional[Dict]:
        """
        Get metadata about a registered parser.
        
        Args:
            name: Parser name
            
        Returns:
            Parser info dictionary, or None if not found
            
        Example:
            >>> registry.get_parser_info('fortinet')
            {
                'name': 'fortinet',
                'version': '1.0',
                'vendor': 'Fortinet',
                ...
            }
        """
        parser = self.get_parser(name)
        if parser:
            return parser.get_info()
        return None
    
    def all_parser_info(self) -> List[Dict]:
        """
        Get metadata for all registered parsers.
        
        Returns:
            List of parser info dictionaries
        """
        return [parser.get_info() for parser in self._parsers.values()]
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a parser (mainly for testing).
        
        Args:
            name: Parser name
            
        Returns:
            True if parser was removed, False if not found
        """
        if name in self._parsers:
            del self._parsers[name]
            return True
        return False
    
    def clear(self) -> None:
        """
        Clear all registered parsers (mainly for testing).
        """
        self._parsers.clear()
    
    def __len__(self) -> int:
        """Return the number of registered parsers."""
        return len(self._parsers)
    
    def __contains__(self, name: str) -> bool:
        """Check if a parser is registered."""
        return name in self._parsers


# Global registry instance (singleton pattern)
# This will be used throughout the application
_global_registry: Optional[ParserRegistry] = None


def get_registry() -> ParserRegistry:
    """
    Get the global parser registry instance.
    
    Creates one if it doesn't exist (lazy initialization).
    
    Returns:
        Global ParserRegistry instance
        
    Example:
        >>> registry = get_registry()
        >>> registry.register(FortinetParser())
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ParserRegistry()
    return _global_registry


def reset_registry() -> None:
    """
    Reset the global registry (mainly for testing).
    """
    global _global_registry
    _global_registry = None
