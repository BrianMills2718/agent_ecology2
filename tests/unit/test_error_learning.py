"""Tests for Plan #161: Agent Error Learning.

Tests that error messages are helpful and discoverable.
"""

import json
import pytest
from unittest.mock import MagicMock

from src.world.artifacts import Artifact
from src.world.actions import parse_intent_from_json, InvokeArtifactIntent


class TestArtifactAttributeErrors:
    """Tests for helpful attribute error messages on Artifact."""

    def test_suggests_type_for_artifact_type_typo(self) -> None:
        """Test that accessing 'artifact_type' suggests 'type'."""
        artifact = Artifact(
            id="test_artifact",
            type="executable",
            content="Test content",
            created_by="alice",
            created_at="2025-01-25T00:00:00Z",
            updated_at="2025-01-25T00:00:00Z",
        )

        with pytest.raises(AttributeError) as exc_info:
            _ = artifact.artifact_type  # type: ignore[attr-defined]

        error_msg = str(exc_info.value)
        assert "artifact_type" in error_msg
        assert "Did you mean 'type'" in error_msg
        assert "Available:" in error_msg

    def test_suggests_id_for_artifact_id_typo(self) -> None:
        """Test that accessing 'artifact_id' suggests 'id'."""
        artifact = Artifact(
            id="test_artifact",
            type="data",
            content="",
            created_by="bob",
            created_at="2025-01-25T00:00:00Z",
            updated_at="2025-01-25T00:00:00Z",
        )

        with pytest.raises(AttributeError) as exc_info:
            _ = artifact.artifact_id  # type: ignore[attr-defined]

        error_msg = str(exc_info.value)
        assert "artifact_id" in error_msg
        assert "Did you mean 'id'" in error_msg

    def test_suggests_created_by_for_owner_typo(self) -> None:
        """Test that accessing 'owner' suggests 'created_by'."""
        artifact = Artifact(
            id="test_artifact",
            type="data",
            content="",
            created_by="charlie",
            created_at="2025-01-25T00:00:00Z",
            updated_at="2025-01-25T00:00:00Z",
        )

        with pytest.raises(AttributeError) as exc_info:
            _ = artifact.owner  # type: ignore[attr-defined]

        error_msg = str(exc_info.value)
        assert "owner" in error_msg
        assert "Did you mean 'created_by'" in error_msg

    def test_shows_available_attributes_for_unknown(self) -> None:
        """Test that unknown attributes show available list."""
        artifact = Artifact(
            id="test_artifact",
            type="data",
            content="",
            created_by="alice",
            created_at="2025-01-25T00:00:00Z",
            updated_at="2025-01-25T00:00:00Z",
        )

        with pytest.raises(AttributeError) as exc_info:
            _ = artifact.nonexistent_field  # type: ignore[attr-defined]

        error_msg = str(exc_info.value)
        assert "nonexistent_field" in error_msg
        assert "Available:" in error_msg
        assert "id" in error_msg
        assert "type" in error_msg
        assert "content" in error_msg


class TestMethodNotFoundError:
    """Tests for improved method-not-found error messages."""

    def test_method_not_found_suggests_describe(self) -> None:
        """Test that method_not_found error suggests using describe()."""
        from src.world.world import get_error_message

        error_msg = get_error_message(
            "method_not_found",
            method="run",
            artifact_id="my_service",
            methods=["list", "search", "describe"]
        )

        # Should mention the artifact
        assert "my_service" in error_msg
        # Should mention the failed method
        assert "run" in error_msg
        # Should list available methods
        assert "list" in error_msg
        assert "search" in error_msg
        # Should suggest using describe()
        assert "describe" in error_msg


class TestDescribeMethod:
    """Tests for the auto-describe method on artifacts."""

    def test_describe_intent_parses_correctly(self) -> None:
        """Test that describe method invocation parses correctly."""
        json_str = json.dumps({
            "action_type": "invoke_artifact",
            "artifact_id": "my_service",
            "method": "describe",
            "args": []
        })

        result = parse_intent_from_json("alice", json_str)
        assert isinstance(result, InvokeArtifactIntent)
        assert result.artifact_id == "my_service"
        assert result.method == "describe"
        assert result.args == []
