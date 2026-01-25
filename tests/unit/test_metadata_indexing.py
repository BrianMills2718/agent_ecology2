"""Unit tests for Plan #182: Metadata Indexing for O(1) artifact queries."""

import pytest

from src.world.artifacts import ArtifactStore


class TestMetadataIndexing:
    """Tests for O(1) index lookups in ArtifactStore."""

    def test_index_by_type_on_write(self) -> None:
        """Artifacts are indexed by type when written."""
        store = ArtifactStore()
        store.write(
            artifact_id="test_data",
            type="data",
            content="hello",
            created_by="alice",
        )
        store.write(
            artifact_id="test_agent",
            type="agent",
            content="agent config",
            created_by="alice",
        )

        # Verify type index
        assert "test_data" in store._index_by_type["data"]
        assert "test_agent" in store._index_by_type["agent"]
        assert "test_data" not in store._index_by_type["agent"]

    def test_index_by_creator_on_write(self) -> None:
        """Artifacts are indexed by owner when written."""
        store = ArtifactStore()
        store.write(
            artifact_id="art1",
            type="data",
            content="hello",
            created_by="alice",
        )
        store.write(
            artifact_id="art2",
            type="data",
            content="world",
            created_by="bob",
        )

        # Verify owner index
        assert "art1" in store._index_by_creator["alice"]
        assert "art2" in store._index_by_creator["bob"]
        assert "art1" not in store._index_by_creator["bob"]

    def test_index_by_metadata_on_write(self) -> None:
        """Artifacts are indexed by configured metadata fields when written."""
        store = ArtifactStore(indexed_metadata_fields=["recipient", "channel"])
        store.write(
            artifact_id="msg1",
            type="message",
            content="hello",
            created_by="alice",
            metadata={"recipient": "bob", "channel": "general"},
        )
        store.write(
            artifact_id="msg2",
            type="message",
            content="world",
            created_by="alice",
            metadata={"recipient": "charlie", "channel": "general"},
        )

        # Verify metadata indexes
        assert "msg1" in store._index_by_metadata["recipient"]["bob"]
        assert "msg2" in store._index_by_metadata["recipient"]["charlie"]
        assert "msg1" in store._index_by_metadata["channel"]["general"]
        assert "msg2" in store._index_by_metadata["channel"]["general"]

    def test_index_updated_on_type_change(self) -> None:
        """Type index is updated when artifact type changes."""
        store = ArtifactStore()
        store.write(
            artifact_id="art1",
            type="data",
            content="hello",
            created_by="alice",
        )
        assert "art1" in store._index_by_type["data"]

        # Update type
        store.write(
            artifact_id="art1",
            type="executable",
            content="code",
            created_by="alice",
            executable=True,
            code="def run(): pass",
        )

        # Old type should not have it, new type should
        assert "art1" not in store._index_by_type["data"]
        assert "art1" in store._index_by_type["executable"]

    def test_index_updated_on_metadata_change(self) -> None:
        """Metadata index is updated when metadata changes."""
        store = ArtifactStore(indexed_metadata_fields=["status"])
        store.write(
            artifact_id="task1",
            type="task",
            content="task content",
            created_by="alice",
            metadata={"status": "pending"},
        )
        assert "task1" in store._index_by_metadata["status"]["pending"]

        # Update metadata
        store.write(
            artifact_id="task1",
            type="task",
            content="task content",
            created_by="alice",
            metadata={"status": "complete"},
        )

        # Old value should not have it, new value should
        assert "task1" not in store._index_by_metadata["status"]["pending"]
        assert "task1" in store._index_by_metadata["status"]["complete"]

    def test_transfer_ownership_does_not_update_creator_index(self) -> None:
        """Creator index is NOT updated when transfer_ownership is called (ADR-0016).

        Per ADR-0016: created_by is immutable, so _index_by_creator should not
        change. transfer_ownership() sets metadata["controller"] but the
        original creator remains indexed.
        """
        store = ArtifactStore()
        store.write(
            artifact_id="art1",
            type="data",
            content="hello",
            created_by="alice",
        )
        assert "art1" in store._index_by_creator["alice"]

        # transfer_ownership sets metadata["controller"], not created_by
        store.transfer_ownership("art1", "alice", "bob")

        # Creator index is unchanged (alice still created it)
        assert "art1" in store._index_by_creator["alice"]
        # Bob didn't create it, so he's not in the creator index
        assert "art1" not in store._index_by_creator.get("bob", set())
        # metadata["controller"] is set (but doesn't affect freeware access)
        artifact = store.get("art1")
        assert artifact is not None
        assert artifact.metadata.get("controller") == "bob"

    def test_query_by_type(self) -> None:
        """query_by_type returns correct results using index."""
        store = ArtifactStore()
        store.write(artifact_id="data1", type="data", content="x", created_by="alice")
        store.write(artifact_id="data2", type="data", content="y", created_by="bob")
        store.write(artifact_id="agent1", type="agent", content="z", created_by="alice")

        results = store.query_by_type("data")
        assert len(results) == 2
        ids = {a.id for a in results}
        assert ids == {"data1", "data2"}

    def test_query_by_owner(self) -> None:
        """query_by_owner returns correct results using index."""
        store = ArtifactStore()
        store.write(artifact_id="art1", type="data", content="x", created_by="alice")
        store.write(artifact_id="art2", type="data", content="y", created_by="alice")
        store.write(artifact_id="art3", type="data", content="z", created_by="bob")

        results = store.query_by_owner("alice")
        assert len(results) == 2
        ids = {a.id for a in results}
        assert ids == {"art1", "art2"}

    def test_query_by_metadata(self) -> None:
        """query_by_metadata returns correct results using index."""
        store = ArtifactStore(indexed_metadata_fields=["recipient"])
        store.write(
            artifact_id="msg1",
            type="message",
            content="hello",
            created_by="alice",
            metadata={"recipient": "bob"},
        )
        store.write(
            artifact_id="msg2",
            type="message",
            content="world",
            created_by="alice",
            metadata={"recipient": "bob"},
        )
        store.write(
            artifact_id="msg3",
            type="message",
            content="!",
            created_by="alice",
            metadata={"recipient": "charlie"},
        )

        results = store.query_by_metadata("recipient", "bob")
        assert len(results) == 2
        ids = {a.id for a in results}
        assert ids == {"msg1", "msg2"}

    def test_query_by_metadata_returns_empty_for_unindexed_field(self) -> None:
        """query_by_metadata returns empty list for non-indexed fields."""
        store = ArtifactStore(indexed_metadata_fields=["recipient"])  # only recipient indexed
        store.write(
            artifact_id="msg1",
            type="message",
            content="hello",
            created_by="alice",
            metadata={"recipient": "bob", "channel": "general"},
        )

        # channel is not indexed
        results = store.query_by_metadata("channel", "general")
        assert results == []

    def test_is_field_indexed(self) -> None:
        """is_field_indexed correctly reports indexed fields."""
        store = ArtifactStore(indexed_metadata_fields=["recipient", "channel"])
        assert store.is_field_indexed("recipient") is True
        assert store.is_field_indexed("channel") is True
        assert store.is_field_indexed("status") is False

    def test_add_indexed_field(self) -> None:
        """add_indexed_field indexes all existing artifacts."""
        store = ArtifactStore()  # No fields indexed initially
        store.write(
            artifact_id="msg1",
            type="message",
            content="hello",
            created_by="alice",
            metadata={"status": "pending"},
        )
        store.write(
            artifact_id="msg2",
            type="message",
            content="world",
            created_by="alice",
            metadata={"status": "complete"},
        )

        # Add index after artifacts exist
        store.add_indexed_field("status")

        # Verify indexing
        assert store.is_field_indexed("status")
        assert "msg1" in store._index_by_metadata["status"]["pending"]
        assert "msg2" in store._index_by_metadata["status"]["complete"]

    def test_get_indexed_fields(self) -> None:
        """get_indexed_fields returns a copy of indexed fields."""
        store = ArtifactStore(indexed_metadata_fields=["a", "b"])
        fields = store.get_indexed_fields()
        assert fields == {"a", "b"}
        # Verify it's a copy
        fields.add("c")
        assert "c" not in store._indexed_metadata_fields

    def test_list_by_owner_uses_index(self) -> None:
        """list_by_owner uses the owner index for O(1) lookup."""
        store = ArtifactStore()
        store.write(artifact_id="art1", type="data", content="x", created_by="alice")
        store.write(artifact_id="art2", type="data", content="y", created_by="alice")
        store.write(artifact_id="art3", type="data", content="z", created_by="bob")

        results = store.list_by_owner("alice")
        assert len(results) == 2
        ids = {r["id"] for r in results}
        assert ids == {"art1", "art2"}

    def test_get_artifacts_by_owner_uses_index(self) -> None:
        """get_artifacts_by_owner uses the owner index for O(1) lookup."""
        store = ArtifactStore()
        store.write(artifact_id="art1", type="data", content="x", created_by="alice")
        store.write(artifact_id="art2", type="data", content="y", created_by="alice")
        store.write(artifact_id="art3", type="data", content="z", created_by="bob")

        ids = store.get_artifacts_by_owner("alice")
        assert set(ids) == {"art1", "art2"}

    def test_get_owner_usage_uses_index(self) -> None:
        """get_owner_usage uses the owner index for O(1) lookup."""
        store = ArtifactStore()
        store.write(artifact_id="art1", type="data", content="hello", created_by="alice")
        store.write(artifact_id="art2", type="data", content="world", created_by="alice")
        store.write(artifact_id="art3", type="data", content="big content", created_by="bob")

        usage = store.get_owner_usage("alice")
        # Content sizes: "hello" (5) + "world" (5) = 10
        assert usage == 10

    def test_nested_metadata_field_indexing(self) -> None:
        """Nested metadata fields (dot notation) can be indexed."""
        store = ArtifactStore(indexed_metadata_fields=["tags.priority"])
        store.write(
            artifact_id="task1",
            type="task",
            content="high priority task",
            created_by="alice",
            metadata={"tags": {"priority": "high", "category": "work"}},
        )
        store.write(
            artifact_id="task2",
            type="task",
            content="low priority task",
            created_by="alice",
            metadata={"tags": {"priority": "low"}},
        )

        # Query by nested field
        results = store.query_by_metadata("tags.priority", "high")
        assert len(results) == 1
        assert results[0].id == "task1"

    def test_metadata_with_none_value_not_indexed(self) -> None:
        """Metadata fields with None values are not indexed."""
        store = ArtifactStore(indexed_metadata_fields=["status"])
        store.write(
            artifact_id="art1",
            type="data",
            content="x",
            created_by="alice",
            metadata={"status": None},
        )

        # Should not appear in index
        assert store._index_by_metadata.get("status", {}).get(None, set()) == set()

    def test_empty_metadata_not_indexed(self) -> None:
        """Artifacts without metadata don't cause index issues."""
        store = ArtifactStore(indexed_metadata_fields=["status"])
        store.write(
            artifact_id="art1",
            type="data",
            content="x",
            created_by="alice",
            # No metadata
        )

        # Should work fine - no crashes, no spurious index entries
        assert "art1" not in store._index_by_metadata.get("status", {}).get(None, set())
