"""Tests for artifact ownership transfer."""

import pytest
from pathlib import Path


from src.world.artifacts import Artifact, ArtifactStore
from src.world.ledger import Ledger
from src.world.genesis import GenesisLedger
from src.world.executor import get_executor


def check_permission(agent_id: str, action: str, artifact: Artifact) -> bool:
    """Check permission via the executor's contract-based system."""
    executor = get_executor()
    allowed, reason = executor._check_permission(agent_id, action, artifact)
    return allowed


class TestArtifactStoreOwnershipTransfer:
    """Test ArtifactStore.transfer_ownership method."""

    def test_transfer_ownership_success(self) -> None:
        """Controller can transfer artifact to another principal.

        Per ADR-0016: created_by is immutable, metadata["controller"] tracks current controller.
        """
        store = ArtifactStore()
        store.write("artifact_1", "generic", "content", "alice")

        result = store.transfer_ownership("artifact_1", "alice", "bob")

        assert result is True
        # created_by stays the same (immutable historical fact)
        assert store.get_creator("artifact_1") == "alice"
        # controller is now bob
        assert store.get("artifact_1").metadata.get("controller", store.get("artifact_1").created_by) == "bob"

    def test_transfer_ownership_nonexistent_artifact(self) -> None:
        """Cannot transfer non-existent artifact."""
        store = ArtifactStore()

        result = store.transfer_ownership("nonexistent", "alice", "bob")

        assert result is False

    def test_transfer_ownership_wrong_owner(self) -> None:
        """Cannot transfer artifact you don't control.

        Per ADR-0016: Only the current controller can transfer.
        """
        store = ArtifactStore()
        store.write("artifact_1", "generic", "content", "alice")

        # Bob tries to transfer Alice's artifact
        result = store.transfer_ownership("artifact_1", "bob", "charlie")

        assert result is False
        assert store.get("artifact_1").metadata.get("controller", store.get("artifact_1").created_by) == "alice"

    def test_transfer_ownership_preserves_content(self) -> None:
        """Transfer preserves artifact content and properties.

        Per ADR-0016: created_by is immutable, only metadata["controller"] changes.
        """
        store = ArtifactStore()
        store.write(
            "artifact_1",
            "code",
            "content here",
            "alice",
            executable=True,
            code="def run(): return 42",
            price=10
        )

        store.transfer_ownership("artifact_1", "alice", "bob")

        artifact = store.get("artifact_1")
        assert artifact is not None
        # created_by is immutable - stays alice (the original creator)
        assert artifact.created_by == "alice"
        # controller is now bob (stored in metadata)
        assert artifact.metadata.get("controller") == "bob"
        # All other properties preserved
        assert artifact.content == "content here"
        assert artifact.type == "code"
        assert artifact.executable is True
        assert artifact.code == "def run(): return 42"
        assert artifact.price == 10

    def test_transfer_to_self(self) -> None:
        """Transfer to self is allowed (no-op)."""
        store = ArtifactStore()
        store.write("artifact_1", "generic", "content", "alice")

        result = store.transfer_ownership("artifact_1", "alice", "alice")

        assert result is True
        assert store.get("artifact_1").metadata.get("controller", store.get("artifact_1").created_by) == "alice"


class TestGenesisLedgerOwnershipTransfer:
    """Test ownership transfer through genesis_ledger.

    Per ADR-0016: Ownership transfers update metadata["controller"],
    not created_by (which is immutable).
    """

    def test_transfer_ownership_via_genesis(self) -> None:
        """Can transfer control through genesis_ledger method."""
        ledger = Ledger()
        store = ArtifactStore()
        store.write("my_artifact", "generic", "content", "alice")

        genesis = GenesisLedger(ledger, artifact_store=store)
        result = genesis._transfer_ownership(
            args=["my_artifact", "bob"],
            invoker_id="alice"
        )

        assert result["success"] is True
        assert result["artifact_id"] == "my_artifact"
        assert result["from_owner"] == "alice"
        assert result["to_owner"] == "bob"
        # created_by stays alice (immutable)
        assert store.get_creator("my_artifact") == "alice"
        # controller is now bob
        assert store.get("my_artifact").metadata.get("controller", store.get("my_artifact").created_by) == "bob"

    def test_transfer_ownership_not_owner(self) -> None:
        """Cannot transfer artifact you don't control."""
        ledger = Ledger()
        store = ArtifactStore()
        store.write("my_artifact", "generic", "content", "alice")

        genesis = GenesisLedger(ledger, artifact_store=store)
        result = genesis._transfer_ownership(
            args=["my_artifact", "charlie"],
            invoker_id="bob"  # Not the controller
        )

        assert result["success"] is False
        assert "not the controller" in result["error"]
        assert store.get("my_artifact").metadata.get("controller", store.get("my_artifact").created_by) == "alice"

    def test_transfer_ownership_nonexistent(self) -> None:
        """Cannot transfer non-existent artifact."""
        ledger = Ledger()
        store = ArtifactStore()

        genesis = GenesisLedger(ledger, artifact_store=store)
        result = genesis._transfer_ownership(
            args=["nonexistent", "bob"],
            invoker_id="alice"
        )

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_transfer_ownership_missing_args(self) -> None:
        """Error with missing arguments."""
        ledger = Ledger()
        store = ArtifactStore()

        genesis = GenesisLedger(ledger, artifact_store=store)
        result = genesis._transfer_ownership(
            args=["only_one_arg"],
            invoker_id="alice"
        )

        assert result["success"] is False
        assert "requires" in result["error"]

    def test_transfer_ownership_no_store(self) -> None:
        """Error when artifact store not configured."""
        ledger = Ledger()

        genesis = GenesisLedger(ledger, artifact_store=None)
        result = genesis._transfer_ownership(
            args=["artifact", "bob"],
            invoker_id="alice"
        )

        assert result["success"] is False
        assert "not configured" in result["error"]

    def test_method_is_registered(self) -> None:
        """transfer_ownership method is registered on genesis_ledger."""
        ledger = Ledger()
        store = ArtifactStore()

        genesis = GenesisLedger(ledger, artifact_store=store)
        method = genesis.get_method("transfer_ownership")

        assert method is not None
        assert method.name == "transfer_ownership"
        assert method.cost == 1  # Default cost from config


class TestOwnershipTransferEdgeCases:
    """Edge cases for ownership transfer.

    Per ADR-0016:
    - created_by is immutable (historical fact)
    - transfer_ownership() sets metadata["controller"]
    - BUT freeware contract checks created_by, not controller
    - So transfer doesn't change access under freeware
    """

    def test_transfer_does_not_affect_freeware_access(self) -> None:
        """Under freeware, transfer doesn't change write access (ADR-0016).

        Freeware checks created_by, not metadata["controller"]. So the
        original creator can still write, and the "transferred to" principal
        cannot write (unless a different contract is used).
        """
        store = ArtifactStore()
        store.write("artifact_1", "generic", "content", "alice")

        store.transfer_ownership("artifact_1", "alice", "bob")

        artifact = store.get("artifact_1")
        assert artifact is not None
        # Freeware checks created_by - alice is the creator, so she CAN write
        assert check_permission("alice", "write", artifact) is True
        # Bob is NOT the creator, so he CANNOT write under freeware
        assert check_permission("bob", "write", artifact) is False

    def test_transfer_sets_metadata_controller(self) -> None:
        """transfer_ownership() sets metadata["controller"] (for custom contracts)."""
        store = ArtifactStore()
        store.write("artifact_1", "generic", "original content", "alice")

        store.transfer_ownership("artifact_1", "alice", "bob")

        artifact = store.get("artifact_1")
        assert artifact is not None
        # metadata["controller"] is set
        assert artifact.metadata.get("controller") == "bob"
        # created_by is unchanged
        assert artifact.created_by == "alice"

    def test_transfer_executable_artifact(self) -> None:
        """Can transfer executable artifacts.

        Per ADR-0016: created_by stays alice (immutable), controller becomes bob.
        """
        store = ArtifactStore()
        store.write(
            "service_1",
            "service",
            "My service",
            "alice",
            executable=True,
            code="def run(): return 'hello'",
            price=5
        )

        result = store.transfer_ownership("service_1", "alice", "bob")

        assert result is True
        artifact = store.get("service_1")
        assert artifact is not None
        # created_by is immutable - stays alice
        assert artifact.created_by == "alice"
        # controller is now bob
        assert artifact.metadata.get("controller") == "bob"
        assert artifact.executable is True
        # Price payments should now go to controller (bob)
        assert artifact.price == 5

    def test_chain_of_transfers(self) -> None:
        """Artifact can be transferred multiple times.

        Per ADR-0016: created_by stays the same, controller changes.
        """
        store = ArtifactStore()
        store.write("artifact_1", "generic", "content", "alice")

        # Alice -> Bob
        store.transfer_ownership("artifact_1", "alice", "bob")
        assert store.get("artifact_1").metadata.get("controller", store.get("artifact_1").created_by) == "bob"
        assert store.get_creator("artifact_1") == "alice"  # Never changes

        # Bob -> Charlie
        store.transfer_ownership("artifact_1", "bob", "charlie")
        assert store.get("artifact_1").metadata.get("controller", store.get("artifact_1").created_by) == "charlie"
        assert store.get_creator("artifact_1") == "alice"  # Never changes

        # Charlie -> Dave
        store.transfer_ownership("artifact_1", "charlie", "dave")
        assert store.get("artifact_1").metadata.get("controller", store.get("artifact_1").created_by) == "dave"
        assert store.get_creator("artifact_1") == "alice"  # Never changes

        # Alice can no longer transfer
        result = store.transfer_ownership("artifact_1", "alice", "eve")
        assert result is False
