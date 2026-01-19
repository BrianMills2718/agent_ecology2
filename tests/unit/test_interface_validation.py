"""Tests for interface validation (Plan #86).

Validates that artifact invocations match their declared interface schemas.
"""
import pytest
from typing import Any
from unittest.mock import MagicMock, patch

from src.world.artifacts import Artifact


# Sample interface for testing
SAMPLE_INTERFACE = {
    "description": "Test artifact",
    "tools": [
        {
            "name": "greet",
            "description": "Greet someone",
            "cost": 1,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to greet"},
                    "times": {"type": "integer", "minimum": 1}
                },
                "required": ["name"]
            }
        },
        {
            "name": "add",
            "description": "Add two numbers",
            "cost": 0,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["a", "b"]
            }
        }
    ]
}


class TestInterfaceValidation:
    """Test interface validation logic."""

    def test_validation_mode_none_skips_check(self) -> None:
        """When mode is 'none', validation is skipped entirely."""
        from src.world.executor import validate_args_against_interface

        # Even with invalid args, should pass when mode is 'none'
        result = validate_args_against_interface(
            interface=SAMPLE_INTERFACE,
            method_name="greet",
            args={"invalid_field": "value"},  # Missing required 'name'
            validation_mode="none"
        )
        assert result.valid is True
        assert result.skipped is True

    def test_validation_mode_warn_logs_mismatch(self) -> None:
        """When mode is 'warn', mismatches are logged but invoke proceeds."""
        from src.world.executor import validate_args_against_interface

        result = validate_args_against_interface(
            interface=SAMPLE_INTERFACE,
            method_name="greet",
            args={"invalid_field": "value"},  # Missing required 'name'
            validation_mode="warn"
        )
        assert result.valid is False
        assert result.proceed is True  # Should still proceed
        assert "name" in result.error_message.lower()  # Should mention missing field

    def test_validation_mode_strict_rejects_mismatch(self) -> None:
        """When mode is 'strict', mismatches reject the invocation."""
        from src.world.executor import validate_args_against_interface

        result = validate_args_against_interface(
            interface=SAMPLE_INTERFACE,
            method_name="greet",
            args={"invalid_field": "value"},  # Missing required 'name'
            validation_mode="strict"
        )
        assert result.valid is False
        assert result.proceed is False  # Should NOT proceed
        assert "name" in result.error_message.lower()

    def test_valid_args_pass_validation(self) -> None:
        """Correct arguments pass validation in all modes."""
        from src.world.executor import validate_args_against_interface

        for mode in ["none", "warn", "strict"]:
            result = validate_args_against_interface(
                interface=SAMPLE_INTERFACE,
                method_name="greet",
                args={"name": "Alice", "times": 3},
                validation_mode=mode
            )
            assert result.valid is True or result.skipped is True
            assert result.proceed is True

    def test_missing_required_field_detected(self) -> None:
        """Missing required fields are detected."""
        from src.world.executor import validate_args_against_interface

        # Missing 'b' which is required
        result = validate_args_against_interface(
            interface=SAMPLE_INTERFACE,
            method_name="add",
            args={"a": 1},  # Missing required 'b'
            validation_mode="strict"
        )
        assert result.valid is False
        assert "b" in result.error_message.lower() or "required" in result.error_message.lower()

    def test_no_interface_skips_validation(self) -> None:
        """Artifacts without interface skip validation."""
        from src.world.executor import validate_args_against_interface

        result = validate_args_against_interface(
            interface=None,
            method_name="any_method",
            args={"anything": "goes"},
            validation_mode="strict"
        )
        assert result.valid is True
        assert result.skipped is True

    def test_method_not_in_interface(self) -> None:
        """Invoking a method not in the interface."""
        from src.world.executor import validate_args_against_interface

        result = validate_args_against_interface(
            interface=SAMPLE_INTERFACE,
            method_name="nonexistent_method",
            args={},
            validation_mode="warn"
        )
        # Method not found in interface - should warn
        assert result.valid is False or result.skipped is True

    def test_type_mismatch_detected(self) -> None:
        """Type mismatches are caught (string instead of number)."""
        from src.world.executor import validate_args_against_interface

        result = validate_args_against_interface(
            interface=SAMPLE_INTERFACE,
            method_name="add",
            args={"a": "not a number", "b": 2},
            validation_mode="strict"
        )
        assert result.valid is False


class TestValidationConfig:
    """Test configuration of validation modes."""

    def test_config_validation_mode_default(self) -> None:
        """Default validation mode should be 'warn'."""
        from src.config_schema import ExecutorConfig

        config = ExecutorConfig()
        assert config.interface_validation == "warn"

    def test_config_validation_mode_options(self) -> None:
        """All three validation modes should be valid."""
        from src.config_schema import ExecutorConfig

        for mode in ["none", "warn", "strict"]:
            config = ExecutorConfig(interface_validation=mode)
            assert config.interface_validation == mode

    def test_config_invalid_mode_rejected(self) -> None:
        """Invalid validation mode should be rejected."""
        from src.config_schema import ExecutorConfig
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExecutorConfig(interface_validation="invalid_mode")


class TestValidationResult:
    """Test the ValidationResult dataclass."""

    def test_validation_result_fields(self) -> None:
        """ValidationResult should have expected fields."""
        from src.world.executor import ValidationResult

        result = ValidationResult(
            valid=True,
            proceed=True,
            skipped=False,
            error_message=""
        )
        assert result.valid is True
        assert result.proceed is True
        assert result.skipped is False
        assert result.error_message == ""
