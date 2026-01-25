"""Tests for Plan #168: Artifact Metadata Field.

Tests that artifacts can have user-defined metadata for addressing,
categorization, and discovery.
"""

import pytest

from src.world.artifacts import Artifact, ArtifactStore
from src.world.actions import WriteArtifactIntent, parse_intent_from_json
from src.world.genesis.store import GenesisStore


@pytest.fixture
def artifact_store() -> ArtifactStore:
    """Create a fresh artifact store."""
    return ArtifactStore()


@pytest.fixture
def genesis_store(artifact_store: ArtifactStore) -> GenesisStore:
    """Create genesis store with artifact store."""
    return GenesisStore(artifact_store=artifact_store)


def call_method(store: GenesisStore, method_name: str, args: list, invoker: str) -> dict:
    """Helper to call a method on genesis store."""
    method = store.get_method(method_name)
    assert method is not None, f"Method {method_name} not found"
    return method.handler(args, invoker)


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

    def test_write_without_metadata_defaults_empty(self, artifact_store: ArtifactStore) -> None:
        """write() without metadata defaults to empty dict."""
        artifact = artifact_store.write(
            artifact_id="test",
            type="generic",
            content="content",
            created_by="alice",
        )
        assert artifact.metadata == {}


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


class TestGenesisStoreMetadataInResponses:
    """Test genesis_store includes metadata in responses."""

    def test_get_returns_metadata(
        self,
        artifact_store: ArtifactStore,
        genesis_store: GenesisStore,
    ) -> None:
        """genesis_store.get() returns artifact metadata."""
        metadata = {"recipient": "bob", "tags": ["urgent"]}
        artifact_store.write(
            artifact_id="msg_001",
            type="message",
            content="Hello",
            created_by="alice",
            metadata=metadata,
        )
        result = call_method(genesis_store, "get", ["msg_001"], "alice")
        assert result["success"] is True
        assert "metadata" in result["artifact"]
        assert result["artifact"]["metadata"] == metadata

    def test_list_returns_metadata(
        self,
        artifact_store: ArtifactStore,
        genesis_store: GenesisStore,
    ) -> None:
        """genesis_store.list() returns metadata for all artifacts."""
        artifact_store.write(
            artifact_id="msg_001",
            type="message",
            content="Hello",
            created_by="alice",
            metadata={"recipient": "bob"},
        )
        artifact_store.write(
            artifact_id="msg_002",
            type="message",
            content="Hi",
            created_by="alice",
            metadata={"recipient": "carol"},
        )
        result = call_method(genesis_store, "list", [], "alice")
        assert result["success"] is True

        artifacts_by_id = {a["id"]: a for a in result["artifacts"]}
        assert artifacts_by_id["msg_001"]["metadata"] == {"recipient": "bob"}
        assert artifacts_by_id["msg_002"]["metadata"] == {"recipient": "carol"}


class TestGenesisStoreMetadataFiltering:
    """Test genesis_store filtering by metadata fields."""

    def test_filter_by_metadata_field(
        self,
        artifact_store: ArtifactStore,
        genesis_store: GenesisStore,
    ) -> None:
        """genesis_store.list() filters by metadata fields."""
        artifact_store.write(
            artifact_id="msg_001",
            type="message",
            content="Hello Bob",
            created_by="alice",
            metadata={"recipient": "bob"},
        )
        artifact_store.write(
            artifact_id="msg_002",
            type="message",
            content="Hello Carol",
            created_by="alice",
            metadata={"recipient": "carol"},
        )
        artifact_store.write(
            artifact_id="msg_003",
            type="message",
            content="Hello Bob again",
            created_by="alice",
            metadata={"recipient": "bob"},
        )

        # Filter by metadata.recipient = "bob"
        result = call_method(
            genesis_store,
            "list",
            [{"metadata.recipient": "bob"}],
            "alice",
        )
        assert result["success"] is True
        assert result["count"] == 2

        ids = [a["id"] for a in result["artifacts"]]
        assert "msg_001" in ids
        assert "msg_003" in ids
        assert "msg_002" not in ids

    def test_filter_by_nested_metadata(
        self,
        artifact_store: ArtifactStore,
        genesis_store: GenesisStore,
    ) -> None:
        """genesis_store.list() filters by dot-notation metadata."""
        artifact_store.write(
            artifact_id="doc_001",
            type="document",
            content="Report",
            created_by="alice",
            metadata={"tags": {"priority": "high", "category": "report"}},
        )
        artifact_store.write(
            artifact_id="doc_002",
            type="document",
            content="Notes",
            created_by="alice",
            metadata={"tags": {"priority": "low", "category": "notes"}},
        )

        # Filter by metadata.tags.priority = "high"
        result = call_method(
            genesis_store,
            "list",
            [{"metadata.tags.priority": "high"}],
            "alice",
        )
        assert result["success"] is True
        assert result["count"] == 1
        assert result["artifacts"][0]["id"] == "doc_001"

    def test_filter_combined_with_type(
        self,
        artifact_store: ArtifactStore,
        genesis_store: GenesisStore,
    ) -> None:
        """Metadata filter works combined with type filter."""
        artifact_store.write(
            artifact_id="msg_001",
            type="message",
            content="Hello",
            created_by="alice",
            metadata={"priority": "high"},
        )
        artifact_store.write(
            artifact_id="doc_001",
            type="document",
            content="Report",
            created_by="alice",
            metadata={"priority": "high"},
        )

        # Filter by type=message AND metadata.priority=high
        result = call_method(
            genesis_store,
            "list",
            [{"type": "message", "metadata.priority": "high"}],
            "alice",
        )
        assert result["success"] is True
        assert result["count"] == 1
        assert result["artifacts"][0]["id"] == "msg_001"
