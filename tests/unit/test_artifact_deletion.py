"""Unit tests for artifact deletion - Plan #18"""

import pytest
import tempfile
from pathlib import Path

from src.world.world import World
from src.world.artifacts import Artifact, ArtifactStore


class TestArtifactDeletionFields:
    """Test that Artifact has deletion fields."""

    def test_artifact_has_deletion_fields(self) -> None:
        """Artifact dataclass has deleted, deleted_at, deleted_by fields."""
        artifact = Artifact(
            id="test",
            type="generic",
            content="test content",
            created_by="alice",
            created_at="2026-01-14T00:00:00",
            updated_at="2026-01-14T00:00:00",
        )
        assert artifact.deleted is False
        assert artifact.deleted_at is None
        assert artifact.deleted_by is None

    def test_artifact_to_dict_includes_deletion_fields_when_set(self) -> None:
        """to_dict() includes deletion fields when artifact is deleted."""
        artifact = Artifact(
            id="test",
            type="generic",
            content="test content",
            created_by="alice",
            created_at="2026-01-14T00:00:00",
            updated_at="2026-01-14T00:00:00",
            deleted=True,
            deleted_at="2026-01-14T01:00:00",
            deleted_by="alice",
        )
        d = artifact.to_dict()
        assert d["deleted"] is True
        assert d["deleted_at"] == "2026-01-14T01:00:00"
        assert d["deleted_by"] == "alice"

    def test_artifact_to_dict_excludes_deletion_fields_when_not_deleted(self) -> None:
        """to_dict() excludes deletion fields when artifact is not deleted."""
        artifact = Artifact(
            id="test",
            type="generic",
            content="test content",
            created_by="alice",
            created_at="2026-01-14T00:00:00",
            updated_at="2026-01-14T00:00:00",
        )
        d = artifact.to_dict()
        assert "deleted" not in d
        assert "deleted_at" not in d
        assert "deleted_by" not in d


class TestDeleteArtifactOwnerOnly:
    """Test that only owner can delete their artifact."""

    def test_owner_can_delete(self) -> None:
        """Owner can delete their artifact."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
                {"id": "bob", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Create artifact owned by alice
        world.artifacts.write(
            artifact_id="alice_artifact",
            type="generic",
            content="alice's stuff",
            created_by="alice",
        )

        # Alice can delete
        result = world.delete_artifact("alice_artifact", "alice")
        assert result["success"] is True

        # Verify artifact is marked deleted
        artifact = world.artifacts.get("alice_artifact")
        assert artifact is not None
        assert artifact.deleted is True
        assert artifact.deleted_by == "alice"
        assert artifact.deleted_at is not None

    def test_non_owner_cannot_delete(self) -> None:
        """Non-owner cannot delete an artifact."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
                {"id": "bob", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Create artifact owned by bob
        world.artifacts.write(
            artifact_id="bob_artifact",
            type="generic",
            content="bob's stuff",
            created_by="bob",
        )

        # Alice cannot delete bob's artifact
        result = world.delete_artifact("bob_artifact", "alice")
        assert result["success"] is False
        assert "owner" in result.get("error", "").lower()

        # Verify artifact is not deleted
        artifact = world.artifacts.get("bob_artifact")
        assert artifact is not None
        assert artifact.deleted is False


class TestDeleteGenesisForbidden:
    """Test that genesis artifacts cannot be deleted."""

    def test_cannot_delete_genesis_ledger(self) -> None:
        """Genesis artifacts cannot be deleted."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Try to delete genesis_ledger
        result = world.delete_artifact("genesis_ledger", "alice")
        assert result["success"] is False
        assert "genesis" in result.get("error", "").lower()

    def test_cannot_delete_genesis_store(self) -> None:
        """Genesis store cannot be deleted."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Try to delete genesis_store
        result = world.delete_artifact("genesis_store", "alice")
        assert result["success"] is False
        assert "genesis" in result.get("error", "").lower()


class TestInvokeDeletedArtifactFails:
    """Test that invoking deleted artifact returns DELETED error."""

    def test_invoke_deleted_artifact_fails(self) -> None:
        """Invoking deleted artifact returns DELETED error."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
                {"id": "bob", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Create executable artifact
        world.artifacts.write(
            artifact_id="exec_artifact",
            type="service",
            content="A service",
            created_by="alice",
            executable=True,
            code="def run(ctx): return {'result': 'ok'}",
        )

        # Delete it
        world.delete_artifact("exec_artifact", "alice")

        # Try to invoke - should fail with DELETED error
        result = world.invoke_artifact("bob", "exec_artifact", "run", [])
        assert result["success"] is False
        # Should mention deleted in error code or message
        error_code = result.get("error_code", "")
        error_msg = result.get("error", result.get("message", ""))
        assert error_code == "DELETED" or "deleted" in error_msg.lower()


class TestListExcludesDeletedByDefault:
    """Test that list_all() excludes deleted artifacts by default."""

    def test_list_excludes_deleted_by_default(self) -> None:
        """list_all() excludes deleted artifacts by default."""
        store = ArtifactStore()

        # Create two artifacts
        store.write("art1", "generic", "content1", "alice")
        store.write("art2", "generic", "content2", "alice")

        # Delete one
        artifact = store.get("art1")
        assert artifact is not None
        artifact.deleted = True
        artifact.deleted_at = "2026-01-14T00:00:00"
        artifact.deleted_by = "alice"

        # List should exclude deleted
        artifacts = store.list_all()
        ids = [a["id"] for a in artifacts]
        assert "art1" not in ids
        assert "art2" in ids

    def test_list_includes_deleted_with_flag(self) -> None:
        """list_all(include_deleted=True) includes deleted artifacts."""
        store = ArtifactStore()

        # Create two artifacts
        store.write("art1", "generic", "content1", "alice")
        store.write("art2", "generic", "content2", "alice")

        # Delete one
        artifact = store.get("art1")
        assert artifact is not None
        artifact.deleted = True
        artifact.deleted_at = "2026-01-14T00:00:00"
        artifact.deleted_by = "alice"

        # List with include_deleted=True should include both
        artifacts = store.list_all(include_deleted=True)
        ids = [a["id"] for a in artifacts]
        assert "art1" in ids
        assert "art2" in ids


class TestReadDeletedArtifactReturnsTombstone:
    """Test that reading deleted artifact returns tombstone metadata."""

    def test_read_deleted_artifact_returns_tombstone(self) -> None:
        """read_artifact on deleted artifact returns tombstone info."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Create and delete artifact
        world.artifacts.write(
            artifact_id="test_artifact",
            type="generic",
            content="test content",
            created_by="alice",
        )
        world.delete_artifact("test_artifact", "alice")

        # Read should return tombstone metadata
        result = world.read_artifact("alice", "test_artifact")
        assert result["deleted"] is True
        assert result.get("deleted_at") is not None
        assert result.get("deleted_by") == "alice"


class TestWriteDeletedArtifactFails:
    """Test that writing to deleted artifact fails."""

    def test_write_deleted_artifact_fails(self) -> None:
        """write_artifact on deleted artifact fails."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Create and delete artifact
        world.artifacts.write(
            artifact_id="test_artifact",
            type="generic",
            content="test content",
            created_by="alice",
        )
        world.delete_artifact("test_artifact", "alice")

        # Try to write - should fail
        result = world.write_artifact(
            agent_id="alice",
            artifact_id="test_artifact",
            artifact_type="generic",
            content="new content",
        )
        assert result["success"] is False
        assert "deleted" in result.get("message", result.get("error", "")).lower()


class TestDeleteNonexistentArtifact:
    """Test deleting nonexistent artifact."""

    def test_delete_nonexistent_artifact_fails(self) -> None:
        """Deleting nonexistent artifact fails gracefully."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "alice", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        result = world.delete_artifact("nonexistent", "alice")
        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()
