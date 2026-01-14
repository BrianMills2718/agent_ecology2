"""Tests for ActionResult error fields (Plan #40)."""

from __future__ import annotations

import pytest

from src.world.actions import ActionResult
from src.world.errors import ErrorCategory, ErrorCode


class TestActionResultErrorFields:
    """Tests for ActionResult error field support."""

    def test_error_fields_default_to_none_and_false(self) -> None:
        """Error fields have appropriate defaults for success cases."""
        result = ActionResult(success=True, message="OK")
        assert result.error_code is None
        assert result.error_category is None
        assert result.retriable is False
        assert result.error_details is None

    def test_error_fields_can_be_set(self) -> None:
        """Error fields can be set for failure cases."""
        result = ActionResult(
            success=False,
            message="Insufficient funds",
            error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
            error_category=ErrorCategory.RESOURCE.value,
            retriable=True,
            error_details={"required": 100, "available": 50},
        )
        assert result.success is False
        assert result.error_code == "insufficient_funds"
        assert result.error_category == "resource"
        assert result.retriable is True
        assert result.error_details == {"required": 100, "available": 50}

    def test_to_dict_includes_error_fields_when_set(self) -> None:
        """to_dict() includes error fields when they are set."""
        result = ActionResult(
            success=False,
            message="Not found",
            error_code=ErrorCode.NOT_FOUND.value,
            error_category=ErrorCategory.RESOURCE.value,
            retriable=False,
            error_details={"artifact_id": "missing_artifact"},
        )
        d = result.to_dict()
        assert d["error_code"] == "not_found"
        assert d["error_category"] == "resource"
        assert d["retriable"] is False
        assert d["error_details"] == {"artifact_id": "missing_artifact"}

    def test_to_dict_excludes_error_fields_when_none(self) -> None:
        """to_dict() excludes error fields when they are None/False."""
        result = ActionResult(success=True, message="OK", data={"content": "test"})
        d = result.to_dict()
        assert "error_code" not in d
        assert "error_category" not in d
        assert "retriable" not in d
        assert "error_details" not in d

    def test_backward_compatibility_success_message_data(self) -> None:
        """Existing code using success/message/data still works."""
        result = ActionResult(
            success=True,
            message="Artifact read successfully",
            data={"content": "Hello, world!"},
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["message"] == "Artifact read successfully"
        assert d["data"] == {"content": "Hello, world!"}

    def test_backward_compatibility_with_resources(self) -> None:
        """Existing code with resources_consumed/charged_to still works."""
        result = ActionResult(
            success=True,
            message="OK",
            resources_consumed={"compute": 1.5},
            charged_to="agent_alice",
        )
        d = result.to_dict()
        assert d["resources_consumed"] == {"compute": 1.5}
        assert d["charged_to"] == "agent_alice"


class TestActionResultRetriability:
    """Tests for error retriability guidance."""

    def test_retriable_true_for_resource_errors(self) -> None:
        """Resource errors (insufficient funds) should be retriable."""
        result = ActionResult(
            success=False,
            message="Insufficient scrip",
            error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
            error_category=ErrorCategory.RESOURCE.value,
            retriable=True,  # Agent could get more scrip and retry
        )
        assert result.retriable is True

    def test_retriable_false_for_permission_errors(self) -> None:
        """Permission errors should not be retriable."""
        result = ActionResult(
            success=False,
            message="Not authorized",
            error_code=ErrorCode.NOT_AUTHORIZED.value,
            error_category=ErrorCategory.PERMISSION.value,
            retriable=False,  # Permission won't change without external action
        )
        assert result.retriable is False

    def test_retriable_for_timeout_errors(self) -> None:
        """Timeout errors may be retriable."""
        result = ActionResult(
            success=False,
            message="Execution timeout",
            error_code=ErrorCode.TIMEOUT.value,
            error_category=ErrorCategory.EXECUTION.value,
            retriable=True,  # Could succeed with different timing
        )
        assert result.retriable is True
