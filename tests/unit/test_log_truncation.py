"""Tests for ActionResult log truncation (Plan #80)

TDD tests for truncating large result.data payloads in log files.
"""

import json
import pytest

from src.world.actions import ActionResult


class TestActionResultTruncation:
    """Tests for to_dict_truncated() method"""

    def test_action_result_truncation_small_data(self) -> None:
        """Small data should pass through unchanged"""
        result = ActionResult(
            success=True,
            message="OK",
            data={"key": "small value"}
        )

        truncated = result.to_dict_truncated(max_data_size=1000)

        assert truncated["success"] is True
        assert truncated["message"] == "OK"
        assert truncated["data"] == {"key": "small value"}
        # No truncation marker for small data
        assert "_truncated" not in str(truncated.get("data", {}))

    def test_action_result_truncation_large_data(self) -> None:
        """Large data should be truncated with metadata"""
        large_data = {"events": [{"id": i, "content": "x" * 100} for i in range(50)]}
        result = ActionResult(
            success=True,
            message="OK",
            data=large_data
        )

        # Truncate to 500 chars
        truncated = result.to_dict_truncated(max_data_size=500)

        assert truncated["success"] is True
        assert truncated["message"] == "OK"

        # Data should be truncated
        data = truncated["data"]
        assert data["_truncated"] is True
        assert "original_size" in data
        assert data["original_size"] > 500
        assert "preview" in data
        assert len(data["preview"]) <= 200  # Preview should be limited

    def test_truncation_preserves_other_fields(self) -> None:
        """Truncation should not affect other ActionResult fields"""
        result = ActionResult(
            success=False,
            message="Insufficient funds",
            data={"events": [{"x": "y" * 1000}]},  # Large data
            resources_consumed={"scrip": 10.0},
            charged_to="agent_1",
            error_code="insufficient_funds",
            error_category="resource",
            retriable=True,
            error_details={"needed": 100, "available": 50}
        )

        truncated = result.to_dict_truncated(max_data_size=100)

        # All non-data fields preserved
        assert truncated["success"] is False
        assert truncated["message"] == "Insufficient funds"
        assert truncated["resources_consumed"] == {"scrip": 10.0}
        assert truncated["charged_to"] == "agent_1"
        assert truncated["error_code"] == "insufficient_funds"
        assert truncated["error_category"] == "resource"
        assert truncated["retriable"] is True
        assert truncated["error_details"] == {"needed": 100, "available": 50}

        # Data should be truncated
        assert truncated["data"]["_truncated"] is True

    def test_nested_data_truncation(self) -> None:
        """Nested structures should be handled correctly"""
        nested_data = {
            "level1": {
                "level2": {
                    "level3": {"content": "x" * 1000}
                }
            }
        }
        result = ActionResult(
            success=True,
            message="OK",
            data=nested_data
        )

        truncated = result.to_dict_truncated(max_data_size=100)

        # Should truncate based on serialized size, not structure depth
        assert truncated["data"]["_truncated"] is True

    def test_none_data_not_truncated(self) -> None:
        """None data should remain None"""
        result = ActionResult(
            success=True,
            message="OK",
            data=None
        )

        truncated = result.to_dict_truncated(max_data_size=100)

        assert truncated["data"] is None

    def test_truncation_default_size(self) -> None:
        """to_dict_truncated() should have a reasonable default max_data_size"""
        large_data = {"content": "x" * 10000}
        result = ActionResult(
            success=True,
            message="OK",
            data=large_data
        )

        # Call without explicit size - should use default
        truncated = result.to_dict_truncated()

        # Should be truncated since 10000 chars exceeds any reasonable default
        assert truncated["data"]["_truncated"] is True

    def test_original_to_dict_unchanged(self) -> None:
        """Original to_dict() method should still return full data"""
        large_data = {"content": "x" * 10000}
        result = ActionResult(
            success=True,
            message="OK",
            data=large_data
        )

        # Original method returns full data
        full = result.to_dict()
        assert full["data"]["content"] == "x" * 10000

        # Truncated method truncates
        truncated = result.to_dict_truncated(max_data_size=100)
        assert truncated["data"]["_truncated"] is True

    def test_truncation_config_respected(self) -> None:
        """Config value should control truncation limit"""
        # Test that different max_data_size values are respected
        large_data = {"content": "x" * 500}  # 500+ chars when serialized
        result = ActionResult(
            success=True,
            message="OK",
            data=large_data
        )

        # With small limit, should truncate
        truncated_small = result.to_dict_truncated(max_data_size=100)
        assert truncated_small["data"]["_truncated"] is True

        # With large limit, should not truncate
        truncated_large = result.to_dict_truncated(max_data_size=2000)
        assert truncated_large["data"]["content"] == "x" * 500


@pytest.mark.plans([80])
class TestLogTruncationIntegration:
    """Integration tests for log truncation in World._log_action()"""

    # These tests will verify the truncation is actually used during logging
    # They require more complex setup with a World instance
    pass
