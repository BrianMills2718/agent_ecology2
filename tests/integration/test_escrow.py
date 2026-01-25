"""Tests for genesis_escrow - trustless artifact trading (Plan #213 redesign).

Plan #213: Escrow now uses metadata["authorized_writer"] instead of
transfer_ownership() for artifact trading. This enables trading while
keeping created_by immutable (per ADR-0016).
"""

import pytest
import tempfile
from pathlib import Path


from src.world.artifacts import ArtifactStore
from src.world.ledger import Ledger
from src.world.genesis import GenesisEscrow


def grant_escrow_access(store: ArtifactStore, artifact_id: str, escrow: GenesisEscrow) -> None:
    """Helper to grant escrow write access to an artifact (Plan #213).

    This simulates the seller setting metadata["authorized_writer"] = escrow.id
    which grants escrow permission to update the authorized_writer on purchase.
    """
    artifact = store.get(artifact_id)
    if artifact:
        artifact.metadata["authorized_writer"] = escrow.id


class TestEscrowDeposit:
    """Test escrow deposit functionality (Plan #213 redesign)."""

    def test_deposit_success(self) -> None:
        """Seller can deposit artifact after granting escrow write access."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)

        # Seller creates artifact
        store.write("my_artifact", "generic", "content", "seller")

        # Create escrow
        escrow = GenesisEscrow(ledger, store)

        # Plan #213: Grant escrow write access via authorized_writer
        grant_escrow_access(store, "my_artifact", escrow)

        # Seller deposits with price
        result = escrow._deposit(["my_artifact", 50], "seller")

        assert result["success"] is True
        assert result["artifact_id"] == "my_artifact"
        assert result["price"] == 50
        assert result["seller"] == "seller"

    def test_deposit_without_access_fails(self) -> None:
        """Cannot deposit artifact without granting escrow write access."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)

        store.write("my_artifact", "generic", "content", "seller")
        escrow = GenesisEscrow(ledger, store)

        # Try to deposit without granting escrow access first
        result = escrow._deposit(["my_artifact", 50], "seller")

        assert result["success"] is False
        assert "does not have write access" in result["error"]
        assert "authorized_writer" in result["error"]

    def test_deposit_nonexistent_artifact(self) -> None:
        """Cannot deposit non-existent artifact."""
        ledger = Ledger()
        store = ArtifactStore()
        escrow = GenesisEscrow(ledger, store)

        result = escrow._deposit(["nonexistent", 50], "seller")

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_deposit_invalid_price(self) -> None:
        """Price must be positive integer."""
        ledger = Ledger()
        store = ArtifactStore()
        escrow = GenesisEscrow(ledger, store)
        store.write("my_artifact", "generic", "content", "seller")
        grant_escrow_access(store, "my_artifact", escrow)

        # Zero price
        result = escrow._deposit(["my_artifact", 0], "seller")
        assert result["success"] is False
        assert "positive" in result["error"]

        # Negative price
        result = escrow._deposit(["my_artifact", -10], "seller")
        assert result["success"] is False

    def test_deposit_with_buyer_restriction(self) -> None:
        """Can restrict purchase to specific buyer."""
        ledger = Ledger()
        store = ArtifactStore()
        escrow = GenesisEscrow(ledger, store)
        store.write("my_artifact", "generic", "content", "seller")
        grant_escrow_access(store, "my_artifact", escrow)

        result = escrow._deposit(["my_artifact", 50, "specific_buyer"], "seller")

        assert result["success"] is True
        assert "restricted to specific_buyer" in result["message"]


class TestEscrowPurchase:
    """Test escrow purchase functionality (Plan #213 redesign)."""

    def setup_listing(self) -> tuple[Ledger, ArtifactStore, GenesisEscrow]:
        """Helper to set up a listed artifact."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)
        ledger.create_principal("buyer", starting_scrip=200, starting_compute=50)

        store.write("my_artifact", "generic", "valuable content", "seller")
        escrow = GenesisEscrow(ledger, store)
        # Plan #213: Grant escrow write access instead of transfer_ownership
        grant_escrow_access(store, "my_artifact", escrow)
        escrow._deposit(["my_artifact", 75], "seller")

        return ledger, store, escrow

    def test_purchase_success(self) -> None:
        """Buyer can purchase listed artifact."""
        ledger, store, escrow = self.setup_listing()

        result = escrow._purchase(["my_artifact"], "buyer")

        assert result["success"] is True
        assert result["artifact_id"] == "my_artifact"
        assert result["price"] == 75
        assert result["seller"] == "seller"
        assert result["buyer"] == "buyer"

        # Plan #213: Verify authorized_writer is now buyer
        assert store.get("my_artifact").metadata.get("authorized_writer") == "buyer"
        assert ledger.get_scrip("buyer") == 125  # 200 - 75
        assert ledger.get_scrip("seller") == 175  # 100 + 75

    def test_purchase_insufficient_funds(self) -> None:
        """Purchase fails if buyer has insufficient scrip."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)
        ledger.create_principal("poor_buyer", starting_scrip=10, starting_compute=50)

        store.write("expensive", "generic", "content", "seller")
        escrow = GenesisEscrow(ledger, store)
        grant_escrow_access(store, "expensive", escrow)
        escrow._deposit(["expensive", 100], "seller")

        result = escrow._purchase(["expensive"], "poor_buyer")

        assert result["success"] is False
        assert "Insufficient scrip" in result["error"]
        # Plan #213: authorized_writer is still escrow
        assert store.get("expensive").metadata.get("authorized_writer") == escrow.id

    def test_purchase_no_listing(self) -> None:
        """Cannot purchase unlisted artifact."""
        ledger = Ledger()
        store = ArtifactStore()
        escrow = GenesisEscrow(ledger, store)

        result = escrow._purchase(["nonexistent"], "buyer")

        assert result["success"] is False
        assert "No listing" in result["error"]

    def test_purchase_own_listing_fails(self) -> None:
        """Cannot purchase your own listing."""
        ledger, store, escrow = self.setup_listing()

        result = escrow._purchase(["my_artifact"], "seller")

        assert result["success"] is False
        assert "Cannot purchase your own" in result["error"]

    def test_purchase_restricted_to_other_buyer(self) -> None:
        """Cannot purchase if restricted to different buyer."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)
        ledger.create_principal("allowed", starting_scrip=200, starting_compute=50)
        ledger.create_principal("not_allowed", starting_scrip=200, starting_compute=50)

        store.write("restricted", "generic", "content", "seller")
        escrow = GenesisEscrow(ledger, store)
        grant_escrow_access(store, "restricted", escrow)
        escrow._deposit(["restricted", 50, "allowed"], "seller")

        # Wrong buyer fails
        result = escrow._purchase(["restricted"], "not_allowed")
        assert result["success"] is False
        assert "restricted to buyer" in result["error"]

        # Correct buyer succeeds
        result = escrow._purchase(["restricted"], "allowed")
        assert result["success"] is True


class TestEscrowCancel:
    """Test escrow cancel functionality (Plan #213 redesign)."""

    def test_cancel_success(self) -> None:
        """Seller can cancel listing and get write access back."""
        ledger = Ledger()
        store = ArtifactStore()
        store.write("my_artifact", "generic", "content", "seller")
        escrow = GenesisEscrow(ledger, store)
        grant_escrow_access(store, "my_artifact", escrow)
        escrow._deposit(["my_artifact", 50], "seller")

        result = escrow._cancel(["my_artifact"], "seller")

        assert result["success"] is True
        # Plan #213: authorized_writer is returned to seller
        assert store.get("my_artifact").metadata.get("authorized_writer") == "seller"

    def test_cancel_not_seller_fails(self) -> None:
        """Only seller can cancel."""
        ledger = Ledger()
        store = ArtifactStore()
        store.write("my_artifact", "generic", "content", "seller")
        escrow = GenesisEscrow(ledger, store)
        grant_escrow_access(store, "my_artifact", escrow)
        escrow._deposit(["my_artifact", 50], "seller")

        result = escrow._cancel(["my_artifact"], "not_seller")

        assert result["success"] is False
        assert "Only the seller" in result["error"]
        # Plan #213: authorized_writer is still escrow
        assert store.get("my_artifact").metadata.get("authorized_writer") == escrow.id

    def test_cancel_after_purchase_fails(self) -> None:
        """Cannot cancel completed listing."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)
        ledger.create_principal("buyer", starting_scrip=200, starting_compute=50)

        store.write("my_artifact", "generic", "content", "seller")
        escrow = GenesisEscrow(ledger, store)
        grant_escrow_access(store, "my_artifact", escrow)
        escrow._deposit(["my_artifact", 50], "seller")
        escrow._purchase(["my_artifact"], "buyer")

        result = escrow._cancel(["my_artifact"], "seller")

        assert result["success"] is False
        assert "not active" in result["error"]


class TestEscrowCheck:
    """Test escrow check functionality."""

    def test_check_listing(self) -> None:
        """Can check listing status."""
        ledger = Ledger()
        store = ArtifactStore()
        store.write("my_artifact", "generic", "content", "seller")
        escrow = GenesisEscrow(ledger, store)
        grant_escrow_access(store, "my_artifact", escrow)
        escrow._deposit(["my_artifact", 50], "seller")

        result = escrow._check(["my_artifact"], "anyone")

        assert result["success"] is True
        assert result["listing"]["artifact_id"] == "my_artifact"
        assert result["listing"]["seller_id"] == "seller"
        assert result["listing"]["price"] == 50
        assert result["listing"]["status"] == "active"

    def test_check_no_listing(self) -> None:
        """Check fails for unlisted artifact."""
        ledger = Ledger()
        store = ArtifactStore()
        escrow = GenesisEscrow(ledger, store)

        result = escrow._check(["nonexistent"], "anyone")

        assert result["success"] is False


class TestEscrowListActive:
    """Test escrow list_active functionality."""

    def test_list_active_empty(self) -> None:
        """List returns empty when no listings."""
        ledger = Ledger()
        store = ArtifactStore()
        escrow = GenesisEscrow(ledger, store)

        result = escrow._list_active([], "anyone")

        assert result["success"] is True
        assert result["listings"] == []
        assert result["count"] == 0

    def test_list_active_with_listings(self) -> None:
        """List returns active listings."""
        ledger = Ledger()
        store = ArtifactStore()
        escrow = GenesisEscrow(ledger, store)

        # Create multiple listings
        for i in range(3):
            artifact_id = f"artifact_{i}"
            store.write(artifact_id, "generic", f"content {i}", "seller")
            # Plan #213: Grant escrow write access via authorized_writer
            grant_escrow_access(store, artifact_id, escrow)
            escrow._deposit([artifact_id, 10 + i], "seller")

        result = escrow._list_active([], "anyone")

        assert result["success"] is True
        assert result["count"] == 3

    def test_list_active_excludes_completed(self) -> None:
        """List excludes completed and cancelled listings."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)
        ledger.create_principal("buyer", starting_scrip=200, starting_compute=50)
        escrow = GenesisEscrow(ledger, store)

        # Active listing
        store.write("active", "generic", "content", "seller")
        # Plan #213: Grant escrow write access via authorized_writer
        grant_escrow_access(store, "active", escrow)
        escrow._deposit(["active", 10], "seller")

        # Completed listing
        store.write("completed", "generic", "content", "seller")
        grant_escrow_access(store, "completed", escrow)
        escrow._deposit(["completed", 20], "seller")
        escrow._purchase(["completed"], "buyer")

        # Cancelled listing
        store.write("cancelled", "generic", "content", "seller")
        grant_escrow_access(store, "cancelled", escrow)
        escrow._deposit(["cancelled", 30], "seller")
        escrow._cancel(["cancelled"], "seller")

        result = escrow._list_active([], "anyone")

        assert result["count"] == 1
        assert result["listings"][0]["artifact_id"] == "active"


class TestEscrowIntegration:
    """Integration tests for escrow in World context."""

    def test_escrow_created_in_world(self) -> None:
        """Escrow is created as part of genesis artifacts."""
        from src.world.world import World

        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            log_file = f.name

        config = {
            'world': {},
            'costs': {'actions': {}, 'default': 1},
            'logging': {'output_file': log_file},
            'principals': [{'id': 'alice', 'starting_scrip': 100}],
            'rate_limiting': {'enabled': True, 'window_seconds': 60.0, 'resources': {'llm_tokens': {'max_per_window': 1000}}}
        }

        world = World(config)

        assert "genesis_escrow" in world.genesis_artifacts
        escrow = world.genesis_artifacts["genesis_escrow"]
        assert isinstance(escrow, GenesisEscrow)

    def test_full_trade_flow_via_world(self) -> None:
        """Complete trade flow through World actions (Plan #213 redesign).

        Plan #213: Escrow now uses metadata["authorized_writer"] instead of
        transfer_ownership(). This test verifies the escrow flow works correctly
        when artifacts are traded via the authorized_writer pattern.
        """
        from src.world.world import World
        from src.world.actions import WriteArtifactIntent, InvokeArtifactIntent

        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            log_file = f.name

        config = {
            'world': {},
            'costs': {'actions': {}, 'default': 1},
            'logging': {'output_file': log_file},
            'principals': [
                {'id': 'seller', 'starting_scrip': 50},
                {'id': 'buyer', 'starting_scrip': 200}
            ],
            'rate_limiting': {'enabled': True, 'window_seconds': 60.0, 'resources': {'llm_tokens': {'max_per_window': 1000}}}
        }

        world = World(config)
        world.advance_tick()

        # 1. Seller creates artifact
        write = WriteArtifactIntent("seller", "tool_1", "tool", "A useful tool")
        result = world.execute_action(write)
        assert result.success, result.message

        # 2. Plan #213: Seller grants escrow write access via authorized_writer
        # (In a full implementation, this would be via a SetMetadataIntent action.
        # For now, we set it directly to test the escrow flow.)
        escrow = world.genesis_artifacts["genesis_escrow"]
        artifact = world.artifacts.get("tool_1")
        artifact.metadata["authorized_writer"] = escrow.id

        # 3. Seller deposits with price
        deposit = InvokeArtifactIntent(
            "seller", "genesis_escrow", "deposit",
            ["tool_1", 100]
        )
        result = world.execute_action(deposit)
        assert result.success, result.message

        # 4. Buyer purchases
        purchase = InvokeArtifactIntent(
            "buyer", "genesis_escrow", "purchase",
            ["tool_1"]
        )
        result = world.execute_action(purchase)
        assert result.success, result.message

        # Verify final state - Plan #213: authorized_writer is now buyer
        artifact = world.artifacts.get("tool_1")
        assert artifact.metadata.get("authorized_writer") == "buyer"
        # created_by is immutable per ADR-0016
        assert artifact.created_by == "seller"
        # Buyer: 200 - 100 (purchase) = 100
        assert world.ledger.get_scrip("buyer") == 100
        # Seller: 50 + 100 (sale) = 150
        # Note: Genesis method fees are compute (resources), not scrip
        assert world.ledger.get_scrip("seller") == 150
