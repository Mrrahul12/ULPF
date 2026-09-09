"""
Tests for the Parser Registry.

Verifies that parser registration, retrieval, and discovery work correctly.
"""

import pytest
from backend.parsers.base import BaseParser
from backend.parsers.registry import ParserRegistry, get_registry, reset_registry
from typing import Dict, Any, Tuple


# Mock parser for testing
class MockParser(BaseParser):
    """Simple mock parser for testing registry."""
    
    def __init__(self, name: str = "mock"):
        super().__init__(name=name, version="1.0")
        self.detect_return = True
        self.parse_return = (True, {"field": "value"}, "")
    
    def detect(self, log: str) -> bool:
        return self.detect_return
    
    def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
        return self.parse_return
    
    def normalize(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        return parsed, {}


class TestParserRegistry:
    """Test suite for ParserRegistry class."""
    
    def setup_method(self):
        """Create a fresh registry for each test."""
        self.registry = ParserRegistry()
    
    def test_register_parser(self):
        """Test registering a parser."""
        parser = MockParser("test_parser")
        self.registry.register(parser)
        
        assert "test_parser" in self.registry
        assert self.registry.get_parser("test_parser") == parser
    
    def test_register_duplicate_fails(self):
        """Test that registering the same name twice fails."""
        parser1 = MockParser("duplicate")
        parser2 = MockParser("duplicate")
        
        self.registry.register(parser1)
        
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(parser2)
    
    def test_register_invalid_type_fails(self):
        """Test that registering a non-BaseParser fails."""
        with pytest.raises(TypeError):
            self.registry.register("not a parser")
    
    def test_get_parser_by_name(self):
        """Test retrieving a parser by name."""
        parser = MockParser("cisco")
        self.registry.register(parser)
        
        retrieved = self.registry.get_parser("cisco")
        assert retrieved == parser
    
    def test_get_nonexistent_parser_returns_none(self):
        """Test that getting a non-existent parser returns None."""
        assert self.registry.get_parser("nonexistent") is None
    
    def test_update_parser(self):
        """Test updating (overwriting) a parser."""
        parser1 = MockParser("cisco")
        parser2 = MockParser("cisco")
        
        self.registry.register(parser1)
        self.registry.update(parser2)
        
        assert self.registry.get_parser("cisco") == parser2
    
    def test_find_parser_by_detection(self):
        """Test finding a parser using its detect() method."""
        parser = MockParser("fortinet")
        parser.detect_return = True
        
        self.registry.register(parser)
        
        found = self.registry.find_parser("some log")
        assert found == parser
    
    def test_find_parser_no_match(self):
        """Test that find_parser returns None when no parser matches."""
        parser = MockParser("cisco")
        parser.detect_return = False
        
        self.registry.register(parser)
        
        found = self.registry.find_parser("some log")
        assert found is None
    
    def test_find_parser_tries_multiple(self):
        """Test that find_parser tries multiple parsers."""
        parser1 = MockParser("parser1")
        parser1.detect_return = False
        
        parser2 = MockParser("parser2")
        parser2.detect_return = True
        
        self.registry.register(parser1)
        self.registry.register(parser2)
        
        found = self.registry.find_parser("some log")
        assert found == parser2
    
    def test_list_parsers(self):
        """Test listing all registered parsers."""
        parser1 = MockParser("parser1")
        parser2 = MockParser("parser2")
        
        self.registry.register(parser1)
        self.registry.register(parser2)
        
        names = self.registry.list_parsers()
        assert set(names) == {"parser1", "parser2"}
    
    def test_unregister_parser(self):
        """Test unregistering a parser."""
        parser = MockParser("cisco")
        self.registry.register(parser)
        
        success = self.registry.unregister("cisco")
        assert success is True
        assert self.registry.get_parser("cisco") is None
    
    def test_unregister_nonexistent_returns_false(self):
        """Test that unregistering non-existent parser returns False."""
        success = self.registry.unregister("nonexistent")
        assert success is False
    
    def test_clear_registry(self):
        """Test clearing all parsers."""
        self.registry.register(MockParser("parser1"))
        self.registry.register(MockParser("parser2"))
        
        self.registry.clear()
        
        assert len(self.registry) == 0
        assert self.registry.list_parsers() == []
    
    def test_len_registry(self):
        """Test getting the number of registered parsers."""
        assert len(self.registry) == 0
        
        self.registry.register(MockParser("parser1"))
        assert len(self.registry) == 1
        
        self.registry.register(MockParser("parser2"))
        assert len(self.registry) == 2
    
    def test_contains_check(self):
        """Test checking if a parser is registered."""
        parser = MockParser("cisco")
        self.registry.register(parser)
        
        assert "cisco" in self.registry
        assert "nonexistent" not in self.registry
    
    def test_get_parser_info(self):
        """Test getting metadata about a parser."""
        parser = MockParser("cisco")
        self.registry.register(parser)
        
        info = self.registry.get_parser_info("cisco")
        assert info is not None
        assert info["name"] == "cisco"
        assert info["version"] == "1.0"
    
    def test_get_parser_info_nonexistent(self):
        """Test that get_parser_info returns None for nonexistent parser."""
        info = self.registry.get_parser_info("nonexistent")
        assert info is None
    
    def test_all_parser_info(self):
        """Test getting metadata for all parsers."""
        self.registry.register(MockParser("parser1"))
        self.registry.register(MockParser("parser2"))
        
        all_info = self.registry.all_parser_info()
        assert len(all_info) == 2
        names = [info["name"] for info in all_info]
        assert set(names) == {"parser1", "parser2"}


class TestGlobalRegistry:
    """Test suite for global registry singleton."""
    
    def setup_method(self):
        """Reset registry before each test."""
        reset_registry()
    
    def test_get_registry_singleton(self):
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        
        assert registry1 is registry2
    
    def test_reset_registry(self):
        """Test resetting the global registry."""
        registry = get_registry()
        registry.register(MockParser("test"))
        
        reset_registry()
        
        new_registry = get_registry()
        assert len(new_registry) == 0
    
    def test_global_registry_persistence(self):
        """Test that global registry persists across calls."""
        registry1 = get_registry()
        registry1.register(MockParser("cisco"))
        
        registry2 = get_registry()
        assert registry2.get_parser("cisco") is not None


class TestParserBaseInterface:
    """Test suite for BaseParser abstract class."""
    
    def test_cannot_instantiate_base_parser(self):
        """Test that BaseParser cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseParser(name="test")
    
    def test_must_implement_detect(self):
        """Test that subclasses must implement detect()."""
        class IncompleteParser(BaseParser):
            def parse(self, log: str) -> Tuple[bool, Dict[str, Any], str]:
                pass
            def normalize(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
                pass
        
        with pytest.raises(TypeError):
            IncompleteParser(name="incomplete")
    
    def test_parser_name_and_version(self):
        """Test that parser stores name and version."""
        parser = MockParser("test_parser")
        parser.version = "2.5.1"
        
        info = parser.get_info()
        assert info["name"] == "test_parser"
        assert info["version"] == "2.5.1"
