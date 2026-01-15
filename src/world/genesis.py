"""Genesis Artifacts - System-owned proxy artifacts

Genesis artifacts are special artifacts that:
1. Are owned by "system" (cannot be modified by agents)
2. Act as proxies to kernel functions (ledger, mint)
3. Have special cost rules (some functions are free)

These enable agents to interact with core infrastructure through
the same invoke_artifact mechanism they use for agent-created artifacts.
"""

# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
# ADR-0003: Contracts can do anything
#
# Genesis artifacts: ledger, oracle, escrow, event_log, rights_registry.
# System-provided, solve cold-start problem.
# --- GOVERNANCE END ---
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable, TypedDict, cast

from ..config import get_genesis_config, get, get_validated_config
from ..config_schema import GenesisConfig

from .ledger import Ledger
from .artifacts import ArtifactStore
from .logger import EventLogger
from .errors import (
    ErrorCode,
    permission_error,
    resource_error,
    validation_error,
)


# System owner ID - cannot be modified by agents
SYSTEM_OWNER: str = "system"


def _get_error_message(error_type: str, **kwargs: Any) -> str:
    """Get a configurable error message with placeholders filled in.

    Args:
        error_type: One of 'escrow_not_owner', etc.
        **kwargs: Placeholder values (artifact_id, escrow_id)

    Returns:
        Formatted error message from config (or default if not configured).
    """
    defaults: dict[str, str] = {
        "escrow_not_owner": "Escrow does not own {artifact_id}. See handbook_trading for the 2-step process: 1) genesis_ledger.transfer_ownership([artifact_id, '{escrow_id}']), 2) deposit.",
    }

    template: str = get(f"agent.errors.{error_type}") or defaults.get(error_type, f"Error: {error_type}")

    try:
        return template.format(**kwargs)
    except KeyError:
        return template


class MethodInfo(TypedDict):
    """Information about a genesis method for listing."""
    name: str
    cost: int
    description: str


class BalanceResult(TypedDict):
    """Result from balance query."""
    success: bool
    agent_id: str
    flow: int
    scrip: int


class AllBalancesResult(TypedDict):
    """Result from all_balances query."""
    success: bool
    balances: dict[str, dict[str, int]]


class TransferResult(TypedDict, total=False):
    """Result from transfer operation."""
    success: bool
    error: str
    transferred: int
    currency: str
    to: str
    from_scrip_after: int
    to_scrip_after: int


class SpawnPrincipalResult(TypedDict, total=False):
    """Result from spawn_principal operation."""
    success: bool
    error: str
    principal_id: str


class MintStatusResult(TypedDict):
    """Result from mint status query."""
    success: bool
    mint: str
    type: str
    pending_submissions: int
    scored_submissions: int
    total_submissions: int


class SubmissionInfo(TypedDict, total=False):
    """Information about a submission."""
    submitter: str
    status: str
    score: int | None
    reason: str | None


class SubmitResult(TypedDict, total=False):
    """Result from submit operation."""
    success: bool
    error: str
    message: str
    receipt: str


class CheckResult(TypedDict, total=False):
    """Result from check operation."""
    success: bool
    error: str
    submission: SubmissionInfo


class ProcessResult(TypedDict, total=False):
    """Result from process operation."""
    success: bool
    message: str
    artifact_id: str
    score: int
    reason: str
    credits_minted: int
    submitter: str
    error: str


class QuotaInfo(TypedDict):
    """Quota information for an agent."""
    compute_quota: int
    disk_quota: int
    disk_used: int
    disk_available: int


class GenericQuotaInfo(TypedDict):
    """Generic quota information for an agent (all resources)."""
    quotas: dict[str, float]
    disk_used: int
    disk_available: int


class CheckQuotaResult(TypedDict, total=False):
    """Result from check_quota operation."""
    success: bool
    error: str
    agent_id: str
    compute_quota: int
    disk_quota: int
    disk_used: int
    disk_available: int


class AllQuotasResult(TypedDict):
    """Result from all_quotas operation."""
    success: bool
    quotas: dict[str, QuotaInfo]


class TransferQuotaResult(TypedDict, total=False):
    """Result from transfer_quota operation."""
    success: bool
    error: str
    transferred: int
    quota_type: str
    to: str
    from_new_quota: int
    to_new_quota: int


class ReadEventsResult(TypedDict):
    """Result from read events operation."""
    success: bool
    events: list[dict[str, Any]]
    count: int
    total_available: int
    warning: str


class GenesisArtifactDict(TypedDict):
    """Dictionary representation of a genesis artifact."""
    id: str
    type: str
    owner_id: str
    content: str
    methods: list[MethodInfo]


@dataclass
class GenesisMethod:
    """A method exposed by a genesis artifact"""
    name: str
    handler: Callable[[list[Any], str], dict[str, Any]]
    cost: int  # 0 = free (system-subsidized)
    description: str


class GenesisArtifact:
    """Base class for genesis artifacts (system proxies)"""

    id: str
    type: str
    owner_id: str
    description: str
    methods: dict[str, GenesisMethod]

    def __init__(self, artifact_id: str, description: str) -> None:
        self.id = artifact_id
        self.type = "genesis"
        self.owner_id = SYSTEM_OWNER
        self.description = description
        self.methods = {}

    def register_method(
        self,
        name: str,
        handler: Callable[[list[Any], str], dict[str, Any]],
        cost: int = 0,
        description: str = ""
    ) -> None:
        """Register a callable method on this genesis artifact"""
        self.methods[name] = GenesisMethod(
            name=name,
            handler=handler,
            cost=cost,
            description=description
        )

    def get_method(self, method_name: str) -> GenesisMethod | None:
        """Get a method by name"""
        return self.methods.get(method_name)

    def list_methods(self) -> list[MethodInfo]:
        """List available methods"""
        return [
            {"name": m.name, "cost": m.cost, "description": m.description}
            for m in self.methods.values()
        ]

    def get_interface(self) -> dict[str, Any]:
        """Get the interface schema for this artifact (Plan #14).

        Returns a JSON Schema-compatible interface describing the artifact's
        tools (methods) and their inputs/outputs. Uses MCP-compatible format.

        Override in subclasses to add detailed inputSchema for each method.
        """
        tools = []
        for method in self.methods.values():
            tools.append({
                "name": method.name,
                "description": method.description,
                "cost": method.cost,
            })
        return {
            "description": self.description,
            "tools": tools,
        }

    def to_dict(self) -> GenesisArtifactDict:
        """Convert to dict for artifact listing"""
        return {
            "id": self.id,
            "type": self.type,
            "owner_id": self.owner_id,
            "content": self.description,
            "methods": self.list_methods()
        }


class TransferOwnershipResult(TypedDict, total=False):
    """Result from transfer_ownership operation."""
    success: bool
    error: str
    artifact_id: str
    from_owner: str
    to_owner: str


class GenesisLedger(GenesisArtifact):
    """
    Genesis artifact that proxies to the world ledger.

    Two types of balances:
    - flow: Action budget (resets each tick) - real resource constraint
    - scrip: Economic currency (persistent) - medium of exchange

    All method costs and descriptions are configurable via config.yaml.
    """

    ledger: Ledger
    artifact_store: ArtifactStore | None

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

    def _balance(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get balance for an agent (resources and scrip)."""
        if not args or len(args) < 1:
            return validation_error(
                "balance requires [agent_id]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["agent_id"],
            )
        agent_id: str = args[0]
        compute = self.ledger.get_compute(agent_id)
        return {
            "success": True,
            "agent_id": agent_id,
            "flow": compute,  # Backward compat
            "compute": compute,  # Clearer name
            "scrip": self.ledger.get_scrip(agent_id),
            "resources": self.ledger.get_all_resources(agent_id)  # New: all resources
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
            return validation_error(
                "transfer requires [from_id, to_id, amount]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["from_id", "to_id", "amount"],
            )

        from_id: str = args[0]
        to_id: str = args[1]
        amount: Any = args[2]

        # Security check: invoker can only transfer FROM themselves
        if from_id != invoker_id:
            return permission_error(
                f"Cannot transfer from {from_id} - you are {invoker_id}",
                code=ErrorCode.NOT_AUTHORIZED,
                invoker=invoker_id,
                target=from_id,
            )

        if not isinstance(amount, int) or amount <= 0:
            return validation_error(
                "Amount must be positive integer",
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

        # Create ledger entry with 0 scrip, 0 compute
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
                "transfer_ownership requires [artifact_id, to_id]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["artifact_id", "to_id"],
            )

        artifact_id: str = args[0]
        to_id: str = args[1]

        if not self.artifact_store:
            return resource_error(
                "Artifact store not configured",
                code=ErrorCode.NOT_FOUND,
            )

        # Get the artifact to verify ownership
        artifact = self.artifact_store.get(artifact_id)
        if not artifact:
            return resource_error(
                f"Artifact {artifact_id} not found",
                code=ErrorCode.NOT_FOUND,
                artifact_id=artifact_id,
            )

        # Security check: can only transfer artifacts you own
        if artifact.owner_id != invoker_id:
            return permission_error(
                f"Cannot transfer {artifact_id} - you are not the owner (owner is {artifact.owner_id})",
                code=ErrorCode.NOT_OWNER,
                artifact_id=artifact_id,
                owner=artifact.owner_id,
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
                "transfer_budget requires [to_id, amount]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["to_id", "amount"],
            )

        to_id: str = args[0]
        amount: Any = args[1]

        # Validate amount
        if not isinstance(amount, (int, float)) or amount <= 0:
            return validation_error(
                "Amount must be positive number",
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
                "get_budget requires [agent_id]",
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


class BidInfo(TypedDict):
    """Information about a bid in the mint auction."""
    agent_id: str
    artifact_id: str
    amount: int
    tick_submitted: int


class AuctionResult(TypedDict):
    """Result of an auction resolution."""
    winner_id: str | None
    artifact_id: str | None
    winning_bid: int
    price_paid: int  # Second-price
    score: int | None
    scrip_minted: int
    ubi_distributed: dict[str, int]
    error: str | None


class GenesisMint(GenesisArtifact):
    """
    Genesis artifact for auction-based external minting.

    Implements periodic auctions where agents bid scrip to submit artifacts
    for LLM scoring. Winning bid is redistributed as UBI to all agents.

    Auction phases:
    - WAITING: Before first_auction_tick
    - BIDDING: Accepting bids (bidding_window ticks)
    - After bidding window: Resolve auction, score artifact, distribute UBI

    All configuration is in config.yaml under genesis.mint.auction.

    Plan #44: GenesisMint now delegates to kernel primitives for bid storage
    and auction resolution. Timing (phases, windows) stays here as policy.
    """

    # World reference for kernel delegation (Plan #44)
    _world: Any

    # Legacy callbacks (deprecated - use kernel primitives)
    mint_callback: Callable[[str, int], None] | None
    ubi_callback: Callable[[int, str | None], dict[str, int]] | None
    artifact_store: ArtifactStore | None
    ledger: Any  # Ledger reference for bid escrow

    # Auction timing state (policy - stays in GenesisMint)
    _current_tick: int
    _auction_start_tick: int | None
    _auction_history: list[AuctionResult]  # Local history for status display

    # Legacy bid state (deprecated - kernel stores bids now)
    _bids: dict[str, BidInfo]  # agent_id -> bid info
    _held_bids: dict[str, int]  # agent_id -> held amount (escrow)

    # Track submission IDs for bid updates (Plan #44)
    _submission_ids: dict[str, str]  # agent_id -> kernel submission_id

    # Config
    _mint_ratio: int
    _period: int
    _bidding_window: int
    _first_auction_tick: int
    _slots_per_auction: int
    _minimum_bid: int
    _tie_breaking: str
    _show_bid_count: bool
    _allow_bid_updates: bool
    _refund_on_scoring_failure: bool

    _scorer: Any  # MintScorer, lazy-loaded

    def __init__(
        self,
        mint_callback: Callable[[str, int], None] | None = None,
        ubi_callback: Callable[[int, str | None], dict[str, int]] | None = None,
        artifact_store: ArtifactStore | None = None,
        ledger: Any = None,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        """
        Args:
            mint_callback: DEPRECATED - kernel handles minting now
            ubi_callback: DEPRECATED - kernel handles UBI now
            artifact_store: ArtifactStore to look up submitted artifacts
            ledger: Ledger for bid escrow
            genesis_config: Optional genesis config (uses global if not provided)
        """
        import random
        self._random = random

        # Get config
        cfg = genesis_config or get_validated_config().genesis
        mint_cfg = cfg.mint

        super().__init__(
            artifact_id=mint_cfg.id,
            description=mint_cfg.description
        )

        # World reference set via set_world() after creation (Plan #44)
        self._world = None

        # Legacy callbacks (deprecated)
        self.mint_callback = mint_callback
        self.ubi_callback = ubi_callback
        self.artifact_store = artifact_store
        self.ledger = ledger

        # Auction timing state
        self._current_tick = 0
        self._auction_start_tick = None
        self._auction_history = []

        # Legacy bid state (for backward compat during transition)
        self._bids = {}
        self._held_bids = {}

        # Kernel submission tracking (Plan #44)
        self._submission_ids = {}

        # Config
        self._mint_ratio = mint_cfg.mint_ratio
        self._period = mint_cfg.auction.period
        self._bidding_window = mint_cfg.auction.bidding_window
        self._first_auction_tick = mint_cfg.auction.first_auction_tick
        self._slots_per_auction = mint_cfg.auction.slots_per_auction
        self._minimum_bid = mint_cfg.auction.minimum_bid
        self._tie_breaking = mint_cfg.auction.tie_breaking
        self._show_bid_count = mint_cfg.auction.show_bid_count
        self._allow_bid_updates = mint_cfg.auction.allow_bid_updates
        self._refund_on_scoring_failure = mint_cfg.auction.refund_on_scoring_failure

        self._scorer = None

        # Register methods
        self.register_method(
            name="status",
            handler=self._status,
            cost=mint_cfg.methods.status.cost,
            description=mint_cfg.methods.status.description
        )

        self.register_method(
            name="bid",
            handler=self._bid,
            cost=mint_cfg.methods.bid.cost,
            description=mint_cfg.methods.bid.description
        )

        self.register_method(
            name="check",
            handler=self._check,
            cost=mint_cfg.methods.check.cost,
            description=mint_cfg.methods.check.description
        )

    def set_world(self, world: Any) -> None:
        """Set world reference for kernel delegation (Plan #44).

        Called by World after genesis artifact creation to enable
        kernel primitive access without circular imports.
        """
        self._world = world

    def _get_phase(self) -> str:
        """Get current auction phase."""
        if self._current_tick < self._first_auction_tick:
            return "WAITING"
        if self._auction_start_tick is None:
            return "WAITING"
        ticks_since_start = self._current_tick - self._auction_start_tick
        # Negative means we're waiting for next auction (start tick is in future)
        if ticks_since_start < 0:
            return "CLOSED"
        if ticks_since_start < self._bidding_window:
            return "BIDDING"
        return "CLOSED"

    def _status(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Return auction status."""
        phase = self._get_phase()
        result: dict[str, Any] = {
            "success": True,
            "mint": "genesis_mint",
            "type": "auction",
            "phase": phase,
            "current_tick": self._current_tick,
            "period": self._period,
            "bidding_window": self._bidding_window,
            "first_auction_tick": self._first_auction_tick,
            "minimum_bid": self._minimum_bid,
            "slots_per_auction": self._slots_per_auction,
            "auctions_completed": len(self._auction_history),
        }

        if phase == "WAITING":
            result["next_auction_tick"] = self._first_auction_tick
        elif phase == "BIDDING":
            result["auction_start_tick"] = self._auction_start_tick
            result["bidding_ends_tick"] = (self._auction_start_tick or 0) + self._bidding_window
            if self._show_bid_count:
                result["bid_count"] = len(self._bids)
            # Show agent's own bid if they have one
            if invoker_id in self._bids:
                result["your_bid"] = {
                    "artifact_id": self._bids[invoker_id]["artifact_id"],
                    "amount": self._bids[invoker_id]["amount"],
                }
        elif phase == "CLOSED":
            result["next_auction_tick"] = (self._auction_start_tick or 0) + self._period

        if self._auction_history:
            last = self._auction_history[-1]
            result["last_auction"] = {
                "winner": last["winner_id"],
                "artifact": last["artifact_id"],
                "price_paid": last["price_paid"],
                "score": last["score"],
                "scrip_minted": last["scrip_minted"],
            }

        return result

    def _bid(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Submit a sealed bid during bidding window.

        Plan #44: Now delegates to kernel primitives for bid storage.
        Timing (phases) stays here as policy.
        """
        if len(args) < 2:
            return {"success": False, "error": "bid requires [artifact_id, amount]"}

        artifact_id: str = str(args[0])
        try:
            amount: int = int(args[1])
        except (TypeError, ValueError):
            return {"success": False, "error": "bid amount must be an integer"}

        # Plan #5: Accept bids anytime (no phase check)
        # Bids apply to the next auction resolution

        # Validate amount (policy)
        if amount < self._minimum_bid:
            return {"success": False, "error": f"Bid must be at least {self._minimum_bid} scrip"}

        # Check if bid update is allowed (policy)
        has_existing_bid = invoker_id in self._submission_ids
        if has_existing_bid and not self._allow_bid_updates:
            return {"success": False, "error": "Bid updates not allowed. You already have a bid."}

        # Use kernel primitives if world is set (Plan #44)
        if self._world is not None:
            # If updating, cancel old submission first
            if has_existing_bid:
                old_submission_id = self._submission_ids[invoker_id]
                self._world.cancel_mint_submission(invoker_id, old_submission_id)
                del self._submission_ids[invoker_id]

            # Submit via kernel
            try:
                submission_id = self._world.submit_for_mint(
                    principal_id=invoker_id,
                    artifact_id=artifact_id,
                    bid=amount
                )
                self._submission_ids[invoker_id] = submission_id

                # Keep local _bids for backward compat with _check() and _status()
                self._bids[invoker_id] = {
                    "agent_id": invoker_id,
                    "artifact_id": artifact_id,
                    "amount": amount,
                    "tick_submitted": self._current_tick,
                }

                return {
                    "success": True,
                    "message": f"Bid of {amount} scrip recorded for {artifact_id}",
                    "artifact_id": artifact_id,
                    "amount": amount,
                    "submission_id": submission_id,
                }
            except ValueError as e:
                return {"success": False, "error": str(e)}

        # Legacy path (no world reference - deprecated)
        # Check if artifact exists and is executable
        if self.artifact_store:
            artifact = self.artifact_store.get(artifact_id)
            if not artifact:
                return {"success": False, "error": f"Artifact {artifact_id} not found"}
            if not artifact.executable:
                return {
                    "success": False,
                    "error": f"Mint only accepts executable artifacts. '{artifact_id}' is not executable."
                }

        # Check if agent can afford the bid
        if self.ledger:
            current_held = self._held_bids.get(invoker_id, 0)
            additional_needed = amount - current_held
            if additional_needed > 0:
                available = self.ledger.get_scrip(invoker_id)
                if available < additional_needed:
                    return {
                        "success": False,
                        "error": f"Insufficient scrip. Need {additional_needed} more (have {available})"
                    }
                # Hold the additional amount
                self.ledger.deduct_scrip(invoker_id, additional_needed)
                self._held_bids[invoker_id] = amount
            elif additional_needed < 0:
                # Refund the difference if lowering bid
                refund = -additional_needed
                self.ledger.credit_scrip(invoker_id, refund)
                self._held_bids[invoker_id] = amount

        # Record bid (legacy)
        self._bids[invoker_id] = {
            "agent_id": invoker_id,
            "artifact_id": artifact_id,
            "amount": amount,
            "tick_submitted": self._current_tick,
        }

        return {
            "success": True,
            "message": f"Bid of {amount} scrip recorded for {artifact_id}",
            "artifact_id": artifact_id,
            "amount": amount,
        }

    def _check(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check bid or auction result status."""
        # If agent has active bid, show it
        if invoker_id in self._bids:
            bid = self._bids[invoker_id]
            return {
                "success": True,
                "has_active_bid": True,
                "bid": {
                    "artifact_id": bid["artifact_id"],
                    "amount": bid["amount"],
                    "tick_submitted": bid["tick_submitted"],
                },
                "phase": self._get_phase(),
            }

        # Check if agent won any recent auctions
        won_auctions = [
            a for a in self._auction_history
            if a["winner_id"] == invoker_id
        ]
        if won_auctions:
            return {
                "success": True,
                "has_active_bid": False,
                "auctions_won": len(won_auctions),
                "last_win": won_auctions[-1],
            }

        return {
            "success": True,
            "has_active_bid": False,
            "message": "No active bid and no auction wins",
        }

    @property
    def submissions(self) -> dict[str, dict[str, Any]]:
        """Expose current bids and recent results for world state summary.

        Returns dict mapping artifact_id -> submission info with:
        - status: "pending" (active bid) or "scored" (from last auction)
        - submitter: agent who submitted
        - score: score if scored, None otherwise
        """
        result: dict[str, dict[str, Any]] = {}

        # Active bids show as "pending"
        for agent_id, bid in self._bids.items():
            result[bid["artifact_id"]] = {
                "status": "pending",
                "submitter": agent_id,
                "score": None,
            }

        # Most recent auction result (if any and had a winner)
        if self._auction_history:
            last = self._auction_history[-1]
            if last["artifact_id"] and last["winner_id"]:
                result[last["artifact_id"]] = {
                    "status": "scored",
                    "submitter": last["winner_id"],
                    "score": last["score"],
                }

        return result

    def on_tick(self, tick: int) -> AuctionResult | None:
        """Called by simulation runner at each tick.

        Handles:
        - Starting bidding windows
        - Resolving auctions at end of bidding window

        Returns AuctionResult if an auction was resolved, None otherwise.
        """
        self._current_tick = tick

        # Check if we should start a new bidding window
        if self._auction_start_tick is None:
            if tick >= self._first_auction_tick:
                self._auction_start_tick = tick
                return None
        else:
            # Check if bidding window just ended
            ticks_since_start = tick - self._auction_start_tick
            if ticks_since_start == self._bidding_window:
                # Resolve the auction
                result = self._resolve_auction()
                # Start next auction period
                self._auction_start_tick = self._auction_start_tick + self._period
                return result

        return None

    def _resolve_auction(self) -> AuctionResult:
        """Resolve the current auction and distribute rewards.

        Plan #44: Now delegates to kernel for auction resolution.
        Kernel handles scoring, minting, and UBI distribution.
        """
        # Use kernel primitives if world is set (Plan #44)
        if self._world is not None:
            # Kernel already has the bids from _bid() calls
            kernel_result = self._world.resolve_mint_auction()

            # Convert kernel result to AuctionResult format
            result: AuctionResult = {
                "winner_id": kernel_result.get("winner_id"),
                "artifact_id": kernel_result.get("artifact_id"),
                "winning_bid": kernel_result.get("winning_bid", 0),
                "price_paid": kernel_result.get("price_paid", 0),
                "score": kernel_result.get("score"),
                "scrip_minted": kernel_result.get("scrip_minted", 0),
                "ubi_distributed": kernel_result.get("ubi_distributed", {}),
                "error": kernel_result.get("error"),
            }
            self._auction_history.append(result)

            # Clear local state
            self._bids.clear()
            self._submission_ids.clear()

            return result

        # Legacy path (no world reference - deprecated)
        if not self._bids:
            # No bids - auction passes
            empty_result: AuctionResult = {
                "winner_id": None,
                "artifact_id": None,
                "winning_bid": 0,
                "price_paid": 0,
                "score": None,
                "scrip_minted": 0,
                "ubi_distributed": {},
                "error": "No bids received",
            }
            self._auction_history.append(empty_result)
            return empty_result

        # Sort bids by amount (descending)
        sorted_bids = sorted(
            self._bids.values(),
            key=lambda b: b["amount"],
            reverse=True
        )

        # Handle ties
        top_amount = sorted_bids[0]["amount"]
        top_bidders = [b for b in sorted_bids if b["amount"] == top_amount]

        if len(top_bidders) > 1:
            if self._tie_breaking == "random":
                winner_bid = self._random.choice(top_bidders)
            else:  # first_bid
                winner_bid = min(top_bidders, key=lambda b: b["tick_submitted"])
        else:
            winner_bid = sorted_bids[0]

        # Determine second-price
        if len(sorted_bids) > 1:
            # Find highest bid that isn't the winner's
            second_price = self._minimum_bid
            for b in sorted_bids:
                if b["agent_id"] != winner_bid["agent_id"]:
                    second_price = b["amount"]
                    break
        else:
            second_price = self._minimum_bid

        winner_id = winner_bid["agent_id"]
        artifact_id = winner_bid["artifact_id"]
        winning_bid = winner_bid["amount"]

        # Refund losing bidders
        for agent_id, held in self._held_bids.items():
            if agent_id != winner_id and self.ledger:
                self.ledger.credit_scrip(agent_id, held)

        # Winner pays second price (refund difference)
        if self.ledger:
            refund = winning_bid - second_price
            if refund > 0:
                self.ledger.credit_scrip(winner_id, refund)

        # Clear held bids
        self._held_bids.clear()

        # Distribute UBI from the price paid (legacy - uses callback)
        ubi_distribution: dict[str, int] = {}
        if self.ubi_callback is not None:
            ubi_distribution = self.ubi_callback(second_price, None)

        # Score the artifact
        score: int | None = None
        scrip_minted = 0
        error: str | None = None

        if self.artifact_store:
            artifact = self.artifact_store.get(artifact_id)
            if artifact:
                # Lazy-load scorer
                if self._scorer is None:
                    from .mint_scorer import get_scorer
                    self._scorer = get_scorer()

                try:
                    score_result = self._scorer.score_artifact(
                        artifact_id=artifact_id,
                        artifact_type=artifact.type,
                        content=artifact.content
                    )
                    if score_result["success"]:
                        score = score_result["score"]
                        scrip_minted = score // self._mint_ratio
                        if scrip_minted > 0 and self.mint_callback is not None:
                            self.mint_callback(winner_id, scrip_minted)
                    else:
                        error = score_result.get("error", "Scoring failed")
                        if self._refund_on_scoring_failure and self.ledger:
                            self.ledger.credit_scrip(winner_id, second_price)
                except Exception as e:
                    error = f"Scoring error: {str(e)}"
                    if self._refund_on_scoring_failure and self.ledger:
                        self.ledger.credit_scrip(winner_id, second_price)
            else:
                error = f"Artifact {artifact_id} not found"

        result = AuctionResult(
            winner_id=winner_id,
            artifact_id=artifact_id,
            winning_bid=winning_bid,
            price_paid=second_price,
            score=score,
            scrip_minted=scrip_minted,
            ubi_distributed=ubi_distribution,
            error=error,
        )
        self._auction_history.append(result)

        # Clear bids for next auction
        self._bids.clear()

        return result

    def mock_score(self, artifact_id: str, score: int) -> bool:
        """Mock scoring - for testing without LLM."""
        # This is a simplified mock for backward compat in tests
        # In auction mode, scoring happens automatically during resolution
        return True


class GenesisRightsRegistry(GenesisArtifact):
    """
    Genesis artifact for managing resource rights (means of production).

    This is a thin wrapper around kernel quota primitives (Plan #42).
    Quotas are kernel state, not genesis artifact state.

    Supports generic resources defined in config. Common resources:
    - compute: LLM tokens per tick (renews each tick)
    - disk: Bytes of storage (fixed pool)

    See docs/RESOURCE_MODEL.md for full design rationale.
    All method costs and descriptions are configurable via config.yaml.
    """

    default_quotas: dict[str, float]
    artifact_store: ArtifactStore | None
    # Legacy storage - used as fallback when _world is not set
    _legacy_quotas: dict[str, dict[str, float]]
    # World reference for kernel delegation (Plan #42)
    _world: Any  # Type is World but avoiding circular import

    def __init__(
        self,
        default_quotas: dict[str, float] | None = None,
        artifact_store: ArtifactStore | None = None,
        genesis_config: GenesisConfig | None = None,
        # Backward compat kwargs
        default_compute: int = 0,
        default_disk: int = 0,
    ) -> None:
        """
        Args:
            default_quotas: Dict of {resource_name: default_amount} for all resources
            artifact_store: ArtifactStore to calculate actual disk usage
            genesis_config: Optional genesis config (uses global if not provided)
            default_compute: DEPRECATED - use default_quotas
            default_disk: DEPRECATED - use default_quotas
        """
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        rights_cfg = cfg.rights_registry

        super().__init__(
            artifact_id=rights_cfg.id,
            description=rights_cfg.description
        )

        # Build default quotas from explicit dict or backward compat params
        if default_quotas:
            self.default_quotas = dict(default_quotas)
        else:
            # Backward compat: build from positional args
            self.default_quotas = {}
            if default_compute > 0:
                self.default_quotas["compute"] = float(default_compute)
            if default_disk > 0:
                self.default_quotas["disk"] = float(default_disk)

        self.artifact_store = artifact_store

        # Legacy quota storage - used when _world not set (backward compat)
        self._legacy_quotas = {}

        # World reference for kernel delegation - set via set_world()
        self._world = None

        # Register methods with costs/descriptions from config
        self.register_method(
            name="check_quota",
            handler=self._check_quota,
            cost=rights_cfg.methods.check_quota.cost,
            description=rights_cfg.methods.check_quota.description
        )

        self.register_method(
            name="all_quotas",
            handler=self._all_quotas,
            cost=rights_cfg.methods.all_quotas.cost,
            description=rights_cfg.methods.all_quotas.description
        )

        self.register_method(
            name="transfer_quota",
            handler=self._transfer_quota,
            cost=rights_cfg.methods.transfer_quota.cost,
            description=rights_cfg.methods.transfer_quota.description
        )

    def set_world(self, world: Any) -> None:
        """Set world reference for kernel delegation (Plan #42).

        Once set, all quota operations delegate to kernel state.

        Args:
            world: The World instance containing kernel quota primitives
        """
        self._world = world
        # Migrate any legacy quotas to kernel
        for agent_id, quotas in self._legacy_quotas.items():
            for resource, amount in quotas.items():
                self._world.set_quota(agent_id, resource, amount)
        self._legacy_quotas.clear()

    @property
    def quotas(self) -> dict[str, dict[str, float]]:
        """Backward compat: return quotas dict (read-only view).

        When _world is set, this reconstructs from kernel state.
        """
        if self._world is not None:
            # Reconstruct from kernel state
            result: dict[str, dict[str, float]] = {}
            for pid in self._world.principal_ids:
                result[pid] = {}
                for resource in self.default_quotas.keys():
                    result[pid][resource] = self._world.get_quota(pid, resource)
            return result
        return self._legacy_quotas

    def ensure_agent(self, agent_id: str) -> None:
        """Ensure an agent has quota entries (initialize with defaults)."""
        if self._world is not None:
            # Kernel mode: set default quotas if not already set
            for resource, amount in self.default_quotas.items():
                if self._world.get_quota(agent_id, resource) == 0.0:
                    self._world.set_quota(agent_id, resource, amount)
        else:
            # Legacy mode
            if agent_id not in self._legacy_quotas:
                self._legacy_quotas[agent_id] = dict(self.default_quotas)

    def get_quota(self, agent_id: str, resource: str) -> float:
        """Get quota for a specific resource.

        Delegates to kernel when world is set (Plan #42).
        """
        if self._world is not None:
            # Kernel mode: ensure defaults then query
            if self._world.get_quota(agent_id, resource) == 0.0:
                self.ensure_agent(agent_id)
            return cast(float, self._world.get_quota(agent_id, resource))
        # Legacy mode
        self.ensure_agent(agent_id)
        return self._legacy_quotas[agent_id].get(resource, 0.0)

    def set_quota(self, agent_id: str, resource: str, amount: float) -> None:
        """Set quota for a specific resource.

        Delegates to kernel when world is set (Plan #42).
        """
        if self._world is not None:
            self._world.set_quota(agent_id, resource, amount)
        else:
            self.ensure_agent(agent_id)
            self._legacy_quotas[agent_id][resource] = amount

    def get_all_quotas(self, agent_id: str) -> dict[str, float]:
        """Get all quotas for an agent.

        Delegates to kernel when world is set (Plan #42).
        """
        if self._world is not None:
            self.ensure_agent(agent_id)
            result = {}
            for resource in self.default_quotas.keys():
                result[resource] = self._world.get_quota(agent_id, resource)
            return result
        # Legacy mode
        self.ensure_agent(agent_id)
        return dict(self._legacy_quotas[agent_id])

    # Backward compat: compute = "compute" resource
    def get_compute_quota(self, agent_id: str) -> int:
        """Get compute quota (tokens/tick) for an agent."""
        return int(self.get_quota(agent_id, "compute"))

    # Backward compat: disk = "disk" resource
    def get_disk_quota(self, agent_id: str) -> int:
        """Get disk quota (bytes) for an agent."""
        return int(self.get_quota(agent_id, "disk"))

    def get_disk_used(self, agent_id: str) -> int:
        """Get actual disk space used by an agent."""
        if self.artifact_store:
            return self.artifact_store.get_owner_usage(agent_id)
        return 0

    def can_write(self, agent_id: str, additional_bytes: int) -> bool:
        """Check if agent can write additional_bytes without exceeding disk quota."""
        quota = self.get_disk_quota(agent_id)
        used = self.get_disk_used(agent_id)
        return (used + additional_bytes) <= quota

    # Backward compat aliases
    def get_flow_quota(self, agent_id: str) -> int:
        """DEPRECATED: Use get_compute_quota()."""
        return self.get_compute_quota(agent_id)

    def get_stock_quota(self, agent_id: str) -> int:
        """DEPRECATED: Use get_disk_quota()."""
        return self.get_disk_quota(agent_id)

    def get_stock_used(self, agent_id: str) -> int:
        """DEPRECATED: Use get_disk_used()."""
        return self.get_disk_used(agent_id)

    def _check_quota(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check quotas for an agent."""
        if not args or len(args) < 1:
            return {"success": False, "error": "check_quota requires [agent_id]"}

        agent_id: str = args[0]
        self.ensure_agent(agent_id)

        all_quotas = self.quotas[agent_id]
        disk_used = self.get_disk_used(agent_id)
        disk_quota = int(all_quotas.get("disk", 0))

        # Include both legacy format and new generic format
        return {
            "success": True,
            "agent_id": agent_id,
            "compute_quota": int(all_quotas.get("compute", 0)),
            "disk_quota": disk_quota,
            "disk_used": disk_used,
            "disk_available": disk_quota - disk_used,
            "quotas": all_quotas  # New: all resource quotas
        }

    def _all_quotas(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get all agent quotas."""
        result: dict[str, Any] = {}
        for agent_id, quota in self.quotas.items():
            disk_used = self.get_disk_used(agent_id)
            disk_quota = int(quota.get("disk", 0))
            result[agent_id] = {
                "compute_quota": int(quota.get("compute", 0)),
                "disk_quota": disk_quota,
                "disk_used": disk_used,
                "disk_available": disk_quota - disk_used,
                "quotas": quota  # New: all resource quotas
            }
        return {"success": True, "quotas": result}

    def _transfer_quota(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer quota between agents. Works with any resource type.

        Delegates to kernel when world is set (Plan #42).
        """
        if not args or len(args) < 4:
            return {"success": False, "error": "transfer_quota requires [from_id, to_id, resource, amount]"}

        from_id: str = args[0]
        to_id: str = args[1]
        resource: str = args[2]
        amount: Any = args[3]

        # Security check: can only transfer FROM yourself
        if from_id != invoker_id:
            return {"success": False, "error": f"Cannot transfer from {from_id} - you are {invoker_id}"}

        # Validate resource exists in defaults (to prevent typos)
        if resource not in self.default_quotas:
            valid_resources = list(self.default_quotas.keys())
            return {"success": False, "error": f"Unknown resource '{resource}'. Valid: {valid_resources}"}

        if not isinstance(amount, (int, float)) or amount <= 0:
            return {"success": False, "error": "amount must be positive number"}

        self.ensure_agent(from_id)
        self.ensure_agent(to_id)

        # Kernel delegation mode (Plan #42)
        if self._world is not None:
            from src.world.kernel_interface import KernelActions
            kernel_actions = KernelActions(self._world)
            success = kernel_actions.transfer_quota(from_id, to_id, resource, float(amount))

            if not success:
                current = self._world.get_quota(from_id, resource)
                return {
                    "success": False,
                    "error": f"Insufficient {resource} quota. Have {current}, need {amount}"
                }

            return {
                "success": True,
                "transferred": amount,
                "quota_type": resource,  # Keep legacy field name
                "resource": resource,    # New field name
                "from": from_id,
                "to": to_id,
                "from_new_quota": self._world.get_quota(from_id, resource),
                "to_new_quota": self._world.get_quota(to_id, resource)
            }

        # Legacy mode
        current = self._legacy_quotas[from_id].get(resource, 0.0)
        if current < amount:
            return {
                "success": False,
                "error": f"Insufficient {resource} quota. Have {current}, need {amount}"
            }

        # Transfer
        self._legacy_quotas[from_id][resource] = current - amount
        self._legacy_quotas[to_id][resource] = self._legacy_quotas[to_id].get(resource, 0.0) + amount

        return {
            "success": True,
            "transferred": amount,
            "quota_type": resource,  # Keep legacy field name
            "resource": resource,    # New field name
            "from": from_id,
            "to": to_id,
            "from_new_quota": self._legacy_quotas[from_id][resource],
            "to_new_quota": self._legacy_quotas[to_id][resource]
        }


class GenesisEventLog(GenesisArtifact):
    """
    Genesis artifact for passive observability.

    This is the only way agents can learn about world events.
    Nothing is injected into prompts - agents must actively read.
    Reading is FREE in scrip, but costs real input tokens.

    All method costs and descriptions are configurable via config.yaml.
    """

    logger: EventLogger
    _max_per_read: int
    _buffer_size: int

    def __init__(self, logger: EventLogger, genesis_config: GenesisConfig | None = None) -> None:
        """
        Args:
            logger: The world's EventLogger instance
            genesis_config: Optional genesis config (uses global if not provided)
        """
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        event_log_cfg = cfg.event_log

        super().__init__(
            artifact_id=event_log_cfg.id,
            description=event_log_cfg.description
        )
        self.logger = logger
        self._max_per_read = event_log_cfg.max_per_read
        self._buffer_size = event_log_cfg.buffer_size

        # Register methods with costs/descriptions from config
        self.register_method(
            name="read",
            handler=self._read,
            cost=event_log_cfg.methods.read.cost,
            description=event_log_cfg.methods.read.description
        )

    def _read(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Read events from the log.

        Args format: [offset, limit]
        - offset: skip this many events from the end (default 0)
        - limit: return at most this many events (default from config)
        """
        offset = 0
        default_limit: int = get("logging.default_recent") or 50
        limit = default_limit

        if args and len(args) >= 1 and isinstance(args[0], int):
            offset = args[0]
        if args and len(args) >= 2 and isinstance(args[1], int):
            limit = min(args[1], self._max_per_read)  # Cap to prevent abuse

        # Get all recent events then slice
        all_events = self.logger.read_recent(self._buffer_size)

        if offset > 0:
            # Slice from offset
            end_idx = len(all_events) - offset
            start_idx = max(0, end_idx - limit)
            events = all_events[start_idx:end_idx]
        else:
            # Just the most recent
            events = all_events[-limit:] if len(all_events) > limit else all_events

        return {
            "success": True,
            "events": events,
            "count": len(events),
            "total_available": len(all_events),
            "warning": "Reading events costs input tokens when you next think. Be strategic about what you read."
        }


class EscrowListing(TypedDict):
    """An active escrow listing."""
    artifact_id: str
    seller_id: str
    price: int
    buyer_id: str | None  # If set, only this buyer can purchase
    status: str  # "active", "completed", "cancelled"


class EscrowDepositResult(TypedDict, total=False):
    """Result from escrow deposit."""
    success: bool
    error: str
    artifact_id: str
    price: int
    seller: str


class EscrowPurchaseResult(TypedDict, total=False):
    """Result from escrow purchase."""
    success: bool
    error: str
    artifact_id: str
    price: int
    seller: str
    buyer: str


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


# =============================================================================
# GENESIS DEBT CONTRACT - Non-privileged lending example
# =============================================================================

class DebtRecord(TypedDict):
    """Record of a debt."""
    debt_id: str
    debtor_id: str
    creditor_id: str
    principal: int
    interest_rate: float
    due_tick: int
    amount_owed: int  # Principal + accrued interest
    amount_paid: int
    status: str  # "pending", "active", "paid", "defaulted"
    created_tick: int


class DebtIssueResult(TypedDict, total=False):
    """Result from debt issue operation."""
    success: bool
    error: str
    debt_id: str
    debtor: str
    creditor: str
    principal: int
    due_tick: int


class DebtCheckResult(TypedDict, total=False):
    """Result from debt check operation."""
    success: bool
    error: str
    debt: DebtRecord


class GenesisDebtContract(GenesisArtifact):
    """
    Genesis artifact for debt/lending contracts.

    This is a NON-PRIVILEGED example contract showing how to implement
    credit/lending. Agents can build their own competing debt contracts.

    Key insight: No magic enforcement. Bad debtors get bad reputation
    via the event log, not kernel-level punishment.

    Flow:
    1. Debtor calls issue(creditor, principal, interest_rate, due_tick)
    2. Creditor calls accept(debt_id) - debt becomes active
    3. Debtor calls repay(debt_id, amount) to pay back
    4. After due_tick, creditor can call collect(debt_id) to attempt collection
    5. Creditor can call transfer_creditor(debt_id, new_creditor) to sell debt
    """

    ledger: Ledger
    debts: dict[str, DebtRecord]
    current_tick: int

    def __init__(
        self,
        ledger: Ledger,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        """
        Args:
            ledger: The world's Ledger instance (for scrip transfers)
            genesis_config: Optional genesis config (uses global if not provided)
        """
        cfg = genesis_config or get_validated_config().genesis
        debt_cfg = cfg.debt_contract

        super().__init__(
            artifact_id=debt_cfg.id,
            description=debt_cfg.description
        )
        self.ledger = ledger
        self.debts = {}
        self.current_tick = 0

        # Register methods with costs/descriptions from config
        self.register_method(
            name="issue",
            handler=self._issue,
            cost=debt_cfg.methods.issue.cost,
            description=debt_cfg.methods.issue.description
        )
        self.register_method(
            name="accept",
            handler=self._accept,
            cost=debt_cfg.methods.accept.cost,
            description=debt_cfg.methods.accept.description
        )
        self.register_method(
            name="repay",
            handler=self._repay,
            cost=debt_cfg.methods.repay.cost,
            description=debt_cfg.methods.repay.description
        )
        self.register_method(
            name="collect",
            handler=self._collect,
            cost=debt_cfg.methods.collect.cost,
            description=debt_cfg.methods.collect.description
        )
        self.register_method(
            name="transfer_creditor",
            handler=self._transfer_creditor,
            cost=debt_cfg.methods.transfer_creditor.cost,
            description=debt_cfg.methods.transfer_creditor.description
        )
        self.register_method(
            name="check",
            handler=self._check,
            cost=debt_cfg.methods.check.cost,
            description=debt_cfg.methods.check.description
        )
        self.register_method(
            name="list_debts",
            handler=self._list_debts,
            cost=debt_cfg.methods.list_debts.cost,
            description=debt_cfg.methods.list_debts.description
        )
        self.register_method(
            name="list_all",
            handler=self._list_all,
            cost=debt_cfg.methods.list_all.cost,
            description=debt_cfg.methods.list_all.description
        )

    def set_tick(self, tick: int) -> None:
        """Update the current tick (called by World)."""
        self.current_tick = tick

    def _issue(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Issue a debt. Invoker becomes debtor.

        Args: [creditor_id, principal, interest_rate, due_tick]
        - creditor_id: Who will be owed the money
        - principal: Amount borrowed
        - interest_rate: Per-tick interest (e.g., 0.01 = 1% per tick)
        - due_tick: When the debt is due
        """
        if len(args) < 4:
            return {"success": False, "error": "issue requires [creditor_id, principal, interest_rate, due_tick]"}

        creditor_id: str = args[0]
        principal: Any = args[1]
        interest_rate: Any = args[2]
        due_tick: Any = args[3]

        # Validate inputs
        if not isinstance(principal, int) or principal <= 0:
            return {"success": False, "error": "Principal must be a positive integer"}
        if not isinstance(interest_rate, (int, float)) or interest_rate < 0:
            return {"success": False, "error": "Interest rate must be non-negative"}
        if not isinstance(due_tick, int) or due_tick <= self.current_tick:
            return {"success": False, "error": f"Due tick must be greater than current tick ({self.current_tick})"}

        # Cannot issue debt to yourself
        if creditor_id == invoker_id:
            return {"success": False, "error": "Cannot issue debt to yourself"}

        # Create debt record (pending until creditor accepts)
        debt_id = f"debt_{uuid.uuid4().hex[:8]}"
        self.debts[debt_id] = {
            "debt_id": debt_id,
            "debtor_id": invoker_id,
            "creditor_id": creditor_id,
            "principal": principal,
            "interest_rate": float(interest_rate),
            "due_tick": due_tick,
            "amount_owed": principal,  # Will accrue interest when active
            "amount_paid": 0,
            "status": "pending",
            "created_tick": self.current_tick
        }

        return {
            "success": True,
            "debt_id": debt_id,
            "debtor": invoker_id,
            "creditor": creditor_id,
            "principal": principal,
            "interest_rate": interest_rate,
            "due_tick": due_tick,
            "message": f"Debt {debt_id} issued. Creditor {creditor_id} must call accept to activate."
        }

    def _accept(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Accept a pending debt (creditor must call).

        Args: [debt_id]
        """
        if len(args) < 1:
            return {"success": False, "error": "accept requires [debt_id]"}

        debt_id: str = args[0]

        if debt_id not in self.debts:
            return {"success": False, "error": f"Debt {debt_id} not found"}

        debt = self.debts[debt_id]

        # Only creditor can accept
        if debt["creditor_id"] != invoker_id:
            return {"success": False, "error": "Only the creditor can accept a debt"}

        # Must be pending
        if debt["status"] != "pending":
            return {"success": False, "error": f"Debt is not pending (status: {debt['status']})"}

        # Activate the debt
        debt["status"] = "active"

        return {
            "success": True,
            "debt_id": debt_id,
            "debtor": debt["debtor_id"],
            "creditor": invoker_id,
            "principal": debt["principal"],
            "message": f"Debt {debt_id} is now active. Debtor owes {debt['principal']} scrip."
        }

    def _repay(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Repay debt (debtor pays creditor).

        Args: [debt_id, amount]
        """
        if len(args) < 2:
            return {"success": False, "error": "repay requires [debt_id, amount]"}

        debt_id: str = args[0]
        amount: Any = args[1]

        if not isinstance(amount, int) or amount <= 0:
            return {"success": False, "error": "Amount must be a positive integer"}

        if debt_id not in self.debts:
            return {"success": False, "error": f"Debt {debt_id} not found"}

        debt = self.debts[debt_id]

        # Only debtor can repay
        if debt["debtor_id"] != invoker_id:
            return {"success": False, "error": "Only the debtor can repay"}

        # Must be active
        if debt["status"] != "active":
            return {"success": False, "error": f"Debt is not active (status: {debt['status']})"}

        # Calculate current amount owed with interest
        ticks_elapsed = max(0, self.current_tick - debt["created_tick"])
        interest = int(debt["principal"] * debt["interest_rate"] * ticks_elapsed)
        current_owed = debt["principal"] + interest - debt["amount_paid"]

        # Cap payment at amount owed
        actual_payment = min(amount, current_owed)

        # Transfer scrip from debtor to creditor
        transfer_success = self.ledger.transfer_scrip(
            invoker_id,
            debt["creditor_id"],
            actual_payment
        )
        if not transfer_success:
            return {"success": False, "error": "Transfer failed: insufficient funds"}

        # Update debt record
        debt["amount_paid"] += actual_payment
        debt["amount_owed"] = current_owed - actual_payment

        # Check if fully paid
        if debt["amount_owed"] <= 0:
            debt["status"] = "paid"
            return {
                "success": True,
                "debt_id": debt_id,
                "amount_paid": actual_payment,
                "total_paid": debt["amount_paid"],
                "remaining": 0,
                "status": "paid",
                "message": f"Debt {debt_id} fully paid!"
            }

        return {
            "success": True,
            "debt_id": debt_id,
            "amount_paid": actual_payment,
            "total_paid": debt["amount_paid"],
            "remaining": debt["amount_owed"],
            "message": f"Paid {actual_payment} scrip. {debt['amount_owed']} remaining."
        }

    def _collect(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Collect overdue debt (creditor only, after due_tick).

        This attempts to collect. No magic enforcement - if debtor has no
        scrip, collection fails but debt is marked defaulted for reputation.

        Args: [debt_id]
        """
        if len(args) < 1:
            return {"success": False, "error": "collect requires [debt_id]"}

        debt_id: str = args[0]

        if debt_id not in self.debts:
            return {"success": False, "error": f"Debt {debt_id} not found"}

        debt = self.debts[debt_id]

        # Only creditor can collect
        if debt["creditor_id"] != invoker_id:
            return {"success": False, "error": "Only the creditor can collect"}

        # Must be active
        if debt["status"] != "active":
            return {"success": False, "error": f"Debt is not active (status: {debt['status']})"}

        # Must be past due
        if self.current_tick < debt["due_tick"]:
            return {
                "success": False,
                "error": f"Debt not yet due (due at tick {debt['due_tick']}, current tick {self.current_tick})"
            }

        # Calculate amount owed
        ticks_elapsed = max(0, self.current_tick - debt["created_tick"])
        interest = int(debt["principal"] * debt["interest_rate"] * ticks_elapsed)
        amount_owed = debt["principal"] + interest - debt["amount_paid"]

        # Try to collect
        debtor_balance = self.ledger.get_scrip(debt["debtor_id"])

        if debtor_balance >= amount_owed:
            # Full collection
            transfer_success = self.ledger.transfer_scrip(
                debt["debtor_id"],
                invoker_id,
                amount_owed
            )
            if transfer_success:
                debt["amount_paid"] += amount_owed
                debt["amount_owed"] = 0
                debt["status"] = "paid"
                return {
                    "success": True,
                    "debt_id": debt_id,
                    "collected": amount_owed,
                    "status": "paid",
                    "message": f"Collected {amount_owed} scrip. Debt fully paid."
                }

        elif debtor_balance > 0:
            # Partial collection
            transfer_success = self.ledger.transfer_scrip(
                debt["debtor_id"],
                invoker_id,
                debtor_balance
            )
            if transfer_success:
                debt["amount_paid"] += debtor_balance
                debt["amount_owed"] = amount_owed - debtor_balance
                return {
                    "success": True,
                    "debt_id": debt_id,
                    "collected": debtor_balance,
                    "remaining": debt["amount_owed"],
                    "status": "active",
                    "message": f"Partial collection: {debtor_balance} scrip. {debt['amount_owed']} still owed."
                }

        # Debtor has no scrip - mark as defaulted for reputation
        debt["status"] = "defaulted"
        return {
            "success": False,
            "debt_id": debt_id,
            "collected": 0,
            "remaining": amount_owed,
            "status": "defaulted",
            "error": f"Debtor {debt['debtor_id']} has no scrip. Debt marked as defaulted."
        }

    def _transfer_creditor(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer creditor rights to another principal (sell the debt).

        Args: [debt_id, new_creditor_id]
        """
        if len(args) < 2:
            return {"success": False, "error": "transfer_creditor requires [debt_id, new_creditor_id]"}

        debt_id: str = args[0]
        new_creditor_id: str = args[1]

        if debt_id not in self.debts:
            return {"success": False, "error": f"Debt {debt_id} not found"}

        debt = self.debts[debt_id]

        # Only current creditor can transfer
        if debt["creditor_id"] != invoker_id:
            return {"success": False, "error": "Only the creditor can transfer creditor rights"}

        # Cannot be paid or pending
        if debt["status"] not in ("active", "defaulted"):
            return {"success": False, "error": f"Cannot transfer debt with status: {debt['status']}"}

        old_creditor = debt["creditor_id"]
        debt["creditor_id"] = new_creditor_id

        return {
            "success": True,
            "debt_id": debt_id,
            "old_creditor": old_creditor,
            "new_creditor": new_creditor_id,
            "message": f"Creditor rights transferred from {old_creditor} to {new_creditor_id}"
        }

    def _check(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check status of a debt.

        Args: [debt_id]
        """
        if len(args) < 1:
            return {"success": False, "error": "check requires [debt_id]"}

        debt_id: str = args[0]

        if debt_id not in self.debts:
            return {"success": False, "error": f"Debt {debt_id} not found"}

        debt = self.debts[debt_id]

        # Calculate current amount owed
        if debt["status"] == "active":
            ticks_elapsed = max(0, self.current_tick - debt["created_tick"])
            interest = int(debt["principal"] * debt["interest_rate"] * ticks_elapsed)
            current_owed = debt["principal"] + interest - debt["amount_paid"]
        else:
            current_owed = debt["amount_owed"]

        return {
            "success": True,
            "debt": {
                **debt,
                "current_owed": current_owed,
                "current_tick": self.current_tick
            }
        }

    def _list_debts(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List debts for a principal.

        Args: [principal_id]
        """
        if len(args) < 1:
            return {"success": False, "error": "list_debts requires [principal_id]"}

        principal_id: str = args[0]

        # Find debts where principal is debtor or creditor
        debts = [
            debt for debt in self.debts.values()
            if debt["debtor_id"] == principal_id or debt["creditor_id"] == principal_id
        ]

        return {
            "success": True,
            "principal_id": principal_id,
            "debts": debts,
            "count": len(debts)
        }

    def _list_all(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List all debts.

        Args: []
        """
        return {
            "success": True,
            "debts": list(self.debts.values()),
            "count": len(self.debts)
        }


class StoreListResult(TypedDict):
    """Result from store list operation."""
    success: bool
    artifacts: list[dict[str, Any]]
    count: int


class StoreGetResult(TypedDict, total=False):
    """Result from store get operation."""
    success: bool
    error: str
    artifact: dict[str, Any]


class StoreSearchResult(TypedDict):
    """Result from store search operation."""
    success: bool
    artifacts: list[dict[str, Any]]
    query: str


class StoreCountResult(TypedDict):
    """Result from store count operation."""
    success: bool
    count: int


class GenesisStore(GenesisArtifact):
    """
    Genesis artifact for artifact discovery and registry.

    Enables agents to programmatically discover artifacts without trial-and-error.
    All methods cost 0 (system-subsidized) to encourage market formation.

    Methods:
    - list: List artifacts with optional filter
    - get: Get single artifact details
    - search: Search by content match
    - list_by_type: List artifacts of specific type
    - list_by_owner: List artifacts by owner
    - list_agents: List all agent artifacts
    - list_principals: List all principals (has_standing=True)
    - count: Count artifacts matching filter

    All method costs and descriptions are configurable via config.yaml.
    """

    artifact_store: ArtifactStore

    def __init__(
        self,
        artifact_store: ArtifactStore,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        """
        Args:
            artifact_store: The world's ArtifactStore for artifact lookups
            genesis_config: Optional genesis config (uses global if not provided)
        """
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        store_cfg = cfg.store

        super().__init__(
            artifact_id=store_cfg.id,
            description=store_cfg.description
        )
        self.artifact_store = artifact_store

        # Register methods with costs/descriptions from config
        self.register_method(
            name="list",
            handler=self._list,
            cost=store_cfg.methods.list.cost,
            description=store_cfg.methods.list.description
        )

        self.register_method(
            name="get",
            handler=self._get,
            cost=store_cfg.methods.get.cost,
            description=store_cfg.methods.get.description
        )

        self.register_method(
            name="search",
            handler=self._search,
            cost=store_cfg.methods.search.cost,
            description=store_cfg.methods.search.description
        )

        self.register_method(
            name="list_by_type",
            handler=self._list_by_type,
            cost=store_cfg.methods.list_by_type.cost,
            description=store_cfg.methods.list_by_type.description
        )

        self.register_method(
            name="list_by_owner",
            handler=self._list_by_owner,
            cost=store_cfg.methods.list_by_owner.cost,
            description=store_cfg.methods.list_by_owner.description
        )

        self.register_method(
            name="list_agents",
            handler=self._list_agents,
            cost=store_cfg.methods.list_agents.cost,
            description=store_cfg.methods.list_agents.description
        )

        self.register_method(
            name="list_principals",
            handler=self._list_principals,
            cost=store_cfg.methods.list_principals.cost,
            description=store_cfg.methods.list_principals.description
        )

        self.register_method(
            name="count",
            handler=self._count,
            cost=store_cfg.methods.count.cost,
            description=store_cfg.methods.count.description
        )

    def _artifact_to_dict(self, artifact: Any) -> dict[str, Any]:
        """Convert an Artifact to a dict representation."""
        result: dict[str, Any] = {
            "id": artifact.id,
            "type": artifact.type,
            "owner_id": artifact.owner_id,
            "content": artifact.content,
            "has_standing": artifact.has_standing,
            "can_execute": artifact.can_execute,
            "executable": artifact.executable,
        }
        # Optional fields
        if hasattr(artifact, "memory_artifact_id") and artifact.memory_artifact_id:
            result["memory_artifact_id"] = artifact.memory_artifact_id
        return result

    def _apply_filter(
        self, artifacts: list[Any], filter_dict: dict[str, Any] | None
    ) -> list[Any]:
        """Apply filter criteria to artifact list."""
        if not filter_dict:
            return artifacts

        filtered = artifacts

        # Filter by type
        if "type" in filter_dict:
            filtered = [a for a in filtered if a.type == filter_dict["type"]]

        # Filter by owner
        if "owner" in filter_dict:
            filtered = [a for a in filtered if a.owner_id == filter_dict["owner"]]

        # Filter by has_standing
        if "has_standing" in filter_dict:
            filtered = [a for a in filtered if a.has_standing == filter_dict["has_standing"]]

        # Filter by can_execute
        if "can_execute" in filter_dict:
            filtered = [a for a in filtered if a.can_execute == filter_dict["can_execute"]]

        # Apply offset
        offset = filter_dict.get("offset", 0)
        if offset > 0:
            filtered = filtered[offset:]

        # Apply limit
        limit = filter_dict.get("limit")
        if limit is not None and limit > 0:
            filtered = filtered[:limit]

        return filtered

    def _get_all_artifacts(self) -> list[Any]:
        """Get all artifacts as Artifact objects (not dicts)."""
        return list(self.artifact_store.artifacts.values())

    def _list(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List artifacts with optional filter.

        Args: [filter?] where filter is a dict with optional keys:
        - type: filter by artifact type
        - owner: filter by owner_id
        - has_standing: filter by has_standing (True/False)
        - can_execute: filter by can_execute (True/False)
        - limit: max results to return
        - offset: skip first N results
        """
        filter_dict = args[0] if args and isinstance(args[0], dict) else None

        all_artifacts = self._get_all_artifacts()
        filtered = self._apply_filter(all_artifacts, filter_dict)

        return {
            "success": True,
            "artifacts": [self._artifact_to_dict(a) for a in filtered],
            "count": len(filtered),
        }

    def _get(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get single artifact details.

        Args: [artifact_id]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "get requires [artifact_id]"}

        artifact_id: str = str(args[0])
        artifact = self.artifact_store.get(artifact_id)

        if not artifact:
            return {"success": False, "error": f"Artifact '{artifact_id}' not found"}

        return {
            "success": True,
            "artifact": self._artifact_to_dict(artifact),
        }

    def _search(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Search artifacts by content match.

        Args: [query, field?, limit?]
        - query: string to search for
        - field: optional field to search in (default: all)
        - limit: optional max results
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "search requires [query]"}

        query: str = str(args[0]).lower()
        field: str | None = str(args[1]) if len(args) > 1 and args[1] else None
        limit: int | None = int(args[2]) if len(args) > 2 and args[2] else None

        all_artifacts = self._get_all_artifacts()
        matches: list[Any] = []

        for artifact in all_artifacts:
            # Search in content
            content = artifact.content
            matched = False

            if field:
                # Search in specific field
                if isinstance(content, dict) and field in content:
                    if query in str(content[field]).lower():
                        matched = True
            else:
                # Search in all content
                content_str = str(content).lower()
                if query in content_str:
                    matched = True

                # Also search in ID and type
                if query in artifact.id.lower() or query in artifact.type.lower():
                    matched = True

            if matched:
                matches.append(artifact)
                if limit and len(matches) >= limit:
                    break

        return {
            "success": True,
            "artifacts": [self._artifact_to_dict(a) for a in matches],
            "query": query,
        }

    def _list_by_type(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List artifacts of specific type.

        Args: [type]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "list_by_type requires [type]"}

        artifact_type: str = str(args[0])
        return self._list([{"type": artifact_type}], invoker_id)

    def _list_by_owner(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List artifacts by owner.

        Args: [owner_id]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "list_by_owner requires [owner_id]"}

        owner_id: str = str(args[0])
        return self._list([{"owner": owner_id}], invoker_id)

    def _list_agents(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List all agent artifacts.

        Agents are artifacts with has_standing=True AND can_execute=True.

        Args: []
        """
        return self._list([{"has_standing": True, "can_execute": True}], invoker_id)

    def _list_principals(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List all principals.

        Principals are artifacts with has_standing=True.
        This includes agents and contracts with standing.

        Args: []
        """
        return self._list([{"has_standing": True}], invoker_id)

    def _count(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Count artifacts matching filter.

        Args: [filter?] - same filter format as list
        """
        filter_dict = args[0] if args and isinstance(args[0], dict) else None

        all_artifacts = self._get_all_artifacts()

        # Don't apply limit/offset for count
        count_filter = dict(filter_dict) if filter_dict else {}
        count_filter.pop("limit", None)
        count_filter.pop("offset", None)

        filtered = self._apply_filter(all_artifacts, count_filter if count_filter else None)

        return {
            "success": True,
            "count": len(filtered),
        }


class RightsConfig(TypedDict, total=False):
    """Configuration for rights registry."""
    default_quotas: dict[str, float]  # Generic: {resource: amount}
    default_compute_quota: int  # Legacy
    default_disk_quota: int  # Legacy
    default_flow_quota: int  # Legacy
    default_stock_quota: int  # Legacy


def create_genesis_artifacts(
    ledger: Ledger,
    mint_callback: Callable[[str, int], None],
    artifact_store: ArtifactStore | None = None,
    logger: EventLogger | None = None,
    rights_config: RightsConfig | None = None,
    genesis_config: GenesisConfig | None = None
) -> dict[str, GenesisArtifact]:
    """
    Factory function to create all genesis artifacts.

    Which artifacts are created is controlled by genesis.artifacts config.
    All method costs and descriptions come from config.

    Args:
        ledger: The world's Ledger instance
        mint_callback: Function(agent_id, amount) to mint new scrip
        artifact_store: ArtifactStore for mint to look up artifacts
        logger: EventLogger for genesis_event_log
        rights_config: Dict with 'default_quotas' (preferred) or legacy keys
                       'default_compute_quota', 'default_disk_quota'
        genesis_config: Optional genesis config (uses global if not provided)

    Returns:
        Dict mapping artifact_id -> GenesisArtifact
    """
    # Get config (use provided or load from global)
    cfg = genesis_config or get_validated_config().genesis

    artifacts: dict[str, GenesisArtifact] = {}

    # Create ledger if enabled
    if cfg.artifacts.ledger.enabled:
        genesis_ledger = GenesisLedger(
            ledger,
            artifact_store=artifact_store,
            genesis_config=cfg
        )
        artifacts[genesis_ledger.id] = genesis_ledger

    # Create mint if enabled
    if cfg.artifacts.mint.enabled:
        # Create UBI callback using ledger
        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        genesis_mint = GenesisMint(
            mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=artifact_store,
            ledger=ledger,
            genesis_config=cfg
        )
        artifacts[genesis_mint.id] = genesis_mint

    # Add event log if enabled and logger provided
    if cfg.artifacts.event_log.enabled and logger:
        genesis_event_log = GenesisEventLog(logger, genesis_config=cfg)
        artifacts[genesis_event_log.id] = genesis_event_log

    # Add rights registry if enabled and config provided
    if cfg.artifacts.rights_registry.enabled and rights_config:
        # Check for new generic format first
        if "default_quotas" in rights_config:
            default_quotas = rights_config["default_quotas"]
        else:
            # Build from legacy keys with config fallback
            compute_fallback: int = get("resources.flow.compute.per_tick") or 50
            disk_fallback: int = get("resources.stock.disk.total") or 10000
            default_compute = rights_config.get("default_compute_quota",
                              rights_config.get("default_flow_quota", compute_fallback))
            default_disk = rights_config.get("default_disk_quota",
                           rights_config.get("default_stock_quota", disk_fallback))
            default_quotas = {
                "compute": float(default_compute),
                "disk": float(default_disk)
            }

        genesis_rights = GenesisRightsRegistry(
            default_quotas=default_quotas,
            artifact_store=artifact_store,
            genesis_config=cfg
        )
        artifacts[genesis_rights.id] = genesis_rights

    # Add escrow if enabled and artifact_store provided
    if cfg.artifacts.escrow.enabled and artifact_store:
        genesis_escrow = GenesisEscrow(
            ledger=ledger,
            artifact_store=artifact_store,
            genesis_config=cfg
        )
        artifacts[genesis_escrow.id] = genesis_escrow

    # Add store if enabled and artifact_store provided
    if cfg.artifacts.store.enabled and artifact_store:
        genesis_store = GenesisStore(
            artifact_store=artifact_store,
            genesis_config=cfg
        )
        artifacts[genesis_store.id] = genesis_store

    # Add debt contract if enabled
    if cfg.artifacts.debt_contract.enabled:
        genesis_debt = GenesisDebtContract(
            ledger=ledger,
            genesis_config=cfg
        )
        artifacts[genesis_debt.id] = genesis_debt

    # Add MCP artifacts if any are enabled
    from .mcp_bridge import create_mcp_artifacts
    mcp_artifacts = create_mcp_artifacts(cfg.mcp)
    for artifact_id, mcp_artifact in mcp_artifacts.items():
        artifacts[artifact_id] = mcp_artifact

    # Add aliases for new naming convention (Plan #44)
    # Maps old names -> new names (both can be used to access same artifact)
    # API wrappers: genesis_*_api - wrap kernel primitives
    # Contracts: genesis_*_contract - pure contract logic
    alias_mapping = {
        "genesis_ledger": "genesis_ledger_api",
        "genesis_mint": "genesis_mint_api",
        "genesis_rights_registry": "genesis_rights_api",
        "genesis_store": "genesis_store_api",
        "genesis_event_log": "genesis_event_log_api",
        "genesis_escrow": "genesis_escrow_contract",
    }
    for old_name, new_name in alias_mapping.items():
        if old_name in artifacts:
            artifacts[new_name] = artifacts[old_name]

    return artifacts
