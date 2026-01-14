# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
# --- GOVERNANCE END ---

"""Standardized error response conventions for artifact invocations.

This module provides consistent error handling across all genesis artifacts
and executor code. It enables programmatic error handling by agents through
error codes, categories, and retry guidance.

Usage:
    from src.world.errors import validation_error, ErrorCode

    # In artifact code:
    return validation_error(
        "transfer requires [from_id, to_id, amount]",
        code=ErrorCode.MISSING_ARGUMENT,
        required=["from_id", "to_id", "amount"],
    )
"""

from dataclasses import dataclass
from enum import Enum


class ErrorCategory(str, Enum):
    """Categories for error classification.

    Helps agents understand the nature of an error:
    - VALIDATION: Agent provided bad input
    - PERMISSION: Agent not authorized
    - RESOURCE: Resource-related issues
    - EXECUTION: Runtime/execution problems
    - SYSTEM: Internal system errors
    """

    VALIDATION = "validation"  # Invalid input, bad arguments
    PERMISSION = "permission"  # Not authorized, wrong owner
    RESOURCE = "resource"  # Not found, already exists
    EXECUTION = "execution"  # Runtime error, timeout
    SYSTEM = "system"  # Internal error, unexpected


class ErrorCode(str, Enum):
    """Specific error codes for programmatic handling.

    Agents can switch on these codes to implement specific recovery logic.
    """

    # Validation errors
    MISSING_ARGUMENT = "missing_argument"
    INVALID_ARGUMENT = "invalid_argument"
    INVALID_TYPE = "invalid_type"

    # Permission errors
    NOT_OWNER = "not_owner"
    NOT_AUTHORIZED = "not_authorized"
    INSUFFICIENT_FUNDS = "insufficient_funds"

    # Resource errors
    NOT_FOUND = "not_found"
    ALREADY_EXISTS = "already_exists"
    ALREADY_LISTED = "already_listed"
    DELETED = "deleted"
    QUOTA_EXCEEDED = "quota_exceeded"

    # Execution errors
    TIMEOUT = "timeout"
    RUNTIME_ERROR = "runtime_error"
    SYNTAX_ERROR = "syntax_error"

    # System errors
    INTERNAL_ERROR = "internal_error"
    NOT_CONFIGURED = "not_configured"


@dataclass
class ErrorResponse:
    """Standardized error response.

    All error responses include:
    - success: Always False
    - error: Human-readable message
    - code: Machine-readable error code
    - category: Error category (validation, permission, etc.)
    - retriable: Whether the operation should be retried
    - details: Optional additional context

    This schema is backwards compatible with the existing
    {"success": False, "error": "message"} pattern.
    """

    success: bool = False  # Always False for errors
    error: str = ""  # Human-readable message
    code: str = ""  # Machine-readable error code
    category: str = ""  # Error category (validation, permission, etc.)
    retriable: bool = False  # Whether the operation should be retried
    details: dict[str, object] | None = None  # Optional additional context

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        result: dict[str, object] = {
            "success": self.success,
            "error": self.error,
            "code": self.code,
            "category": self.category,
            "retriable": self.retriable,
        }
        if self.details:
            result["details"] = self.details
        return result


# Factory functions for creating error responses


def validation_error(
    message: str,
    code: ErrorCode = ErrorCode.INVALID_ARGUMENT,
    **details: object,
) -> dict[str, object]:
    """Create a validation error response.

    Use when the agent provided invalid input.

    Args:
        message: Human-readable error message
        code: Specific error code (default: INVALID_ARGUMENT)
        **details: Additional context (e.g., required=["field1", "field2"])

    Returns:
        Error response dict with success=False
    """
    return ErrorResponse(
        error=message,
        code=code.value,
        category=ErrorCategory.VALIDATION.value,
        retriable=False,
        details=dict(details) if details else None,
    ).to_dict()


def permission_error(
    message: str,
    code: ErrorCode = ErrorCode.NOT_AUTHORIZED,
    **details: object,
) -> dict[str, object]:
    """Create a permission error response.

    Use when the agent is not authorized for the operation.

    Args:
        message: Human-readable error message
        code: Specific error code (default: NOT_AUTHORIZED)
        **details: Additional context

    Returns:
        Error response dict with success=False
    """
    return ErrorResponse(
        error=message,
        code=code.value,
        category=ErrorCategory.PERMISSION.value,
        retriable=False,
        details=dict(details) if details else None,
    ).to_dict()


def resource_error(
    message: str,
    code: ErrorCode = ErrorCode.NOT_FOUND,
    **details: object,
) -> dict[str, object]:
    """Create a resource error response.

    Use for resource not found, already exists, etc.

    Args:
        message: Human-readable error message
        code: Specific error code (default: NOT_FOUND)
        **details: Additional context

    Returns:
        Error response dict with success=False
    """
    return ErrorResponse(
        error=message,
        code=code.value,
        category=ErrorCategory.RESOURCE.value,
        retriable=False,
        details=dict(details) if details else None,
    ).to_dict()


def execution_error(
    message: str,
    code: ErrorCode = ErrorCode.RUNTIME_ERROR,
    retriable: bool = False,
    **details: object,
) -> dict[str, object]:
    """Create an execution error response.

    Use for runtime errors, timeouts, etc.

    Args:
        message: Human-readable error message
        code: Specific error code (default: RUNTIME_ERROR)
        retriable: Whether the operation should be retried
        **details: Additional context

    Returns:
        Error response dict with success=False
    """
    return ErrorResponse(
        error=message,
        code=code.value,
        category=ErrorCategory.EXECUTION.value,
        retriable=retriable,
        details=dict(details) if details else None,
    ).to_dict()


def system_error(
    message: str,
    code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    retriable: bool = True,
    **details: object,
) -> dict[str, object]:
    """Create a system error response.

    Use for internal errors, unexpected conditions.

    Args:
        message: Human-readable error message
        code: Specific error code (default: INTERNAL_ERROR)
        retriable: Whether the operation should be retried (default: True)
        **details: Additional context

    Returns:
        Error response dict with success=False
    """
    return ErrorResponse(
        error=message,
        code=code.value,
        category=ErrorCategory.SYSTEM.value,
        retriable=retriable,
        details=dict(details) if details else None,
    ).to_dict()
