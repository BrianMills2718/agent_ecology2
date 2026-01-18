"""Genesis Escrow - Trustless artifact trading

Implements the Gatekeeper pattern for safe trading without trusting counterparties.
"""

from __future__ import annotations

from typing import Any

from ...config import get_validated_config
from ...config_schema import GenesisConfig
from ..ledger import Ledger
from ..artifacts import ArtifactStore
from .base import GenesisArtifact, _get_error_message
from .types import EscrowListing


class GenesisEscrow(GenesisArtifact):
    """
    Genesis artifact for trustless artifact trading.

    Implements the Gatekeeper pattern:
    1. Seller transfers artifact ownership to escrow
    2. Seller registers listing with price
    3. Buyer pays price -> escrow transfers ownership to buyer, scrip to seller

    This enables safe trading without trusting counterparties.
    All method costs and descriptions are configurable via config.yaml.
    """

    ledger: Ledger
    artifact_store: ArtifactStore
    listings: dict[str, EscrowListing]

    def __init__(
        self,
        ledger: Ledger,
        artifact_store: ArtifactStore,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        """
        Args:
            ledger: The world's Ledger instance (for scrip transfers)
            artifact_store: The world's ArtifactStore (for ownership transfers)
            genesis_config: Optional genesis config (uses global if not provided)
        """
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        escrow_cfg = cfg.escrow

        super().__init__(
            artifact_id=escrow_cfg.id,
            description=escrow_cfg.description
        )
        self.ledger = ledger
        self.artifact_store = artifact_store
        self.listings = {}

        # Register methods with costs/descriptions from config
        self.register_method(
            name="deposit",
            handler=self._deposit,
            cost=escrow_cfg.methods.deposit.cost,
            description=escrow_cfg.methods.deposit.description
        )

        self.register_method(
            name="purchase",
            handler=self._purchase,
            cost=escrow_cfg.methods.purchase.cost,
            description=escrow_cfg.methods.purchase.description
        )

        self.register_method(
            name="cancel",
            handler=self._cancel,
            cost=escrow_cfg.methods.cancel.cost,
            description=escrow_cfg.methods.cancel.description
        )

        self.register_method(
            name="check",
            handler=self._check,
            cost=escrow_cfg.methods.check.cost,
            description=escrow_cfg.methods.check.description
        )

        self.register_method(
            name="list_active",
            handler=self._list_active,
            cost=escrow_cfg.methods.list_active.cost,
            description=escrow_cfg.methods.list_active.description
        )

    def _deposit(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Deposit an artifact into escrow for sale.

        IMPORTANT: You must first transfer ownership to escrow:
        invoke_artifact("genesis_ledger", "transfer_ownership", [artifact_id, "genesis_escrow"])

        Args: [artifact_id, price] or [artifact_id, price, buyer_id]
        - artifact_id: The artifact to sell (must already be owned by escrow)
        - price: Sale price in scrip
        - buyer_id: Optional - restrict purchase to specific buyer
        """
        if not args or len(args) < 2:
            return {"success": False, "error": "deposit requires [artifact_id, price] or [artifact_id, price, buyer_id]"}

        artifact_id: str = args[0]
        price: Any = args[1]
        buyer_id: str | None = args[2] if len(args) > 2 else None

        # Validate price
        if not isinstance(price, int) or price <= 0:
            return {"success": False, "error": "Price must be a positive integer"}

        # Check artifact exists
        artifact = self.artifact_store.get(artifact_id)
        if not artifact:
            return {"success": False, "error": f"Artifact {artifact_id} not found"}

        # Verify escrow owns the artifact (seller must have transferred first)
        if artifact.owner_id != self.id:
            return {
                "success": False,
                "error": _get_error_message("escrow_not_owner", artifact_id=artifact_id, escrow_id=self.id)
            }

        # Check not already listed
        if artifact_id in self.listings and self.listings[artifact_id]["status"] == "active":
            return {"success": False, "error": f"Artifact {artifact_id} is already listed"}

        # Create listing
        self.listings[artifact_id] = {
            "artifact_id": artifact_id,
            "seller_id": invoker_id,
            "price": price,
            "buyer_id": buyer_id,
            "status": "active"
        }

        return {
            "success": True,
            "artifact_id": artifact_id,
            "price": price,
            "seller": invoker_id,
            "message": f"Listed {artifact_id} for {price} scrip" + (f" (restricted to {buyer_id})" if buyer_id else "")
        }

    def _purchase(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Purchase an artifact from escrow.

        Transfers price from buyer to seller, ownership from escrow to buyer.

        Args: [artifact_id]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "purchase requires [artifact_id]"}

        artifact_id: str = args[0]

        # Check listing exists and is active
        if artifact_id not in self.listings:
            return {"success": False, "error": f"No listing found for {artifact_id}"}

        listing = self.listings[artifact_id]
        if listing["status"] != "active":
            return {"success": False, "error": f"Listing for {artifact_id} is not active (status: {listing['status']})"}

        # Check buyer restriction
        if listing["buyer_id"] and listing["buyer_id"] != invoker_id:
            return {"success": False, "error": f"This listing is restricted to buyer {listing['buyer_id']}"}

        # Can't buy your own listing
        if listing["seller_id"] == invoker_id:
            return {"success": False, "error": "Cannot purchase your own listing"}

        price = listing["price"]
        seller_id = listing["seller_id"]

        # Check buyer can afford
        if not self.ledger.can_afford_scrip(invoker_id, price):
            return {
                "success": False,
                "error": f"Insufficient scrip. Need {price}, have {self.ledger.get_scrip(invoker_id)}"
            }

        # Execute the trade atomically:
        # 1. Transfer scrip from buyer to seller
        if not self.ledger.transfer_scrip(invoker_id, seller_id, price):
            return {"success": False, "error": "Scrip transfer failed"}

        # 2. Transfer ownership from escrow to buyer
        if not self.artifact_store.transfer_ownership(artifact_id, self.id, invoker_id):
            # Rollback scrip transfer
            self.ledger.transfer_scrip(seller_id, invoker_id, price)
            return {"success": False, "error": "Ownership transfer failed (scrip refunded)"}

        # Mark listing as completed
        listing["status"] = "completed"

        return {
            "success": True,
            "artifact_id": artifact_id,
            "price": price,
            "seller": seller_id,
            "buyer": invoker_id,
            "message": f"Purchased {artifact_id} for {price} scrip from {seller_id}"
        }

    def _cancel(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Cancel an escrow listing and return artifact to seller.

        Only the seller can cancel. Only active listings can be cancelled.

        Args: [artifact_id]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "cancel requires [artifact_id]"}

        artifact_id: str = args[0]

        # Check listing exists
        if artifact_id not in self.listings:
            return {"success": False, "error": f"No listing found for {artifact_id}"}

        listing = self.listings[artifact_id]

        # Only seller can cancel
        if listing["seller_id"] != invoker_id:
            return {"success": False, "error": "Only the seller can cancel a listing"}

        # Must be active
        if listing["status"] != "active":
            return {"success": False, "error": f"Listing is not active (status: {listing['status']})"}

        # Return ownership to seller
        if not self.artifact_store.transfer_ownership(artifact_id, self.id, invoker_id):
            return {"success": False, "error": "Failed to return ownership to seller"}

        # Mark as cancelled
        listing["status"] = "cancelled"

        return {
            "success": True,
            "artifact_id": artifact_id,
            "seller": invoker_id,
            "message": f"Cancelled listing for {artifact_id}, ownership returned to {invoker_id}"
        }

    def _check(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check the status of an escrow listing.

        Args: [artifact_id]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "check requires [artifact_id]"}

        artifact_id: str = args[0]

        if artifact_id not in self.listings:
            return {"success": False, "error": f"No listing found for {artifact_id}"}

        listing = self.listings[artifact_id]
        return {
            "success": True,
            "listing": listing
        }

    def _list_active(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List all active escrow listings.

        Args: []
        """
        active = [
            listing for listing in self.listings.values()
            if listing["status"] == "active"
        ]
        return {
            "success": True,
            "listings": active,
            "count": len(active)
        }
