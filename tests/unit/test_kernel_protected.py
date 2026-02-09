"""Tests for kernel-protected artifact fields (Plan #235).

Phase 0 closes two confirmed authorization bypasses:
- FM-6: type is immutable after creation
- FM-7: access_contract_id is creator-only

Phase 1 adds kernel_protected flag and reserved ID namespace:
- FM-1: kernel_protected must not be user-writable
- FM-2: Protection surface must be precise (content, code, metadata)
- FM-3: System fields immutable regardless of protection
- FM-4: Reserved ID namespace enforcement
- Kernel primitive: modify_protected_content() bypass for kernel use
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
            access_contract_id="kernel_contract_private",
        )

        # Attacker tries to swap to freeware
        with pytest.raises(PermissionError, match="Only creator .* can change access_contract_id"):
            store.write(
                "test-artifact", "document", "content", "attacker",
                access_contract_id="kernel_contract_freeware",
            )

    def test_creator_can_change_access_contract(self) -> None:
        """Creator CAN change access_contract_id."""
        store = ArtifactStore()
        store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="kernel_contract_private",
        )

        # Creator changes to freeware - should succeed
        artifact = store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="kernel_contract_freeware",
        )
        assert artifact.access_contract_id == "kernel_contract_freeware"

    def test_writer_cannot_swap_access_contract(self) -> None:
        """A writer (not creator) cannot swap access_contract_id."""
        store = ArtifactStore()
        store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="kernel_contract_private",
        )

        # writer tries to change contract
        with pytest.raises(PermissionError, match="Only creator .* can change access_contract_id"):
            store.write(
                "test-artifact", "document", "hacked content", "writer",
                access_contract_id="kernel_contract_freeware",
            )

    def test_access_contract_unchanged_write_succeeds(self) -> None:
        """Writing with same access_contract_id succeeds for any caller."""
        store = ArtifactStore()
        store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="kernel_contract_private",
        )

        # Different caller writes with same contract - should succeed
        artifact = store.write(
            "test-artifact", "document", "updated", "other_agent",
            access_contract_id="kernel_contract_private",
        )
        assert artifact.content == "updated"
        assert artifact.access_contract_id == "kernel_contract_private"

    def test_access_contract_none_on_update_leaves_unchanged(self) -> None:
        """Passing access_contract_id=None on update preserves existing value."""
        store = ArtifactStore()
        store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="kernel_contract_private",
        )

        # Update without specifying access_contract_id
        artifact = store.write(
            "test-artifact", "document", "updated", "other_agent",
        )
        assert artifact.access_contract_id == "kernel_contract_private"

    def test_access_contract_set_on_create(self) -> None:
        """access_contract_id can be set freely on first creation."""
        store = ArtifactStore()
        artifact = store.write(
            "test-artifact", "document", "content", "creator1",
            access_contract_id="kernel_contract_private",
        )
        assert artifact.access_contract_id == "kernel_contract_private"


# ---------------------------------------------------------------------------
# Phase 1: kernel_protected flag and reserved ID namespace
# ---------------------------------------------------------------------------


class TestKernelProtectedUserWrite:
    """FM-1: kernel_protected must not be user-writable.

    Once kernel_protected=True is set on an artifact (a system-level field),
    normal store.write() calls must be rejected with PermissionError.
    """

    def test_edit_blocked_on_protected_artifact(self) -> None:
        """store.write() update is rejected when kernel_protected=True."""
        store = ArtifactStore()
        artifact = store.write("sys-artifact", "document", "original", "system")
        artifact.kernel_protected = True  # System-level flag set directly

        with pytest.raises(PermissionError, match="kernel_protected"):
            store.write("sys-artifact", "document", "hacked", "attacker")

    def test_write_blocked_on_protected_artifact(self) -> None:
        """write() is the common path -- even the creator is blocked."""
        store = ArtifactStore()
        artifact = store.write("sys-artifact", "document", "original", "creator1")
        artifact.kernel_protected = True

        with pytest.raises(PermissionError, match="kernel_protected"):
            store.write("sys-artifact", "document", "updated", "creator1")

    def test_cannot_toggle_kernel_protected_via_metadata(self) -> None:
        """kernel_protected is a system field, not metadata -- metadata dict cannot affect it."""
        store = ArtifactStore()
        artifact = store.write(
            "sys-artifact", "document", "content", "agent1",
            metadata={"kernel_protected": True},
        )
        # The metadata dict may contain "kernel_protected" as a user key,
        # but it must NOT affect the actual system field.
        assert not getattr(artifact, "kernel_protected", False)


class TestProtectionSurface:
    """FM-2: Protection surface must be precise.

    A kernel_protected artifact rejects changes to content, code, AND metadata.
    """

    def test_protection_covers_content(self) -> None:
        """Protected artifact rejects content change."""
        store = ArtifactStore()
        artifact = store.write("protected-doc", "document", "sacred text", "system")
        artifact.kernel_protected = True

        with pytest.raises(PermissionError, match="kernel_protected"):
            store.write("protected-doc", "document", "defaced text", "attacker")

    def test_protection_covers_code(self) -> None:
        """Protected artifact rejects code change."""
        store = ArtifactStore()
        artifact = store.write(
            "protected-contract", "contract", "content", "system",
            executable=True, code="def run(): pass",
        )
        artifact.kernel_protected = True

        with pytest.raises(PermissionError, match="kernel_protected"):
            store.write(
                "protected-contract", "contract", "content", "attacker",
                executable=True, code="def run(): steal()",
            )

    def test_protection_covers_metadata(self) -> None:
        """Protected artifact rejects metadata change."""
        store = ArtifactStore()
        artifact = store.write(
            "protected-meta", "document", "content", "system",
            metadata={"version": 1},
        )
        artifact.kernel_protected = True

        with pytest.raises(PermissionError, match="kernel_protected"):
            store.write(
                "protected-meta", "document", "content", "attacker",
                metadata={"version": 999},
            )


class TestKernelProtectedImmutability:
    """FM-3: kernel_protected itself cannot be toggled off by users.

    Once set to True, only the kernel (via modify_protected_content) can
    change the artifact. There is no user-facing path to set it back to False.
    (Type immutability is covered by Phase 0 FM-6 tests above.)
    """

    def test_kernel_protected_cannot_be_toggled_off(self) -> None:
        """A user cannot flip kernel_protected from True to False."""
        store = ArtifactStore()
        artifact = store.write("locked-artifact", "document", "content", "system")
        artifact.kernel_protected = True

        # Even if somehow the caller tries to write, the flag stays True
        # and the write is rejected -- the flag itself cannot be cleared.
        with pytest.raises(PermissionError, match="kernel_protected"):
            store.write("locked-artifact", "document", "content", "system")


class TestReservedIDNamespace:
    """FM-4: Reserved ID namespace enforcement.

    Certain ID prefixes are reserved:
    - "charge_delegation:<owner>" can only be created by <owner>
    - "right:*" can only be created by "system" (or kernel)
    """

    def test_charge_delegation_id_self_creation_allowed(self) -> None:
        """Caller 'alice' CAN create artifact ID 'charge_delegation:alice'."""
        store = ArtifactStore()
        artifact = store.write(
            "charge_delegation:alice", "document", "delegation config", "alice",
        )
        assert artifact.id == "charge_delegation:alice"
        assert artifact.created_by == "alice"

    def test_charge_delegation_id_squatting_blocked(self) -> None:
        """Caller 'attacker' CANNOT create 'charge_delegation:alice' (squatting)."""
        store = ArtifactStore()
        with pytest.raises(PermissionError, match="charge_delegation"):
            store.write(
                "charge_delegation:alice", "document", "hijacked", "attacker",
            )

    def test_right_prefix_id_requires_system(self) -> None:
        """Caller 'alice' CANNOT create artifact ID 'right:some_right'."""
        store = ArtifactStore()
        with pytest.raises(PermissionError, match="right:"):
            store.write(
                "right:some_right", "right", "right content", "alice",
            )


class TestKernelModifyProtected:
    """Kernel primitive: modify_protected_content() bypasses protection.

    The kernel (not agents) must be able to update protected artifacts
    via a dedicated method that is NOT exposed to user-facing write().
    """

    def test_kernel_can_modify_protected_content(self) -> None:
        """modify_protected_content() can update a kernel_protected artifact."""
        store = ArtifactStore()
        artifact = store.write("kernel-artifact", "document", "v1", "system")
        artifact.kernel_protected = True

        # Normal write is blocked
        with pytest.raises(PermissionError, match="kernel_protected"):
            store.write("kernel-artifact", "document", "v2", "system")

        # Kernel bypass method succeeds
        updated = store.modify_protected_content("kernel-artifact", content="v2")
        assert updated.content == "v2"
