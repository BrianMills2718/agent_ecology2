"""Feature acceptance tests for escrow - maps to meta/acceptance_gates/escrow.yaml.

Run with: pytest --feature escrow tests/
"""

from __future__ import annotations

import pytest

from src.world.ledger import Ledger
from src.world.artifacts import ArtifactStore
from src.world.genesis import GenesisEscrow


@pytest.mark.feature("escrow")
class TestEscrowFeature:
    """Tests mapping to meta/acceptance_gates/escrow.yaml acceptance criteria."""

    # AC-1: Successful artifact sale via escrow (happy_path)
    def test_ac_1_successful_artifact_sale(
        self, escrow_with_store: tuple[GenesisEscrow, ArtifactStore, Ledger]
    ) -> None:
        """AC-1: Successful artifact sale via escrow.

        Given:
          - Seller owns artifact X
          - Seller has transferred ownership to genesis_escrow
          - Seller deposits artifact X at price 100 scrip
          - Buyer has 150 scrip
        When: Buyer purchases artifact X
        Then:
          - Buyer now owns artifact X
          - Buyer's balance reduced by 100 scrip
          - Seller's balance increased by 100 scrip
          - Listing removed from escrow
        """
        escrow, store, ledger = escrow_with_store

        # Seller creates and lists artifact
        store.write("artifact_x", "generic", "valuable content", "seller")
        store.transfer_ownership("artifact_x", "seller", escrow.id)
        deposit_result = escrow._deposit(["artifact_x", 100], "seller")
        assert deposit_result["success"] is True

        # Record initial balances (seller=100, buyer=500)
        seller_initial = ledger.get_scrip("seller")
        buyer_initial = ledger.get_scrip("buyer")

        # Buyer purchases
        result = escrow._purchase(["artifact_x"], "buyer")

        assert result["success"] is True
        assert store.get_controller("artifact_x") == "buyer"
        assert ledger.get_scrip("buyer") == buyer_initial - 100
        assert ledger.get_scrip("seller") == seller_initial + 100

        # Listing should be removed (completed)
        check = escrow._check(["artifact_x"], "anyone")
        assert check["listing"]["status"] == "completed"

    # AC-2: Purchase fails when buyer has insufficient funds (error_case)
    def test_ac_2_purchase_fails_insufficient_funds(self) -> None:
        """AC-2: Purchase fails when buyer has insufficient funds.

        Given:
          - Artifact X listed at price 100 scrip
          - Buyer has only 50 scrip
        When: Buyer attempts to purchase
        Then:
          - Purchase returns error (insufficient funds)
          - Artifact ownership unchanged (still escrow)
          - Listing remains active
          - No scrip transferred
        """
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)
        ledger.create_principal("poor_buyer", starting_scrip=50, starting_compute=50)

        escrow = GenesisEscrow(ledger, store)
        store.write("artifact_x", "generic", "content", "seller")
        store.transfer_ownership("artifact_x", "seller", escrow.id)
        escrow._deposit(["artifact_x", 100], "seller")

        result = escrow._purchase(["artifact_x"], "poor_buyer")

        assert result["success"] is False
        assert "Insufficient" in result["error"]
        assert store.get_controller("artifact_x") == escrow.id
        assert ledger.get_scrip("poor_buyer") == 50  # Unchanged
        assert ledger.get_scrip("seller") == 100  # Unchanged

        # Listing remains active
        check = escrow._check(["artifact_x"], "anyone")
        assert check["listing"]["status"] == "active"

    # AC-3: Seller cancels listing and reclaims artifact (happy_path)
    def test_ac_3_seller_cancels_reclaims(
        self, escrow_with_store: tuple[GenesisEscrow, ArtifactStore, Ledger]
    ) -> None:
        """AC-3: Seller cancels listing and reclaims artifact.

        Given:
          - Seller has deposited artifact X into escrow
          - No purchase has occurred
        When: Seller cancels the listing
        Then:
          - Artifact ownership returned to seller
          - Listing removed from escrow
          - Seller can re-list or use artifact
        """
        escrow, store, ledger = escrow_with_store

        # Seller creates and lists artifact
        store.write("artifact_x", "generic", "content", "seller")
        store.transfer_ownership("artifact_x", "seller", escrow.id)
        escrow._deposit(["artifact_x", 50], "seller")

        # Verify in escrow
        assert store.get_controller("artifact_x") == escrow.id

        # Cancel
        result = escrow._cancel(["artifact_x"], "seller")

        assert result["success"] is True
        assert store.get_controller("artifact_x") == "seller"

        # Can re-list (demonstrates artifact is usable)
        store.transfer_ownership("artifact_x", "seller", escrow.id)
        relist = escrow._deposit(["artifact_x", 75], "seller")
        assert relist["success"] is True

    # AC-4: Cannot purchase artifact not in escrow (error_case)
    def test_ac_4_cannot_purchase_unlisted(self) -> None:
        """AC-4: Cannot purchase artifact not in escrow.

        Given: Artifact X exists but is not deposited in escrow
        When: Buyer attempts to purchase artifact X
        Then:
          - Purchase fails with 'listing not found' error
          - No state changes occur
        """
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("owner", starting_scrip=100, starting_compute=50)
        ledger.create_principal("buyer", starting_scrip=500, starting_compute=50)

        escrow = GenesisEscrow(ledger, store)

        # Artifact exists but not in escrow
        store.write("artifact_x", "generic", "content", "owner")

        buyer_initial = ledger.get_scrip("buyer")

        result = escrow._purchase(["artifact_x"], "buyer")

        assert result["success"] is False
        assert "No listing" in result["error"] or "not found" in result["error"].lower()
        assert store.get_controller("artifact_x") == "owner"  # Unchanged
        assert ledger.get_scrip("buyer") == buyer_initial  # Unchanged

    # AC-5: Restricted buyer listing only allows designated buyer (edge_case)
    def test_ac_5_restricted_buyer_listing(
        self, escrow_with_store: tuple[GenesisEscrow, ArtifactStore, Ledger]
    ) -> None:
        """AC-5: Restricted buyer listing only allows designated buyer.

        Given:
          - Seller deposits artifact X with buyer restriction to Agent B
          - Agent C has sufficient funds
        When: Agent C attempts to purchase artifact X
        Then:
          - Purchase fails (restricted to Agent B)
          - Agent B can still purchase successfully
        """
        escrow, store, ledger = escrow_with_store

        # Seller creates artifact with buyer restriction
        store.write("artifact_x", "generic", "content", "seller")
        store.transfer_ownership("artifact_x", "seller", escrow.id)
        # Deposit with restriction to "restricted_buyer" (Agent B)
        escrow._deposit(["artifact_x", 50, "restricted_buyer"], "seller")

        # Agent C (buyer) attempts to purchase - should fail
        result = escrow._purchase(["artifact_x"], "buyer")
        assert result["success"] is False
        assert "restricted" in result["error"].lower()

        # Agent B (restricted_buyer) can purchase
        result = escrow._purchase(["artifact_x"], "restricted_buyer")
        assert result["success"] is True
        assert store.get_controller("artifact_x") == "restricted_buyer"


@pytest.mark.feature("escrow")
class TestEscrowEdgeCases:
    """Additional edge case tests for escrow robustness."""

    def test_seller_cannot_purchase_own_listing(self) -> None:
        """Seller should not be able to buy their own listing."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=200, starting_compute=50)

        escrow = GenesisEscrow(ledger, store)
        store.write("artifact", "generic", "content", "seller")
        store.transfer_ownership("artifact", "seller", escrow.id)
        escrow._deposit(["artifact", 50], "seller")

        result = escrow._purchase(["artifact"], "seller")

        assert result["success"] is False
        assert "own" in result["error"].lower()

    def test_cancel_after_purchase_fails(self) -> None:
        """Cannot cancel a completed sale."""
        ledger = Ledger()
        store = ArtifactStore()
        ledger.create_principal("seller", starting_scrip=100, starting_compute=50)
        ledger.create_principal("buyer", starting_scrip=200, starting_compute=50)

        escrow = GenesisEscrow(ledger, store)
        store.write("artifact", "generic", "content", "seller")
        store.transfer_ownership("artifact", "seller", escrow.id)
        escrow._deposit(["artifact", 50], "seller")
        escrow._purchase(["artifact"], "buyer")

        result = escrow._cancel(["artifact"], "seller")

        assert result["success"] is False
