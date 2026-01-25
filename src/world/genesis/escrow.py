"""Genesis Escrow - Trustless artifact trading (Plan #213 redesign)

Implements the Gatekeeper pattern for safe trading without trusting counterparties.

**Trading Flow (Plan #213):**
1. Seller creates artifact with:
   - access_contract_id = "genesis_contract_transferable_freeware"
   - metadata["authorized_writer"] = seller_id
2. Seller grants escrow write access: set authorized_writer = "genesis_escrow"
3. Seller deposits artifact on escrow (escrow verifies it has write access)
4. Buyer purchases:
   - Escrow transfers scrip from buyer to seller
   - Escrow sets authorized_writer = buyer_id
   - Buyer can now write to artifact

This uses the transferable_freeware contract which checks metadata["authorized_writer"]
for write permissions, not created_by. This allows artifact trading while keeping
created_by immutable (per ADR-0016).
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
    Genesis artifact for trustless artifact trading (Plan #213 redesign).

    Implements the Gatekeeper pattern using authorized_writer metadata:
    1. Seller creates artifact with transferable_freeware contract
    2. Seller grants escrow write access (sets authorized_writer = escrow)
    3. Seller registers listing with price
    4. Buyer pays price -> escrow sets authorized_writer to buyer, scrip to seller

    This enables safe trading without trusting counterparties while keeping
    created_by immutable (per ADR-0016). The transferable_freeware contract
    checks metadata["authorized_writer"] for write permissions.

    All method costs and descriptions are configurable via config.yaml.
    """

    ledger: Ledger
    artifact_store: ArtifactStore
    listings: dict[str, EscrowListing]
    # World reference for kernel delegation (Plan #111)
    _world: Any

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
        # World reference for kernel delegation (Plan #111)
        self._world: Any = None

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

    def set_world(self, world: Any) -> None:
        """Set world reference for kernel delegation (Plan #111).

        When set, this enables unprivileged access via KernelActions
        instead of direct Ledger/ArtifactStore calls.
        """
        self._world = world

    def _deposit(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Deposit an artifact into escrow for sale (Plan #213 redesign).

        IMPORTANT: Before depositing, you must:
        1. Use transferable_freeware contract on your artifact
        2. Set metadata["authorized_writer"] = "genesis_escrow"

        This grants escrow write access so it can transfer the authorized_writer
        to the buyer on purchase.

        Args: [artifact_id, price] or [artifact_id, price, buyer_id]
        - artifact_id: The artifact to sell (escrow must be authorized_writer)
        - price: Sale price in scrip
        - buyer_id: Optional - restrict purchase to specific buyer
        """
        if not args or len(args) < 2:
            return {
                "success": False,
                "error": "deposit requires [artifact_id, price] or [artifact_id, price, buyer_id]. "
                         "Example: genesis_escrow.deposit(['my_artifact', 50])"
            }

        artifact_id: str = args[0]
        price: Any = args[1]
        buyer_id: str | None = args[2] if len(args) > 2 else None

        # Plan #160: Type coercion now happens centrally in world.py
        # Validate price - Plan #160: Improved error message showing actual type
        if not isinstance(price, int):
            if isinstance(price, str) and price.isdigit():
                correct_price = int(price)
                return {
                    "success": False,
                    "error": f"Price must be an integer, got str: '{price}'. "
                             f"Fix: {{\"action_type\": \"invoke_artifact\", \"artifact_id\": \"genesis_escrow\", "
                             f"\"method\": \"deposit\", \"args\": [\"{artifact_id}\", {correct_price}]}}"
                }
            return {
                "success": False,
                "error": f"Price must be an integer, got {type(price).__name__}: {repr(price)}. "
                         f"Example: {{\"action_type\": \"invoke_artifact\", \"artifact_id\": \"genesis_escrow\", "
                         f"\"method\": \"deposit\", \"args\": [\"{artifact_id}\", 10]}}"
            }
        if price <= 0:
            return {"success": False, "error": f"Price must be positive (at least 1), got {price}."}

        # Check artifact exists
        artifact = self.artifact_store.get(artifact_id)
        if not artifact:
            return {
                "success": False,
                "error": f"Artifact '{artifact_id}' not found. "
                         f"Use query_kernel action to discover artifacts."
            }

        # Plan #213: Verify escrow has write access via authorized_writer
        # Seller must have set metadata["authorized_writer"] = "genesis_escrow"
        authorized_writer = artifact.metadata.get("authorized_writer")
        if authorized_writer != self.id:
            return {
                "success": False,
                "error": f"Escrow does not have write access to '{artifact_id}'. "
                         f"Fix with this action: "
                         f'{{\"action_type\": \"write_artifact\", \"artifact_id\": \"{artifact_id}\", '
                         f'\"metadata\": {{\"authorized_writer\": \"{self.id}\"}}}}'
                         f" (current authorized_writer: {authorized_writer or 'not set'})"
            }

        # Check not already listed
        if artifact_id in self.listings and self.listings[artifact_id]["status"] == "active":
            listing = self.listings[artifact_id]
            return {
                "success": False,
                "error": f"{artifact_id} is already listed for sale at price {listing['price']}. "
                         f"NEXT STEPS: Wait for a buyer, or cancel with genesis_escrow.cancel(['{artifact_id}'])."
            }

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
        """Purchase an artifact from escrow (Plan #213 redesign).

        Transfers price from buyer to seller, sets authorized_writer to buyer.

        Args: [artifact_id]
        """
        if not args or len(args) < 1:
            return {
                "success": False,
                "error": "purchase requires [artifact_id]. Example: genesis_escrow.purchase(['item_for_sale'])"
            }

        artifact_id: str = args[0]

        # Check listing exists and is active
        if artifact_id not in self.listings:
            return {
                "success": False,
                "error": f"No listing found for '{artifact_id}'. "
                         f"Use genesis_escrow.list_all([]) to see active listings."
            }

        listing = self.listings[artifact_id]
        if listing["status"] != "active":
            return {
                "success": False,
                "error": f"Listing for '{artifact_id}' is not active (status: {listing['status']}). "
                         f"It may have been purchased or cancelled."
            }

        # Check buyer restriction
        if listing["buyer_id"] and listing["buyer_id"] != invoker_id:
            return {"success": False, "error": f"This listing is restricted to buyer {listing['buyer_id']}"}

        # Can't buy your own listing
        if listing["seller_id"] == invoker_id:
            return {"success": False, "error": "Cannot purchase your own listing"}

        price = listing["price"]
        seller_id = listing["seller_id"]

        # Plan #213: Use kernel interface for atomic trade
        if self._world is not None:
            from ..kernel_interface import KernelActions, KernelState
            kernel_state = KernelState(self._world)
            kernel_actions = KernelActions(self._world)

            # Check buyer can afford
            buyer_balance = kernel_state.get_balance(invoker_id)
            if buyer_balance < price:
                return {
                    "success": False,
                    "error": f"Insufficient scrip. Need {price}, have {buyer_balance}"
                }

            # Execute the trade atomically:
            # 1. Transfer scrip from buyer to seller
            if not kernel_actions.transfer_scrip(invoker_id, seller_id, price):
                return {"success": False, "error": "Scrip transfer failed"}

            # 2. Plan #213: Set authorized_writer to buyer (not transfer_ownership)
            if not kernel_actions.update_artifact_metadata(
                self.id, artifact_id, "authorized_writer", invoker_id
            ):
                # Rollback scrip transfer
                kernel_actions.transfer_scrip(seller_id, invoker_id, price)
                return {"success": False, "error": "Failed to transfer write access (scrip refunded)"}
        else:
            # Legacy path: direct ledger/artifact_store access
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

            # 2. Plan #213: Set authorized_writer to buyer directly
            artifact = self.artifact_store.get(artifact_id)
            if artifact:
                artifact.metadata["authorized_writer"] = invoker_id
            else:
                # Rollback scrip transfer
                self.ledger.transfer_scrip(seller_id, invoker_id, price)
                return {"success": False, "error": "Artifact not found (scrip refunded)"}

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
        """Cancel an escrow listing and return write access to seller (Plan #213).

        Only the seller can cancel. Only active listings can be cancelled.

        Args: [artifact_id]
        """
        if not args or len(args) < 1:
            return {
                "success": False,
                "error": "cancel requires [artifact_id]. Example: genesis_escrow.cancel(['my_listed_item'])"
            }

        artifact_id: str = args[0]

        # Check listing exists
        if artifact_id not in self.listings:
            return {
                "success": False,
                "error": f"No listing found for '{artifact_id}'. "
                         f"Use genesis_escrow.list_all([]) to see your active listings."
            }

        listing = self.listings[artifact_id]

        # Only seller can cancel
        if listing["seller_id"] != invoker_id:
            return {"success": False, "error": "Only the seller can cancel a listing"}

        # Must be active
        if listing["status"] != "active":
            return {"success": False, "error": f"Listing is not active (status: {listing['status']})"}

        # Plan #213: Return write access to seller by setting authorized_writer
        if self._world is not None:
            from ..kernel_interface import KernelActions
            kernel_actions = KernelActions(self._world)
            success = kernel_actions.update_artifact_metadata(
                self.id, artifact_id, "authorized_writer", invoker_id
            )
        else:
            artifact = self.artifact_store.get(artifact_id)
            success = artifact is not None
            if success:
                artifact.metadata["authorized_writer"] = invoker_id

        if not success:
            return {"success": False, "error": "Failed to return write access to seller"}

        # Mark as cancelled
        listing["status"] = "cancelled"

        return {
            "success": True,
            "artifact_id": artifact_id,
            "seller": invoker_id,
            "message": f"Cancelled listing for {artifact_id}, write access returned to {invoker_id}"
        }

    def _check(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check the status of an escrow listing.

        Args: [artifact_id]
        """
        if not args or len(args) < 1:
            return {
                "success": False,
                "error": "check requires [artifact_id]. Example: genesis_escrow.check(['item_id'])"
            }

        artifact_id: str = args[0]

        if artifact_id not in self.listings:
            return {
                "success": False,
                "error": f"No listing found for '{artifact_id}'. "
                         f"Use genesis_escrow.list_all([]) to see all listings."
            }

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

    def get_interface(self) -> dict[str, Any]:
        """Get detailed interface schema for the escrow (Plan #114, #213)."""
        return {
            "description": self.description,
            "dataType": "service",
            "tools": [
                {
                    "name": "deposit",
                    "description": "Deposit an artifact into escrow for sale. IMPORTANT: First set metadata['authorized_writer'] = 'genesis_escrow' on your artifact (requires transferable_freeware contract)",
                    "cost": self.methods["deposit"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "artifact_id": {
                                "type": "string",
                                "description": "ID of artifact to sell (escrow must be authorized_writer)"
                            },
                            "price": {
                                "type": "integer",
                                "description": "Sale price in scrip",
                                "minimum": 1
                            },
                            "buyer_id": {
                                "type": "string",
                                "description": "Optional: restrict purchase to specific buyer"
                            }
                        },
                        "required": ["artifact_id", "price"]
                    }
                },
                {
                    "name": "purchase",
                    "description": "Purchase an artifact from escrow. Transfers scrip to seller, sets authorized_writer to buyer.",
                    "cost": self.methods["purchase"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "artifact_id": {
                                "type": "string",
                                "description": "ID of artifact to purchase"
                            }
                        },
                        "required": ["artifact_id"]
                    }
                },
                {
                    "name": "cancel",
                    "description": "Cancel an escrow listing and return artifact to seller. Only seller can cancel.",
                    "cost": self.methods["cancel"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "artifact_id": {
                                "type": "string",
                                "description": "ID of artifact listing to cancel"
                            }
                        },
                        "required": ["artifact_id"]
                    }
                },
                {
                    "name": "check",
                    "description": "Check the status of an escrow listing",
                    "cost": self.methods["check"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "artifact_id": {
                                "type": "string",
                                "description": "ID of artifact to check"
                            }
                        },
                        "required": ["artifact_id"]
                    }
                },
                {
                    "name": "list_active",
                    "description": "List all active escrow listings",
                    "cost": self.methods["list_active"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
        }
