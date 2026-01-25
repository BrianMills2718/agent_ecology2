"""Genesis Ledger - Proxy to world ledger

Provides balance queries, scrip transfers, ownership transfers, and budget management.
"""

from __future__ import annotations

import uuid
from typing import Any

from ...config import get_validated_config
from ...config_schema import GenesisConfig
from ..ledger import Ledger
from ..artifacts import ArtifactStore
from ..errors import (
    ErrorCode,
    permission_error,
    resource_error,
    validation_error,
)
from .base import GenesisArtifact


class GenesisLedger(GenesisArtifact):
    """
    Genesis artifact that proxies to the world ledger.

    Two types of balances:
    - resources: Action budget (rate-limited via RateTracker) - real resource constraint
    - scrip: Economic currency (persistent) - medium of exchange

    All method costs and descriptions are configurable via config.yaml.
    """

    ledger: Ledger
    artifact_store: ArtifactStore | None
    # World reference for kernel delegation (Plan #111)
    _world: Any

    def __init__(
        self,
        ledger: Ledger,
        artifact_store: ArtifactStore | None = None,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        ledger_cfg = cfg.ledger

        super().__init__(
            artifact_id=ledger_cfg.id,
            description=ledger_cfg.description
        )
        self.ledger = ledger
        self.artifact_store = artifact_store
        # World reference for kernel delegation (Plan #111)
        self._world: Any = None

        # Register methods with costs/descriptions from config
        self.register_method(
            name="balance",
            handler=self._balance,
            cost=ledger_cfg.methods.balance.cost,
            description=ledger_cfg.methods.balance.description
        )

        self.register_method(
            name="all_balances",
            handler=self._all_balances,
            cost=ledger_cfg.methods.all_balances.cost,
            description=ledger_cfg.methods.all_balances.description
        )

        self.register_method(
            name="transfer",
            handler=self._transfer,
            cost=ledger_cfg.methods.transfer.cost,
            description=ledger_cfg.methods.transfer.description
        )

        self.register_method(
            name="spawn_principal",
            handler=self._spawn_principal,
            cost=ledger_cfg.methods.spawn_principal.cost,
            description=ledger_cfg.methods.spawn_principal.description
        )

        self.register_method(
            name="transfer_ownership",
            handler=self._transfer_ownership,
            cost=ledger_cfg.methods.transfer_ownership.cost,
            description=ledger_cfg.methods.transfer_ownership.description
        )

        self.register_method(
            name="transfer_budget",
            handler=self._transfer_budget,
            cost=ledger_cfg.methods.transfer_budget.cost,
            description=ledger_cfg.methods.transfer_budget.description
        )

        self.register_method(
            name="get_budget",
            handler=self._get_budget,
            cost=ledger_cfg.methods.get_budget.cost,
            description=ledger_cfg.methods.get_budget.description
        )

    def set_world(self, world: Any) -> None:
        """Set world reference for kernel delegation (Plan #111).

        When set, this enables unprivileged access via KernelActions
        instead of direct Ledger/ArtifactStore calls.
        """
        self._world = world

    def _balance(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get balance for an agent (resources and scrip)."""
        if not args or len(args) < 1:
            return validation_error(
                f"balance requires [agent_id]. Example: genesis_ledger.balance(['{invoker_id}'])",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["agent_id"],
            )
        agent_id: str = args[0]
        llm_tokens = self.ledger.get_llm_tokens(agent_id)
        return {
            "success": True,
            "agent_id": agent_id,
            "llm_tokens": llm_tokens,
            "scrip": self.ledger.get_scrip(agent_id),
            "resources": self.ledger.get_all_resources(agent_id)
        }

    def _all_balances(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get all balances (resources and scrip for each agent)."""
        # Include both legacy format and new format
        legacy = self.ledger.get_all_balances()
        full = self.ledger.get_all_balances_full()
        return {
            "success": True,
            "balances": legacy,  # Backward compat
            "balances_full": full  # New: includes all resources
        }

    def _transfer(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer SCRIP between agents (not flow - flow is non-transferable)"""
        if not args or len(args) < 3:
            # Plan #160: If 2 args provided, they might be trying to transfer ownership
            hint = ""
            if args and len(args) == 2:
                hint = (
                    " NOTE: 'transfer' sends SCRIP (money). "
                    "To transfer ARTIFACT OWNERSHIP, use 'transfer_ownership' method instead: "
                    f"genesis_ledger.transfer_ownership(['{args[0]}', '{args[1]}'])"
                )
            return validation_error(
                f"transfer requires [from_id, to_id, amount] (3 args, got {len(args or [])}).{hint}",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["from_id", "to_id", "amount"],
            )

        from_id: str = args[0]
        to_id: str = args[1]
        amount: Any = args[2]

        # Security check: invoker can only transfer FROM themselves
        if from_id != invoker_id:
            return permission_error(
                f"Cannot transfer from {from_id} - you are {invoker_id}. "
                f"You can only transfer YOUR OWN scrip. "
                f"To send your scrip: genesis_ledger.transfer(['{invoker_id}', '{to_id}', {amount}])",
                code=ErrorCode.NOT_AUTHORIZED,
                invoker=invoker_id,
                target=from_id,
            )

        # Plan #160: Improved error message showing actual type
        if not isinstance(amount, int):
            hint = ""
            if isinstance(amount, str):
                if amount.isdigit():
                    hint = (
                        f" Fix: {{\"action_type\": \"invoke_artifact\", \"artifact_id\": \"genesis_ledger\", "
                        f"\"method\": \"transfer\", \"args\": [\"{from_id}\", \"{to_id}\", {int(amount)}]}}"
                    )
                else:
                    # Looks like an artifact name - they probably want transfer_ownership
                    hint = (
                        f" NOTE: You seem to be trying to transfer an artifact '{amount}'. "
                        f"'transfer' is for SCRIP (money), not artifacts. "
                        f"To transfer ARTIFACT OWNERSHIP, use: {{\"action_type\": \"invoke_artifact\", "
                        f"\"artifact_id\": \"genesis_ledger\", \"method\": \"transfer_ownership\", "
                        f"\"args\": [\"{amount}\", \"{to_id}\"]}}"
                    )
            return validation_error(
                f"Amount must be an integer, got {type(amount).__name__}: {repr(amount)}.{hint}",
                code=ErrorCode.INVALID_ARGUMENT,
                provided=amount,
            )
        if amount <= 0:
            return validation_error(
                f"Amount must be positive, got {amount}",
                code=ErrorCode.INVALID_ARGUMENT,
                provided=amount,
            )

        success = self.ledger.transfer_scrip(from_id, to_id, amount)
        if success:
            return {
                "success": True,
                "transferred": amount,
                "currency": "scrip",
                "from": from_id,
                "to": to_id,
                "from_scrip_after": self.ledger.get_scrip(from_id),
                "to_scrip_after": self.ledger.get_scrip(to_id)
            }
        else:
            return permission_error(
                "Transfer failed (insufficient scrip or invalid recipient)",
                code=ErrorCode.INSUFFICIENT_FUNDS,
                from_id=from_id,
                to_id=to_id,
                amount=amount,
            )

    def _spawn_principal(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Spawn a new principal with 0 scrip and 0 compute.

        The new principal starts with nothing - parent must transfer resources
        to keep it alive.

        Args:
            args: [] (no arguments needed, system generates ID)
            invoker_id: The agent spawning the new principal

        Returns:
            {"success": True, "principal_id": new_id} on success
        """
        # Generate a unique principal ID
        new_id = f"agent_{uuid.uuid4().hex[:8]}"

        # Plan #111: Use kernel interface when world is set
        if self._world is not None:
            from ..kernel_interface import KernelActions
            kernel_actions = KernelActions(self._world)
            success = kernel_actions.create_principal(new_id, starting_scrip=0, starting_compute=0)
            if not success:
                # Principal already exists (unlikely with UUID)
                return {"success": False, "error": f"Principal {new_id} already exists"}
        else:
            # Legacy path: direct ledger access
            self.ledger.create_principal(new_id, starting_scrip=0, starting_compute=0)

        return {"success": True, "principal_id": new_id}

    def _transfer_ownership(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer ownership of an artifact to another principal.

        Args:
            args: [artifact_id, to_id] - artifact to transfer and new owner
            invoker_id: Must be the current owner of the artifact

        Returns:
            {"success": True, "artifact_id": ..., "from_owner": ..., "to_owner": ...}
        """
        if not args or len(args) < 2:
            return validation_error(
                "transfer_ownership requires [artifact_id, to_id]. "
                "Example: genesis_ledger.transfer_ownership(['my_artifact', 'buyer_agent'])",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["artifact_id", "to_id"],
            )

        artifact_id: str = args[0]
        to_id: str = args[1]

        # Plan #111: Use kernel interface when world is set
        if self._world is not None:
            from ..kernel_interface import KernelActions, KernelState
            kernel_state = KernelState(self._world)
            kernel_actions = KernelActions(self._world)

            # Check artifact exists
            metadata = kernel_state.get_artifact_metadata(artifact_id)
            if metadata is None:
                return resource_error(
                    f"Artifact '{artifact_id}' not found. "
                    f"Use query_kernel action to discover artifacts.",
                    code=ErrorCode.NOT_FOUND,
                    artifact_id=artifact_id,
                )

            # Security check: can only transfer artifacts you control
            # Per ADR-0016: Check metadata["controller"] (not created_by which is immutable)
            current_controller = metadata.get("controller", metadata["created_by"])
            if current_controller != invoker_id:
                # Prescriptive error: if in escrow, tell them what to do next
                if current_controller == "genesis_escrow":
                    return permission_error(
                        f"{artifact_id} is in escrow (you already transferred it). "
                        f"NEXT STEPS: Use genesis_escrow.check(['{artifact_id}']) to see listing status, "
                        f"or genesis_escrow.cancel(['{artifact_id}']) to reclaim it.",
                        code=ErrorCode.NOT_OWNER,
                        artifact_id=artifact_id,
                        owner=current_controller,
                        invoker=invoker_id,
                    )
                else:
                    return permission_error(
                        f"Cannot transfer {artifact_id} - you are not the controller (controller is {current_controller}). "
                        f"You may need to purchase it first via genesis_escrow.purchase(['{artifact_id}']).",
                        code=ErrorCode.NOT_OWNER,
                        artifact_id=artifact_id,
                        owner=current_controller,
                        invoker=invoker_id,
                    )

            # Perform the transfer via kernel
            success = kernel_actions.transfer_ownership(invoker_id, artifact_id, to_id)
            if success:
                return {
                    "success": True,
                    "artifact_id": artifact_id,
                    "from_owner": invoker_id,
                    "to_owner": to_id
                }
            else:
                return resource_error(
                    "Transfer failed",
                    code=ErrorCode.NOT_FOUND,
                    artifact_id=artifact_id,
                )

        # Legacy path: direct artifact_store access
        if not self.artifact_store:
            return resource_error(
                "Artifact store not configured",
                code=ErrorCode.NOT_FOUND,
            )

        # Get the artifact to verify ownership
        artifact = self.artifact_store.get(artifact_id)
        if not artifact:
            return resource_error(
                f"Artifact '{artifact_id}' not found. "
                f"Use query_kernel action to discover artifacts.",
                code=ErrorCode.NOT_FOUND,
                artifact_id=artifact_id,
            )

        # Security check: can only transfer artifacts you control
        # Per ADR-0016: Check metadata["controller"] (not created_by which is immutable)
        current_controller = artifact.metadata.get("controller", artifact.created_by)
        if current_controller != invoker_id:
            # Prescriptive error: if in escrow, tell them what to do next
            if current_controller == "genesis_escrow":
                return permission_error(
                    f"{artifact_id} is in escrow (you already transferred it). "
                    f"NEXT STEPS: Use genesis_escrow.check(['{artifact_id}']) to see listing status, "
                    f"or genesis_escrow.cancel(['{artifact_id}']) to reclaim it.",
                    code=ErrorCode.NOT_OWNER,
                    artifact_id=artifact_id,
                    owner=current_controller,
                    invoker=invoker_id,
                )
            else:
                return permission_error(
                    f"Cannot transfer {artifact_id} - you are not the controller (controller is {current_controller}). "
                    f"You may need to purchase it first via genesis_escrow.purchase(['{artifact_id}']).",
                    code=ErrorCode.NOT_OWNER,
                    artifact_id=artifact_id,
                    owner=current_controller,
                    invoker=invoker_id,
                )

        # Perform the transfer
        success = self.artifact_store.transfer_ownership(artifact_id, invoker_id, to_id)
        if success:
            return {
                "success": True,
                "artifact_id": artifact_id,
                "from_owner": invoker_id,
                "to_owner": to_id
            }
        else:
            return resource_error(
                "Transfer failed",
                code=ErrorCode.NOT_FOUND,
                artifact_id=artifact_id,
            )

    def _transfer_budget(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer LLM budget to another agent.

        LLM budget is a depletable resource representing dollars available
        for LLM API calls. Making it tradeable enables budget markets.

        Args:
            args: [to_id, amount] - recipient and amount to transfer
            invoker_id: The caller (transfers FROM this principal)

        Returns:
            {"success": True, "transferred": ..., "from": ..., "to": ...}
        """
        if not args or len(args) < 2:
            return validation_error(
                "transfer_budget requires [to_id, amount]. "
                "Example: genesis_ledger.transfer_budget(['other_agent', 100])",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["to_id", "amount"],
            )

        to_id: str = args[0]
        amount: Any = args[1]

        # Validate amount
        if not isinstance(amount, (int, float)) or amount <= 0:
            return validation_error(
                f"Amount must be a positive number, got {type(amount).__name__}: {repr(amount)}. "
                f"Use a number like 100, not a string like \"100\".",
                code=ErrorCode.INVALID_ARGUMENT,
                provided=amount,
            )

        # Check invoker has sufficient budget
        current_budget = self.ledger.get_resource(invoker_id, "llm_budget")
        if current_budget < amount:
            return permission_error(
                f"Insufficient LLM budget. Have {current_budget}, need {amount}",
                code=ErrorCode.INSUFFICIENT_FUNDS,
                from_id=invoker_id,
                current=current_budget,
                requested=amount,
            )

        # Perform transfer via ledger
        self.ledger.spend_resource(invoker_id, "llm_budget", float(amount))
        recipient_budget = self.ledger.get_resource(to_id, "llm_budget")
        self.ledger.set_resource(to_id, "llm_budget", recipient_budget + float(amount))

        return {
            "success": True,
            "transferred": amount,
            "resource": "llm_budget",
            "from": invoker_id,
            "to": to_id,
            "from_budget_after": self.ledger.get_resource(invoker_id, "llm_budget"),
            "to_budget_after": self.ledger.get_resource(to_id, "llm_budget")
        }

    def _get_budget(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get LLM budget for an agent.

        Args:
            args: [agent_id] - the agent to query
            invoker_id: The caller (anyone can query)

        Returns:
            {"success": True, "agent_id": ..., "budget": ...}
        """
        if not args or len(args) < 1:
            return validation_error(
                f"get_budget requires [agent_id]. Example: genesis_ledger.get_budget(['{invoker_id}'])",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["agent_id"],
            )

        agent_id: str = args[0]
        budget = self.ledger.get_resource(agent_id, "llm_budget")

        return {
            "success": True,
            "agent_id": agent_id,
            "budget": budget
        }

    def get_interface(self) -> dict[str, Any]:
        """Get detailed interface schema for the ledger (Plan #14)."""
        return {
            "description": self.description,
            "tools": [
                {
                    "name": "balance",
                    "description": "Get balance for an agent (resources and scrip)",
                    "cost": self.methods["balance"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent to query"
                            }
                        },
                        "required": ["agent_id"]
                    }
                },
                {
                    "name": "all_balances",
                    "description": "Get balances for all principals",
                    "cost": self.methods["all_balances"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "transfer",
                    "description": "Transfer scrip to another principal",
                    "cost": self.methods["transfer"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "to": {
                                "type": "string",
                                "description": "Recipient principal ID"
                            },
                            "amount": {
                                "type": "integer",
                                "description": "Amount of scrip to transfer",
                                "minimum": 1
                            }
                        },
                        "required": ["to", "amount"]
                    }
                },
                {
                    "name": "spawn_principal",
                    "description": "Create a new principal with initial scrip",
                    "cost": self.methods["spawn_principal"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "principal_id": {
                                "type": "string",
                                "description": "ID for the new principal"
                            },
                            "initial_scrip": {
                                "type": "integer",
                                "description": "Initial scrip balance",
                                "minimum": 0
                            }
                        },
                        "required": ["principal_id"]
                    }
                },
                {
                    "name": "transfer_ownership",
                    "description": "Transfer artifact ownership to another principal",
                    "cost": self.methods["transfer_ownership"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "artifact_id": {
                                "type": "string",
                                "description": "ID of the artifact to transfer"
                            },
                            "to": {
                                "type": "string",
                                "description": "New owner principal ID"
                            }
                        },
                        "required": ["artifact_id", "to"]
                    }
                }
            ]
        }
