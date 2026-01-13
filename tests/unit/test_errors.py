"""Unit tests for error response conventions.

Tests the error module from Plan #23 (Error Response Conventions).
"""

import pytest

from src.world.errors import (
    ErrorCategory,
    ErrorCode,
    ErrorResponse,
    execution_error,
    permission_error,
    resource_error,
    system_error,
    validation_error,
)


class TestErrorEnums:
    """Tests for ErrorCategory and ErrorCode enums."""

    def test_error_category_values(self) -> None:
        """All error categories have string values."""
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.PERMISSION.value == "permission"
        assert ErrorCategory.RESOURCE.value == "resource"
        assert ErrorCategory.EXECUTION.value == "execution"
        assert ErrorCategory.SYSTEM.value == "system"

    def test_error_code_enum(self) -> None:
        """All error codes have valid string values."""
        # Validation codes
        assert ErrorCode.MISSING_ARGUMENT.value == "missing_argument"
        assert ErrorCode.INVALID_ARGUMENT.value == "invalid_argument"
        assert ErrorCode.INVALID_TYPE.value == "invalid_type"

        # Permission codes
        assert ErrorCode.NOT_OWNER.value == "not_owner"
        assert ErrorCode.NOT_AUTHORIZED.value == "not_authorized"
        assert ErrorCode.INSUFFICIENT_FUNDS.value == "insufficient_funds"

        # Resource codes
        assert ErrorCode.NOT_FOUND.value == "not_found"
        assert ErrorCode.ALREADY_EXISTS.value == "already_exists"
        assert ErrorCode.DELETED.value == "deleted"

        # Execution codes
        assert ErrorCode.TIMEOUT.value == "timeout"
        assert ErrorCode.RUNTIME_ERROR.value == "runtime_error"

        # System codes
        assert ErrorCode.INTERNAL_ERROR.value == "internal_error"


class TestErrorResponse:
    """Tests for ErrorResponse dataclass."""

    def test_error_to_dict(self) -> None:
        """ErrorResponse serializes correctly."""
        resp = ErrorResponse(
            error="Test error",
            code="test_code",
            category="test_category",
            retriable=True,
        )
        result = resp.to_dict()

        assert result["success"] is False
        assert result["error"] == "Test error"
        assert result["code"] == "test_code"
        assert result["category"] == "test_category"
        assert result["retriable"] is True
        assert "details" not in result

    def test_error_to_dict_with_details(self) -> None:
        """ErrorResponse includes details when provided."""
        resp = ErrorResponse(
            error="Test error",
            code="test_code",
            category="test_category",
            details={"field": "value"},
        )
        result = resp.to_dict()

        assert result["details"] == {"field": "value"}

    def test_backwards_compatible(self) -> None:
        """Error responses have success and error fields for backwards compatibility."""
        resp = ErrorResponse(error="Some error", code="err", category="cat")
        result = resp.to_dict()

        # These are the fields that existing code checks
        assert "success" in result
        assert "error" in result
        assert result["success"] is False


class TestValidationError:
    """Tests for validation_error factory function."""

    def test_validation_error_format(self) -> None:
        """Validation errors have correct structure."""
        result = validation_error("Bad input")

        assert result["success"] is False
        assert result["error"] == "Bad input"
        assert result["code"] == "invalid_argument"
        assert result["category"] == "validation"
        assert result["retriable"] is False

    def test_validation_error_with_code(self) -> None:
        """Validation errors accept custom error code."""
        result = validation_error(
            "Missing field",
            code=ErrorCode.MISSING_ARGUMENT,
        )

        assert result["code"] == "missing_argument"

    def test_validation_error_with_details(self) -> None:
        """Validation errors can include details."""
        result = validation_error(
            "Missing required fields",
            code=ErrorCode.MISSING_ARGUMENT,
            required=["from_id", "to_id", "amount"],
        )

        assert result["details"] == {"required": ["from_id", "to_id", "amount"]}


class TestPermissionError:
    """Tests for permission_error factory function."""

    def test_permission_error_format(self) -> None:
        """Permission errors have correct structure."""
        result = permission_error("Not authorized")

        assert result["success"] is False
        assert result["error"] == "Not authorized"
        assert result["code"] == "not_authorized"
        assert result["category"] == "permission"
        assert result["retriable"] is False

    def test_permission_error_not_owner(self) -> None:
        """Permission errors can use NOT_OWNER code."""
        result = permission_error(
            "Only owner can delete",
            code=ErrorCode.NOT_OWNER,
            owner="alice",
            requester="bob",
        )

        assert result["code"] == "not_owner"
        assert result["details"] == {"owner": "alice", "requester": "bob"}


class TestResourceError:
    """Tests for resource_error factory function."""

    def test_resource_error_format(self) -> None:
        """Resource errors have correct structure."""
        result = resource_error("Artifact not found")

        assert result["success"] is False
        assert result["error"] == "Artifact not found"
        assert result["code"] == "not_found"
        assert result["category"] == "resource"
        assert result["retriable"] is False

    def test_resource_error_already_exists(self) -> None:
        """Resource errors can use ALREADY_EXISTS code."""
        result = resource_error(
            "Artifact already exists",
            code=ErrorCode.ALREADY_EXISTS,
            artifact_id="art_123",
        )

        assert result["code"] == "already_exists"
        assert result["details"]["artifact_id"] == "art_123"


class TestExecutionError:
    """Tests for execution_error factory function."""

    def test_execution_error_format(self) -> None:
        """Execution errors have correct structure."""
        result = execution_error("Code execution failed")

        assert result["success"] is False
        assert result["error"] == "Code execution failed"
        assert result["code"] == "runtime_error"
        assert result["category"] == "execution"
        assert result["retriable"] is False

    def test_execution_error_retriable(self) -> None:
        """Execution errors can be marked retriable."""
        result = execution_error(
            "Operation timed out",
            code=ErrorCode.TIMEOUT,
            retriable=True,
        )

        assert result["code"] == "timeout"
        assert result["retriable"] is True


class TestSystemError:
    """Tests for system_error factory function."""

    def test_system_error_format(self) -> None:
        """System errors have correct structure."""
        result = system_error("Internal error")

        assert result["success"] is False
        assert result["error"] == "Internal error"
        assert result["code"] == "internal_error"
        assert result["category"] == "system"
        assert result["retriable"] is True  # System errors are retriable by default

    def test_system_error_not_retriable(self) -> None:
        """System errors can be marked non-retriable."""
        result = system_error(
            "Configuration missing",
            code=ErrorCode.NOT_CONFIGURED,
            retriable=False,
        )

        assert result["code"] == "not_configured"
        assert result["retriable"] is False
