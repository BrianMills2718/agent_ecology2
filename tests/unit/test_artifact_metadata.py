"""Tests for Plan #168: Artifact Metadata Field.

Tests that artifacts can have user-defined metadata for addressing,
categorization, and discovery.
"""

import pytest

from src.world.artifacts import Artifact, ArtifactStore
from src.world.actions import WriteArtifactIntent, parse_intent_from_json


@pytest.fixture
def artifact_store() -> ArtifactStore:
    """Create a fresh artifact store."""
    return ArtifactStore()


class TestArtifactMetadataField:
    """Test that Artifact has metadata field."""

    def test_artifact_has_metadata_field(self) -> None:
        """Artifact dataclass has metadata field defaulting to empty dict."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        artifact = Artifact(
            id="test",
            type="generic",
            content="test content",
            created_by="alice",
            created_at=now,
            updated_at=now,
        )
        assert hasattr(artifact, "metadata")
        assert artifact.metadata == {}

    def test_artifact_with_metadata(self) -> None:
        """Artifact can be created with metadata."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        metadata = {"recipient": "bob", "priority": "high", "tags": ["urgent"]}
        artifact = Artifact(
            id="test",
            type="generic",
            content="test content",
            created_by="alice",
            created_at=now,
            updated_at=now,
            metadata=metadata,
        )
        assert artifact.metadata == metadata
        assert artifact.metadata["recipient"] == "bob"

    def test_to_dict_includes_metadata(self) -> None:
        """Artifact.to_dict() includes metadata when present."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        metadata = {"recipient": "bob"}
        artifact = Artifact(
            id="test",
            type="generic",
            content="test content",
            created_by="alice",
            created_at=now,
            updated_at=now,
            metadata=metadata,
        )
        d = artifact.to_dict()
        assert "metadata" in d
        assert d["metadata"] == {"recipient": "bob"}

    def test_to_dict_omits_empty_metadata(self) -> None:
        """Artifact.to_dict() omits metadata when empty."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        artifact = Artifact(
            id="test",
            type="generic",
            content="test content",
            created_by="alice",
            created_at=now,
            updated_at=now,
        )
        d = artifact.to_dict()
        # Empty metadata should be omitted to keep responses clean
        assert "metadata" not in d or d.get("metadata") == {}


class TestArtifactStoreWriteWithMetadata:
    """Test ArtifactStore.write() with metadata."""

    def test_write_with_metadata(self, artifact_store: ArtifactStore) -> None:
        """write() accepts and stores metadata."""
        metadata = {"recipient": "bob", "category": "message"}
        artifact = artifact_store.write(
            artifact_id="msg_001",
            type="message",
            content="Hello Bob",
            created_by="alice",
            metadata=metadata,
        )
        assert artifact.metadata == metadata

    def test_write_updates_metadata(self, artifact_store: ArtifactStore) -> None:
        """Updating artifact replaces metadata."""
        # Create with initial metadata
        artifact_store.write(
            artifact_id="msg_001",
            type="message",
            content="Hello",
            created_by="alice",
            metadata={"v": 1},
        )
        # Update with new metadata
        artifact = artifact_store.write(
            artifact_id="msg_001",
            type="message",
            content="Hello again",
            created_by="alice",
            metadata={"v": 2, "edited": True},
        )
        assert artifact.metadata == {"v": 2, "edited": True}

    def test_write_without_metadata_auto_populates_auth(self, artifact_store: ArtifactStore) -> None:
        """write() without metadata auto-populates writer in state (ADR-0028)."""
        artifact = artifact_store.write(
            artifact_id="test",
            type="generic",
            content="content",
            created_by="alice",
        )
        # ADR-0028: freeware artifacts auto-populate writer in state from created_by
        assert artifact.state["writer"] == "alice"


class TestWriteArtifactIntentMetadata:
    """Test WriteArtifactIntent supports metadata."""

    def test_intent_accepts_metadata(self) -> None:
        """WriteArtifactIntent can be created with metadata."""
        metadata = {"recipient": "bob"}
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="msg_001",
            artifact_type="message",
            content="Hello",
            metadata=metadata,
        )
        assert intent.metadata == metadata

    def test_intent_to_dict_includes_metadata(self) -> None:
        """WriteArtifactIntent.to_dict() includes metadata."""
        metadata = {"recipient": "bob"}
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="msg_001",
            artifact_type="message",
            content="Hello",
            metadata=metadata,
        )
        d = intent.to_dict()
        assert "metadata" in d
        assert d["metadata"] == metadata


class TestParseIntentWithMetadata:
    """Test parse_intent_from_json handles metadata."""

    def test_parse_write_with_metadata(self) -> None:
        """parse_intent_from_json extracts metadata for write_artifact."""
        json_str = """{
            "action_type": "write_artifact",
            "artifact_id": "msg_001",
            "artifact_type": "message",
            "content": "Hello Bob",
            "metadata": {"recipient": "bob", "priority": "high"}
        }"""
        result = parse_intent_from_json("alice", json_str)
        assert isinstance(result, WriteArtifactIntent)
        assert result.metadata == {"recipient": "bob", "priority": "high"}

    def test_parse_write_without_metadata(self) -> None:
        """parse_intent_from_json works without metadata."""
        json_str = """{
            "action_type": "write_artifact",
            "artifact_id": "test",
            "artifact_type": "generic",
            "content": "content"
        }"""
        result = parse_intent_from_json("alice", json_str)
        assert isinstance(result, WriteArtifactIntent)
        assert result.metadata is None

    def test_parse_write_invalid_metadata(self) -> None:
        """parse_intent_from_json rejects non-dict metadata."""
        json_str = """{
            "action_type": "write_artifact",
            "artifact_id": "test",
            "artifact_type": "generic",
            "content": "content",
            "metadata": "not a dict"
        }"""
        result = parse_intent_from_json("alice", json_str)
        assert isinstance(result, str)  # Error message
        assert "metadata must be a dict" in result.lower()
