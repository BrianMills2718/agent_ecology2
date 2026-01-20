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
        """Owner can transfer artifact to another principal."""
        store = ArtifactStore()
        store.write("artifact_1", "generic", "content", "alice")

        result = store.transfer_ownership("artifact_1", "alice", "bob")

        assert result is True
        assert store.get_owner("artifact_1") == "bob"

    def test_transfer_ownership_nonexistent_artifact(self) -> None:
        """Cannot transfer non-existent artifact."""
        store = ArtifactStore()

        result = store.transfer_ownership("nonexistent", "alice", "bob")

        assert result is False

    def test_transfer_ownership_wrong_owner(self) -> None:
        """Cannot transfer artifact you don't own."""
        store = ArtifactStore()
        store.write("artifact_1", "generic", "content", "alice")

        # Bob tries to transfer Alice's artifact
        result = store.transfer_ownership("artifact_1", "bob", "charlie")

        assert result is False
        assert store.get_owner("artifact_1") == "alice"

    def test_transfer_ownership_preserves_content(self) -> None:
        """Transfer preserves artifact content and properties."""
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
        assert artifact.created_by == "bob"
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
        assert store.get_owner("artifact_1") == "alice"


class TestGenesisLedgerOwnershipTransfer:
    """Test ownership transfer through genesis_ledger."""

    def test_transfer_ownership_via_genesis(self) -> None:
        """Can transfer ownership through genesis_ledger method."""
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
        assert store.get_owner("my_artifact") == "bob"

    def test_transfer_ownership_not_owner(self) -> None:
        """Cannot transfer artifact you don't own."""
        ledger = Ledger()
        store = ArtifactStore()
        store.write("my_artifact", "generic", "content", "alice")

        genesis = GenesisLedger(ledger, artifact_store=store)
        result = genesis._transfer_ownership(
            args=["my_artifact", "charlie"],
            invoker_id="bob"  # Not the owner
        )

        assert result["success"] is False
        assert "not the owner" in result["error"]
        assert store.get_owner("my_artifact") == "alice"

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
    """Edge cases for ownership transfer."""

    def test_transfer_then_original_owner_cannot_write(self) -> None:
        """After transfer, original owner loses write access."""
        store = ArtifactStore()
        store.write("artifact_1", "generic", "content", "alice")

        store.transfer_ownership("artifact_1", "alice", "bob")

        artifact = store.get("artifact_1")
        assert artifact is not None
        # Alice should no longer have write access (via freeware contract, only creator can write)
        assert check_permission("alice", "write", artifact) is False
        # Bob should have write access (now the creator)
        assert check_permission("bob", "write", artifact) is True

    def test_new_owner_can_write(self) -> None:
        """New owner can modify artifact after transfer."""
        store = ArtifactStore()
        store.write("artifact_1", "generic", "original content", "alice")

        store.transfer_ownership("artifact_1", "alice", "bob")

        # Bob updates the artifact
        artifact = store.get("artifact_1")
        assert artifact is not None
        # Via freeware contract, creator can write
        assert check_permission("bob", "write", artifact) is True

    def test_transfer_executable_artifact(self) -> None:
        """Can transfer executable artifacts."""
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
        assert artifact.created_by == "bob"
        assert artifact.executable is True
        # Price payments should now go to bob
        assert artifact.price == 5

    def test_chain_of_transfers(self) -> None:
        """Artifact can be transferred multiple times."""
        store = ArtifactStore()
        store.write("artifact_1", "generic", "content", "alice")

        # Alice -> Bob
        store.transfer_ownership("artifact_1", "alice", "bob")
        assert store.get_owner("artifact_1") == "bob"

        # Bob -> Charlie
        store.transfer_ownership("artifact_1", "bob", "charlie")
        assert store.get_owner("artifact_1") == "charlie"

        # Charlie -> Dave
        store.transfer_ownership("artifact_1", "charlie", "dave")
        assert store.get_owner("artifact_1") == "dave"

        # Alice can no longer transfer
        result = store.transfer_ownership("artifact_1", "alice", "eve")
        assert result is False
