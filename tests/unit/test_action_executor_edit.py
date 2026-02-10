"""Tests for _execute_edit() in action_executor (Plan #239).

Tests that edit_artifact actions properly delegate to ArtifactStore.edit_artifact()
using old_string/new_string replacement (Claude Code-style editing).
"""

from pathlib import Path

import pytest

from src.world.world import World
from src.world.actions import (
    ActionResult, EditArtifactIntent, WriteArtifactIntent,
)
from src.world.errors import ErrorCode, ErrorCategory


@pytest.fixture
def world(tmp_path: Path) -> World:
    """Create a test World with two agents."""
    config = {
        "world": {},
        "principals": [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 100},
        ],
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
        "logging": {"output_file": str(tmp_path / "test.jsonl")},
        "resources": {
            "stock": {
                "disk": {"total": 20000, "unit": "bytes"},  # 10000 per agent
            }
        },
    }
    return World(config)


def _write_artifact(world: World, artifact_id: str, content: str,
                    principal_id: str = "alice", **kwargs: object) -> ActionResult:
    """Helper to write an artifact."""
    if "access_contract_id" not in kwargs:
        kwargs["access_contract_id"] = "kernel_contract_freeware"
    intent = WriteArtifactIntent(
        principal_id=principal_id,
        artifact_id=artifact_id,
        artifact_type="document",
        content=content,
        **kwargs,  # type: ignore[arg-type]
    )
    return world.execute_action(intent)


@pytest.mark.plans([239])
class TestExecuteEditSuccess:
    """Tests that edit_artifact works through the action executor."""

    def test_execute_edit_replaces_string(self, world: World) -> None:
        """edit_artifact should replace old_string with new_string in content."""
        _write_artifact(world, "doc1", "Hello world, this is a test.")

        intent = EditArtifactIntent("alice", "doc1", "Hello world", "Goodbye world")
        result = world.execute_action(intent)

        assert result.success is True
        artifact = world.artifacts.get("doc1")
        assert artifact is not None
        assert artifact.content == "Goodbye world, this is a test."

    def test_execute_edit_returns_size_delta(self, world: World) -> None:
        """edit_artifact should report size delta in result data."""
        _write_artifact(world, "doc1", "short")

        intent = EditArtifactIntent("alice", "doc1", "short", "much longer string")
        result = world.execute_action(intent)

        assert result.success is True
        assert result.data is not None
        assert result.data["size_delta"] > 0

    def test_execute_edit_multiline(self, world: World) -> None:
        """edit_artifact should handle multiline content."""
        content = "line1\nline2\nline3"
        _write_artifact(world, "doc1", content)

        intent = EditArtifactIntent("alice", "doc1", "line2", "modified")
        result = world.execute_action(intent)

        assert result.success is True
        artifact = world.artifacts.get("doc1")
        assert artifact is not None
        assert artifact.content == "line1\nmodified\nline3"


@pytest.mark.plans([239])
class TestExecuteEditNotFound:
    """Tests for missing artifact error handling."""

    def test_execute_edit_artifact_not_found(self, world: World) -> None:
        """edit_artifact should fail if artifact doesn't exist."""
        intent = EditArtifactIntent("alice", "nonexistent", "old", "new")
        result = world.execute_action(intent)

        assert result.success is False
        assert result.error_code == ErrorCode.NOT_FOUND.value

    def test_execute_edit_old_string_not_in_content(self, world: World) -> None:
        """edit_artifact should fail if old_string not found in content."""
        _write_artifact(world, "doc1", "Hello world")

        intent = EditArtifactIntent("alice", "doc1", "Goodbye", "Hi")
        result = world.execute_action(intent)

        assert result.success is False
        assert result.error_code == ErrorCode.INVALID_ARGUMENT.value

    def test_execute_edit_not_unique(self, world: World) -> None:
        """edit_artifact should fail if old_string appears multiple times."""
        _write_artifact(world, "doc1", "Hello Hello Hello")

        intent = EditArtifactIntent("alice", "doc1", "Hello", "Hi")
        result = world.execute_action(intent)

        assert result.success is False
        assert result.error_code == ErrorCode.INVALID_ARGUMENT.value


@pytest.mark.plans([239])
class TestExecuteEditKernelProtected:
    """Tests that kernel_protected artifacts cannot be edited."""

    def test_execute_edit_kernel_protected_blocked(self, world: World) -> None:
        """edit_artifact should block edits to kernel_protected artifacts."""
        _write_artifact(world, "protected_doc", "Some content")
        artifact = world.artifacts.get("protected_doc")
        assert artifact is not None
        artifact.kernel_protected = True

        intent = EditArtifactIntent("alice", "protected_doc", "Some", "Other")
        result = world.execute_action(intent)

        assert result.success is False
        assert result.error_code == ErrorCode.NOT_AUTHORIZED.value
        assert "kernel_protected" in result.message


@pytest.mark.plans([239])
class TestExecuteEditPermission:
    """Tests that edit respects contract-based permissions."""

    def test_execute_edit_private_artifact_blocked_for_non_owner(self, world: World) -> None:
        """edit_artifact should block non-owner edits on private artifacts."""
        _write_artifact(world, "private_doc", "Secret content",
                        principal_id="alice",
                        access_contract_id="kernel_contract_private")

        intent = EditArtifactIntent("bob", "private_doc", "Secret", "Public")
        result = world.execute_action(intent)

        assert result.success is False
        assert result.error_code == ErrorCode.NOT_AUTHORIZED.value

    def test_execute_edit_private_artifact_allowed_for_owner(self, world: World) -> None:
        """edit_artifact should allow owner to edit their private artifact."""
        _write_artifact(world, "private_doc", "Secret content",
                        principal_id="alice",
                        access_contract_id="kernel_contract_private")

        intent = EditArtifactIntent("alice", "private_doc", "Secret", "Updated")
        result = world.execute_action(intent)

        assert result.success is True
        artifact = world.artifacts.get("private_doc")
        assert artifact is not None
        assert artifact.content == "Updated content"
