"""Tests for edit_artifact functionality (Plan #131)

Tests for Claude Code-style artifact editing using old_string/new_string replacement.
"""

import pytest

from src.world.artifacts import ArtifactStore


class TestArtifactStoreEdit:
    """Tests for ArtifactStore.edit_artifact method"""

    def test_edit_artifact_success(self) -> None:
        """edit_artifact should successfully replace unique string"""
        store = ArtifactStore()
        store.write("doc1", "document", "Hello world, this is a test.", "agent1")

        result = store.edit_artifact("doc1", "Hello world", "Goodbye world")

        assert result["success"] is True
        assert "Edited" in result["message"]
        artifact = store.get("doc1")
        assert artifact is not None
        assert artifact.content == "Goodbye world, this is a test."

    def test_edit_artifact_not_found(self) -> None:
        """edit_artifact should fail if artifact doesn't exist"""
        store = ArtifactStore()

        result = store.edit_artifact("nonexistent", "old", "new")

        assert result["success"] is False
        assert "not found" in result["message"].lower()
        data = result.get("data") or {}
        assert data.get("error") == "not_found"

    def test_edit_artifact_old_string_not_in_content(self) -> None:
        """edit_artifact should fail if old_string not in content"""
        store = ArtifactStore()
        store.write("doc1", "document", "Hello world", "agent1")

        result = store.edit_artifact("doc1", "Goodbye", "Hi")

        assert result["success"] is False
        assert "not found" in result["message"].lower()
        data = result.get("data") or {}
        assert data.get("error") == "not_found_in_content"

    def test_edit_artifact_old_string_not_unique(self) -> None:
        """edit_artifact should fail if old_string appears multiple times"""
        store = ArtifactStore()
        store.write("doc1", "document", "Hello Hello Hello", "agent1")

        result = store.edit_artifact("doc1", "Hello", "Hi")

        assert result["success"] is False
        assert "not unique" in result["message"].lower() or "3 times" in result["message"]
        data = result.get("data") or {}
        assert data.get("error") == "not_unique"
        assert data.get("count") == 3

    def test_edit_artifact_same_strings(self) -> None:
        """edit_artifact should fail if old_string equals new_string"""
        store = ArtifactStore()
        store.write("doc1", "document", "Hello world", "agent1")

        result = store.edit_artifact("doc1", "Hello", "Hello")

        assert result["success"] is False
        assert "different" in result["message"].lower()
        data = result.get("data") or {}
        assert data.get("error") == "no_change"

    def test_edit_artifact_deleted_artifact(self) -> None:
        """edit_artifact should fail if artifact is deleted"""
        store = ArtifactStore()
        store.write("doc1", "document", "Hello world", "agent1")
        artifact = store.get("doc1")
        assert artifact is not None
        artifact.deleted = True

        result = store.edit_artifact("doc1", "Hello", "Hi")

        assert result["success"] is False
        assert "deleted" in result["message"].lower()
        data = result.get("data") or {}
        assert data.get("error") == "deleted"

    def test_edit_artifact_updates_timestamp(self) -> None:
        """edit_artifact should update the artifact's updated_at timestamp"""
        store = ArtifactStore()
        store.write("doc1", "document", "Hello world", "agent1")
        artifact = store.get("doc1")
        assert artifact is not None
        original_updated = artifact.updated_at

        # Small delay to ensure timestamp changes
        import time
        time.sleep(0.01)

        result = store.edit_artifact("doc1", "Hello", "Hi")

        assert result["success"] is True
        artifact = store.get("doc1")
        assert artifact is not None
        assert artifact.updated_at != original_updated

    def test_edit_artifact_preserves_other_fields(self) -> None:
        """edit_artifact should only change content and updated_at"""
        store = ArtifactStore()
        store.write("doc1", "document", "Hello world", "agent1")
        artifact = store.get("doc1")
        assert artifact is not None
        original_created_at = artifact.created_at
        original_created_by = artifact.created_by
        original_type = artifact.type

        result = store.edit_artifact("doc1", "Hello", "Hi")

        assert result["success"] is True
        artifact = store.get("doc1")
        assert artifact is not None
        assert artifact.created_at == original_created_at
        assert artifact.created_by == original_created_by
        assert artifact.type == original_type

    def test_edit_artifact_with_special_characters(self) -> None:
        """edit_artifact should handle special characters in strings"""
        store = ArtifactStore()
        store.write("doc1", "document", 'def run():\n    return {"key": "value"}', "agent1")

        result = store.edit_artifact("doc1", '"value"', '"new_value"')

        assert result["success"] is True
        artifact = store.get("doc1")
        assert artifact is not None
        assert artifact.content == 'def run():\n    return {"key": "new_value"}'

    def test_edit_artifact_with_multiline_string(self) -> None:
        """edit_artifact should handle multiline strings"""
        store = ArtifactStore()
        original_content = """Line 1
Line 2
Line 3"""
        store.write("doc1", "document", original_content, "agent1")

        result = store.edit_artifact("doc1", "Line 2", "Modified Line")

        assert result["success"] is True
        artifact = store.get("doc1")
        assert artifact is not None
        expected = """Line 1
Modified Line
Line 3"""
        assert artifact.content == expected

    def test_edit_artifact_empty_new_string(self) -> None:
        """edit_artifact should allow replacing with empty string (deletion)"""
        store = ArtifactStore()
        store.write("doc1", "document", "Hello world", "agent1")

        result = store.edit_artifact("doc1", " world", "")

        assert result["success"] is True
        artifact = store.get("doc1")
        assert artifact is not None
        assert artifact.content == "Hello"
