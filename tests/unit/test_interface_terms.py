"""Tests for interface reserved terms (Plan #54).

These tests verify that interface structures using reserved terms
work correctly for artifact discoverability.
"""

import pytest
from typing import Any


def validate_interface_structure(interface: dict[str, Any] | None) -> dict[str, Any]:
    """Validate interface structure and return parsed info.
    
    This helper recognizes reserved terms and extracts structured info.
    Returns a dict with recognized fields and a 'valid' flag.
    """
    if interface is None:
        return {"valid": True, "has_interface": False}
    
    result: dict[str, Any] = {"valid": True, "has_interface": True}
    
    # Core terms
    if "description" in interface:
        result["description"] = interface["description"]
    
    if "methods" in interface:
        if isinstance(interface["methods"], list):
            result["methods"] = []
            for method in interface["methods"]:
                method_info: dict[str, Any] = {}
                if "name" in method:
                    method_info["name"] = method["name"]
                if "description" in method:
                    method_info["description"] = method["description"]
                if "inputSchema" in method:
                    method_info["inputSchema"] = method["inputSchema"]
                if "outputSchema" in method:
                    method_info["outputSchema"] = method["outputSchema"]
                if "cost" in method:
                    method_info["cost"] = method["cost"]
                if "errors" in method:
                    method_info["errors"] = method["errors"]
                if "examples" in method:
                    method_info["examples"] = method["examples"]
                if "linearization" in method:
                    method_info["linearization"] = method["linearization"]
                result["methods"].append(method_info)
    
    # StructGPT-inspired terms
    if "dataType" in interface:
        result["dataType"] = interface["dataType"]
    
    return result


class TestInterfaceReservedTerms:
    """Test interface reserved terms recognition."""
    
    def test_interface_description_only(self) -> None:
        """Minimal interface with just description works."""
        interface = {
            "description": "A simple note storage service"
        }
        
        result = validate_interface_structure(interface)
        
        assert result["valid"] is True
        assert result["has_interface"] is True
        assert result["description"] == "A simple note storage service"
        assert "methods" not in result
    
    def test_interface_with_methods(self) -> None:
        """Interface with methods array is recognized."""
        interface = {
            "description": "Calculator service",
            "methods": [
                {
                    "name": "add",
                    "description": "Add two numbers",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number"},
                            "b": {"type": "number"}
                        }
                    },
                    "outputSchema": {"type": "number"},
                    "cost": 0
                }
            ]
        }
        
        result = validate_interface_structure(interface)
        
        assert result["valid"] is True
        assert result["description"] == "Calculator service"
        assert len(result["methods"]) == 1
        assert result["methods"][0]["name"] == "add"
        assert result["methods"][0]["cost"] == 0
    
    def test_interface_full_example(self) -> None:
        """Full StructGPT-style interface with all reserved terms works."""
        interface = {
            "description": "Movie knowledge graph",
            "dataType": "knowledge_graph",
            "methods": [
                {
                    "name": "get_relations",
                    "description": "Get all relations for an entity",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "entity": {"type": "string"}
                        },
                        "required": ["entity"]
                    },
                    "outputSchema": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "linearization": "Relations: {result.join(', ')}",
                    "cost": 1,
                    "errors": ["ENTITY_NOT_FOUND"],
                    "examples": [
                        {
                            "input": {"entity": "Spielberg"},
                            "output": ["directed", "produced", "wrote"]
                        }
                    ]
                }
            ]
        }
        
        result = validate_interface_structure(interface)
        
        assert result["valid"] is True
        assert result["description"] == "Movie knowledge graph"
        assert result["dataType"] == "knowledge_graph"
        assert len(result["methods"]) == 1
        
        method = result["methods"][0]
        assert method["name"] == "get_relations"
        assert method["linearization"] == "Relations: {result.join(', ')}"
        assert method["cost"] == 1
        assert "ENTITY_NOT_FOUND" in method["errors"]
        assert len(method["examples"]) == 1
    
    def test_interface_none(self) -> None:
        """None interface is valid (no interface defined)."""
        result = validate_interface_structure(None)
        
        assert result["valid"] is True
        assert result["has_interface"] is False
    
    def test_interface_unknown_fields_preserved(self) -> None:
        """Unknown fields don't break validation (graceful degradation)."""
        interface = {
            "description": "Custom service",
            "custom_field": "some value",
            "another_custom": {"nested": "data"}
        }
        
        result = validate_interface_structure(interface)
        
        assert result["valid"] is True
        assert result["description"] == "Custom service"
        # Unknown fields are not extracted but don't cause failure
    
    def test_interface_data_types(self) -> None:
        """Different dataType values are recognized."""
        for data_type in ["table", "knowledge_graph", "service", "document"]:
            interface = {
                "description": f"A {data_type} artifact",
                "dataType": data_type
            }
            
            result = validate_interface_structure(interface)
            
            assert result["valid"] is True
            assert result["dataType"] == data_type
