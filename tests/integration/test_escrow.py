"""Tests for genesis_escrow - trustless artifact trading."""

import pytest
import tempfile
from pathlib import Path


from src.world.artifacts import ArtifactStore
from src.world.ledger import Ledger
from src.world.genesis import GenesisEscrow


class TestEscrowDeposit:
    """Test escrow deposit functionality."""

    def test_deposit_success(self) -> None:
        """Seller can deposit artifact after transferring ownership."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)

        # Seller creates artifact
        store.write("my_artifact", "generic", "content", "seller")

        # Create escrow
        escrow = GenesisEscrow(ledger, store)

        # Seller transfers ownership to escrow
        store.transfer_ownership("my_artifact", "seller", escrow.id)

        # Seller deposits with price
        result = escrow._deposit(["my_artifact", 50], "seller")

        assert result["success"] is True
        assert result["artifact_id"] == "my_artifact"
        assert result["price"] == 50
        assert result["seller"] == "seller"

    def test_deposit_without_ownership_fails(self) -> None:
        """Cannot deposit artifact still owned by seller."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)

        store.write("my_artifact", "generic", "content", "seller")
        escrow = GenesisEscrow(ledger, store)

        # Try to deposit without transferring ownership first
        result = escrow._deposit(["my_artifact", 50], "seller")

        assert result["success"] is False
        assert "does not own" in result["error"]
        assert "transfer_ownership" in result["error"]

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
        store.transfer_ownership("my_artifact", "seller", escrow.id)

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
        store.transfer_ownership("my_artifact", "seller", escrow.id)

        result = escrow._deposit(["my_artifact", 50, "specific_buyer"], "seller")

        assert result["success"] is True
        assert "restricted to specific_buyer" in result["message"]


class TestEscrowPurchase:
    """Test escrow purchase functionality."""

    def setup_listing(self) -> tuple[Ledger, ArtifactStore, GenesisEscrow]:
        """Helper to set up a listed artifact."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)
        ledger.create_principal("buyer", starting_scrip=200, starting_compute=50)

        store.write("my_artifact", "generic", "valuable content", "seller")
        escrow = GenesisEscrow(ledger, store)
        store.transfer_ownership("my_artifact", "seller", escrow.id)
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

        # Verify transfers
        assert store.get_owner("my_artifact") == "buyer"
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
        store.transfer_ownership("expensive", "seller", escrow.id)
        escrow._deposit(["expensive", 100], "seller")

        result = escrow._purchase(["expensive"], "poor_buyer")

        assert result["success"] is False
        assert "Insufficient scrip" in result["error"]
        assert store.get_owner("expensive") == escrow.id  # Still in escrow

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
        store.transfer_ownership("restricted", "seller", escrow.id)
        escrow._deposit(["restricted", 50, "allowed"], "seller")

        # Wrong buyer fails
        result = escrow._purchase(["restricted"], "not_allowed")
        assert result["success"] is False
        assert "restricted to buyer" in result["error"]

        # Correct buyer succeeds
        result = escrow._purchase(["restricted"], "allowed")
        assert result["success"] is True


class TestEscrowCancel:
    """Test escrow cancel functionality."""

    def test_cancel_success(self) -> None:
        """Seller can cancel listing and get artifact back."""
        ledger = Ledger()
        store = ArtifactStore()
        store.write("my_artifact", "generic", "content", "seller")
        escrow = GenesisEscrow(ledger, store)
        store.transfer_ownership("my_artifact", "seller", escrow.id)
        escrow._deposit(["my_artifact", 50], "seller")

        result = escrow._cancel(["my_artifact"], "seller")

        assert result["success"] is True
        assert store.get_owner("my_artifact") == "seller"

    def test_cancel_not_seller_fails(self) -> None:
        """Only seller can cancel."""
        ledger = Ledger()
        store = ArtifactStore()
        store.write("my_artifact", "generic", "content", "seller")
        escrow = GenesisEscrow(ledger, store)
        store.transfer_ownership("my_artifact", "seller", escrow.id)
        escrow._deposit(["my_artifact", 50], "seller")

        result = escrow._cancel(["my_artifact"], "not_seller")

        assert result["success"] is False
        assert "Only the seller" in result["error"]
        assert store.get_owner("my_artifact") == escrow.id  # Still in escrow

    def test_cancel_after_purchase_fails(self) -> None:
        """Cannot cancel completed listing."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)
        ledger.create_principal("buyer", starting_scrip=200, starting_compute=50)

        store.write("my_artifact", "generic", "content", "seller")
        escrow = GenesisEscrow(ledger, store)
        store.transfer_ownership("my_artifact", "seller", escrow.id)
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
        store.transfer_ownership("my_artifact", "seller", escrow.id)
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
            store.transfer_ownership(artifact_id, "seller", escrow.id)
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
        store.transfer_ownership("active", "seller", escrow.id)
        escrow._deposit(["active", 10], "seller")

        # Completed listing
        store.write("completed", "generic", "content", "seller")
        store.transfer_ownership("completed", "seller", escrow.id)
        escrow._deposit(["completed", 20], "seller")
        escrow._purchase(["completed"], "buyer")

        # Cancelled listing
        store.write("cancelled", "generic", "content", "seller")
        store.transfer_ownership("cancelled", "seller", escrow.id)
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
            'world': {'max_ticks': 10},
            'costs': {'actions': {}, 'default': 1},
            'logging': {'output_file': log_file},
            'principals': [{'id': 'alice', 'starting_scrip': 100}]
        }

        world = World(config)

        assert "genesis_escrow" in world.genesis_artifacts
        escrow = world.genesis_artifacts["genesis_escrow"]
        assert isinstance(escrow, GenesisEscrow)

    def test_full_trade_flow_via_world(self) -> None:
        """Complete trade flow through World actions."""
        from src.world.world import World
        from src.world.actions import WriteArtifactIntent, InvokeArtifactIntent

        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            log_file = f.name

        config = {
            'world': {'max_ticks': 10},
            'costs': {'actions': {}, 'default': 1},
            'logging': {'output_file': log_file},
            'principals': [
                {'id': 'seller', 'starting_scrip': 50},
                {'id': 'buyer', 'starting_scrip': 200}
            ]
        }

        world = World(config)
        world.advance_tick()

        # 1. Seller creates artifact
        write = WriteArtifactIntent("seller", "tool_1", "tool", "A useful tool")
        result = world.execute_action(write)
        assert result.success, result.message

        # 2. Seller transfers ownership to escrow
        transfer = InvokeArtifactIntent(
            "seller", "genesis_ledger", "transfer_ownership",
            ["tool_1", "genesis_escrow"]
        )
        result = world.execute_action(transfer)
        assert result.success, result.message

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

        # Verify final state
        assert world.artifacts.get_owner("tool_1") == "buyer"
        # Buyer: 200 - 100 (purchase) = 100
        assert world.ledger.get_scrip("buyer") == 100
        # Seller: 50 + 100 (sale) = 150
        # Note: Genesis method fees are compute (resources), not scrip
        assert world.ledger.get_scrip("seller") == 150
