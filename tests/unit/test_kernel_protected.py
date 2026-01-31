"""Tests for kernel-protected artifact fields (Plan #235 Phase 0).

Phase 0 closes two confirmed authorization bypasses:
- FM-6: type is immutable after creation
- FM-7: access_contract_id is creator-only
"""

import pytest

from src.world.artifacts import ArtifactStore


class TestTypeImmutability:
    """FM-6: type field cannot be changed after creation."""

    def test_type_flip_to_right_blocked(self) -> None:
        """Cannot change artifact type to 'right' after creation."""
        store = ArtifactStore()
        store.write("test-artifact", "document", "content", "agent1")

        with pytest.raises(ValueError, match="Cannot change artifact type"):
            store.write("test-artifact", "right", "content", "agent1")

    def test_type_flip_to_trigger_blocked(self) -> None:
        """Cannot change artifact type to 'trigger' after creation."""
        store = ArtifactStore()
        store.write("test-artifact", "document", "content", "agent1")

        with pytest.raises(ValueError, match="Cannot change artifact type"):
            store.write("test-artifact", "trigger", "content", "agent1")

    def test_type_flip_to_config_blocked(self) -> None:
        """Cannot change artifact type to 'config' after creation."""
        store = ArtifactStore()
        store.write("test-artifact", "document", "content", "agent1")

        with pytest.raises(ValueError, match="Cannot change artifact type"):
            store.write("test-artifact", "config", "content", "agent1")

    def test_type_unchanged_write_succeeds(self) -> None:
        """Writing with same type succeeds (normal update path)."""
        store = ArtifactStore()
        store.write("test-artifact", "document", "old content", "agent1")
        artifact = store.write("test-artifact", "document", "new content", "agent1")
        assert artifact.content == "new content"
        assert artifact.type == "document"

    def test_type_set_on_create(self) -> None:
        """Type can be set freely on first creation."""
        store = ArtifactStore()
        artifact = store.write("test-artifact", "trigger", "content", "agent1")
        assert artifact.type == "trigger"


class TestCreatorOnlyAccessContract:
    """FM-7: Only the creator can change access_contract_id."""

    def test_non_creator_cannot_swap_access_contract(self) -> None:
        """Non-creator write cannot change access_contract_id."""
        store = ArtifactStore()
        store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="genesis_contract_private",
        )

        # Attacker tries to swap to freeware
        with pytest.raises(PermissionError, match="Only creator .* can change access_contract_id"):
            store.write(
                "test-artifact", "document", "content", "attacker",
                access_contract_id="genesis_contract_freeware",
            )

    def test_creator_can_change_access_contract(self) -> None:
        """Creator CAN change access_contract_id."""
        store = ArtifactStore()
        store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="genesis_contract_private",
        )

        # Creator changes to freeware - should succeed
        artifact = store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="genesis_contract_freeware",
        )
        assert artifact.access_contract_id == "genesis_contract_freeware"

    def test_authorized_writer_cannot_swap_access_contract(self) -> None:
        """An authorized writer (not creator) cannot swap access_contract_id."""
        store = ArtifactStore()
        store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="genesis_contract_private",
        )

        # authorized_writer tries to change contract
        with pytest.raises(PermissionError, match="Only creator .* can change access_contract_id"):
            store.write(
                "test-artifact", "document", "hacked content", "authorized_writer",
                access_contract_id="genesis_contract_freeware",
            )

    def test_access_contract_unchanged_write_succeeds(self) -> None:
        """Writing with same access_contract_id succeeds for any caller."""
        store = ArtifactStore()
        store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="genesis_contract_private",
        )

        # Different caller writes with same contract - should succeed
        artifact = store.write(
            "test-artifact", "document", "updated", "other_agent",
            access_contract_id="genesis_contract_private",
        )
        assert artifact.content == "updated"
        assert artifact.access_contract_id == "genesis_contract_private"

    def test_access_contract_none_on_update_leaves_unchanged(self) -> None:
        """Passing access_contract_id=None on update preserves existing value."""
        store = ArtifactStore()
        store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="genesis_contract_private",
        )

        # Update without specifying access_contract_id
        artifact = store.write(
            "test-artifact", "document", "updated", "other_agent",
        )
        assert artifact.access_contract_id == "genesis_contract_private"

    def test_access_contract_set_on_create(self) -> None:
        """access_contract_id can be set freely on first creation."""
        store = ArtifactStore()
        artifact = store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="genesis_contract_private",
        )
        assert artifact.access_contract_id == "genesis_contract_private"
