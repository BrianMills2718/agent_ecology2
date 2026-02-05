"""Ledger for tracking resources and scrip (economic currency)

Two separate systems:
1. Resources - Generic resource tracking (llm_budget, disk, bandwidth, etc.)
   - Renewable resources: Rate-limited via RateTracker
   - Stock resources: Finite pool, never reset (e.g., disk)
2. Scrip - Economic currency. Persistent. Earned/spent through trade.

Resources are defined in config and can be extended without code changes.
Principals can be any string ID - agents OR artifacts.

Precision Strategy (Plan #84):
    - Resources are STORED as float for API simplicity and JSON compatibility
    - Arithmetic operations use DECIMAL internally via _decimal_add/_decimal_sub
    - This avoids float precision errors (e.g., 0.1 + 0.2 != 0.3) while
      maintaining a simple float interface for callers
    - Scrip is stored as int (discrete currency units) - no precision issues
    - This hybrid approach is intentional: float storage for simplicity,
      Decimal arithmetic for correctness

See docs/architecture/current/resources.md for full design rationale.
"""

# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
# ADR-0002: No compute debt
#
# All balance mutations go through here.
# Never allow negative balances - fail loud.
# --- GOVERNANCE END ---
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any, TypedDict

from src.world.rate_tracker import RateTracker


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .id_registry import IDRegistry
    from .logger import EventLogger


def _to_decimal(value: float) -> Decimal:
    """Convert float to Decimal using string conversion for precision.

    Using str() avoids float representation issues like:
    >>> Decimal(0.1)  # Bad: Decimal('0.1000000000000000055511151231...')
    >>> Decimal(str(0.1))  # Good: Decimal('0.1')
    """
    return Decimal(str(value))


def _from_decimal(value: Decimal) -> float:
    """Convert Decimal back to float for API compatibility."""
    return float(value)


def _decimal_add(a: float, b: float) -> float:
    """Add two floats using Decimal arithmetic for precision.

    Part of the hybrid precision strategy: accepts/returns float for API
    simplicity, but uses Decimal internally to avoid accumulation errors.
    """
    return _from_decimal(_to_decimal(a) + _to_decimal(b))


def _decimal_sub(a: float, b: float) -> float:
    """Subtract two floats using Decimal arithmetic for precision.

    Part of the hybrid precision strategy: accepts/returns float for API
    simplicity, but uses Decimal internally to avoid accumulation errors.
    """
    return _from_decimal(_to_decimal(a) - _to_decimal(b))


class BalanceInfo(TypedDict):
    """Type for balance information per principal."""
    scrip: int
    resources: dict[str, float]


class Ledger:
    """
    Tracks resources and scrip per principal.

    - resources: Generic resource balances {principal: {resource: amount}}
    - scrip: Economic currency (special - used for trading)

    Resources can be:
    - Renewable: Rate-limited via RateTracker (llm_budget, bandwidth)
    - Stock: Never reset (disk)

    Integrates with RateTracker for rolling-window rate limiting.

    Optionally integrates with IDRegistry for global ID collision prevention
    (Plan #7: Single ID Namespace).
    """

    resources: dict[str, dict[str, float]]
    scrip: dict[str, int]
    rate_tracker: RateTracker
    id_registry: "IDRegistry | None"
    _scrip_lock: asyncio.Lock
    _resource_lock: asyncio.Lock

    def __init__(
        self,
        rate_tracker: RateTracker | None = None,
        id_registry: "IDRegistry | None" = None,
    ) -> None:
        # Generic resources: {principal_id: {resource_name: amount}}
        self.resources = {}
        # Scrip: persistent currency (accumulates/depletes)
        self.scrip = {}
        # Rate tracker for rolling-window rate limiting (always active, Plan #247)
        self.rate_tracker = rate_tracker or RateTracker(window_seconds=60.0)
        # ID registry for global collision prevention (Plan #7)
        self.id_registry = id_registry
        # Async locks for thread-safe concurrent access
        self._scrip_lock = asyncio.Lock()
        self._resource_lock = asyncio.Lock()
        # TD-011: Optional event logger for observability
        self._logger: "EventLogger | None" = None

    def set_logger(self, logger: "EventLogger") -> None:
        """Set the event logger for scrip mutation logging (TD-011)."""
        self._logger = logger

    def _log_scrip_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Log a scrip mutation event if logger is available."""
        if self._logger is not None:
            self._logger.log(event_type, data)

    @classmethod
    def from_config(
        cls,
        config: dict[str, Any],
        agent_ids: list[str],
        id_registry: "IDRegistry | None" = None,
    ) -> "Ledger":
        """Create Ledger from config with optional RateTracker and IDRegistry.

        Args:
            config: Configuration dict, may contain 'rate_limiting' section
            agent_ids: List of agent IDs to initialize (currently unused,
                       but kept for future extension)
            id_registry: Optional IDRegistry for global ID collision prevention (Plan #7)

        Returns:
            Configured Ledger instance
        """
        rate_limiting_config = config.get("rate_limiting", {})

        rate_tracker = RateTracker(
            window_seconds=rate_limiting_config.get("window_seconds", 60.0)
        )
        # Configure limits from config
        resources = rate_limiting_config.get("resources", {})
        for resource_name, resource_config in resources.items():
            max_per_window = resource_config.get("max_per_window", float("inf"))
            rate_tracker.configure_limit(resource_name, max_per_window)

        return cls(
            rate_tracker=rate_tracker,
            id_registry=id_registry,
        )

    def create_principal(
        self,
        principal_id: str,
        starting_scrip: int,
        starting_resources: dict[str, float] | None = None,
    ) -> None:
        """Create a new principal with starting balances.

        If id_registry is set, registers the principal ID. Allows
        artifact→principal registration for unified ontology (Plan #254).
        """
        # Register with ID registry if available (Plan #7)
        # Plan #254: Allow if already registered as artifact (unified ontology)
        if self.id_registry is not None:
            existing_type = self.id_registry.lookup(principal_id)
            if existing_type is None:
                # Not registered - register as principal
                self.id_registry.register(principal_id, "principal")
            # If already registered as artifact or principal, skip registration
            # This supports unified ontology where artifacts can be principals
        self.scrip[principal_id] = starting_scrip
        self.resources[principal_id] = starting_resources.copy() if starting_resources else {}

    # ===== GENERIC RESOURCE API =====

    def get_resource(self, principal_id: str, resource: str) -> float:
        """Get balance for a specific resource."""
        if principal_id not in self.resources:
            return 0.0
        return self.resources[principal_id].get(resource, 0.0)

    def can_spend_resource(self, principal_id: str, resource: str, amount: float) -> bool:
        """Check if principal has enough of a resource."""
        return self.get_resource(principal_id, resource) >= amount

    def spend_resource(self, principal_id: str, resource: str, amount: float) -> bool:
        """Spend a resource. Returns False if insufficient."""
        if not self.can_spend_resource(principal_id, resource, amount):
            return False
        if principal_id not in self.resources:
            self.resources[principal_id] = {}
        current = self.get_resource(principal_id, resource)
        self.resources[principal_id][resource] = _decimal_sub(current, amount)
        return True

    def credit_resource(self, principal_id: str, resource: str, amount: float) -> None:
        """Add to a resource balance."""
        if principal_id not in self.resources:
            self.resources[principal_id] = {}
        current = self.resources[principal_id].get(resource, 0.0)
        self.resources[principal_id][resource] = _decimal_add(current, amount)

    def set_resource(self, principal_id: str, resource: str, amount: float) -> None:
        """Set a resource to a specific value."""
        if principal_id not in self.resources:
            self.resources[principal_id] = {}
        self.resources[principal_id][resource] = amount

    def transfer_resource(
        self, from_id: str, to_id: str, resource: str, amount: float
    ) -> bool:
        """Transfer a resource between principals."""
        if amount <= 0:
            return False
        if not self.can_spend_resource(from_id, resource, amount):
            return False
        # Ensure recipient exists
        if to_id not in self.resources:
            self.resources[to_id] = {}
        from_current = self.get_resource(from_id, resource)
        to_current = self.get_resource(to_id, resource)
        self.resources[from_id][resource] = _decimal_sub(from_current, amount)
        self.resources[to_id][resource] = _decimal_add(to_current, amount)
        return True

    def get_all_resources(self, principal_id: str) -> dict[str, float]:
        """Get all resource balances for a principal."""
        return dict(self.resources.get(principal_id, {}))

    # ===== ASYNC RESOURCE OPERATIONS (Thread-Safe) =====

    async def spend_resource_async(
        self, principal_id: str, resource: str, amount: float
    ) -> bool:
        """Async thread-safe spend a resource.

        Uses asyncio.Lock to ensure atomicity of check-then-spend pattern.
        Returns False if insufficient resources.

        Args:
            principal_id: ID of the principal
            resource: Name of the resource
            amount: Amount to spend

        Returns:
            True if successful, False if insufficient resources
        """
        async with self._resource_lock:
            if not self.can_spend_resource(principal_id, resource, amount):
                return False
            if principal_id not in self.resources:
                self.resources[principal_id] = {}
            current = self.get_resource(principal_id, resource)
            self.resources[principal_id][resource] = _decimal_sub(current, amount)
            return True

    async def credit_resource_async(
        self, principal_id: str, resource: str, amount: float
    ) -> None:
        """Async thread-safe add to a resource balance.

        Uses asyncio.Lock to ensure atomicity.

        Args:
            principal_id: ID of the principal
            resource: Name of the resource
            amount: Amount to add
        """
        async with self._resource_lock:
            if principal_id not in self.resources:
                self.resources[principal_id] = {}
            current = self.resources[principal_id].get(resource, 0.0)
            self.resources[principal_id][resource] = _decimal_add(current, amount)

    async def transfer_resource_async(
        self, from_id: str, to_id: str, resource: str, amount: float
    ) -> bool:
        """Async thread-safe transfer a resource between principals.

        Uses asyncio.Lock to ensure atomicity of check-then-transfer pattern.
        Returns False if insufficient resources.

        Args:
            from_id: ID of the source principal
            to_id: ID of the destination principal
            resource: Name of the resource
            amount: Amount to transfer

        Returns:
            True if successful, False if insufficient resources or invalid amount
        """
        async with self._resource_lock:
            if amount <= 0:
                return False
            if not self.can_spend_resource(from_id, resource, amount):
                return False
            # Ensure recipient exists
            if to_id not in self.resources:
                self.resources[to_id] = {}
            from_current = self.get_resource(from_id, resource)
            to_current = self.get_resource(to_id, resource)
            self.resources[from_id][resource] = _decimal_sub(from_current, amount)
            self.resources[to_id][resource] = _decimal_add(to_current, amount)
            return True

    # ===== SCRIP (Economic Currency) =====

    def get_scrip(self, principal_id: str) -> int:
        """Get scrip balance (persistent economic currency)."""
        return self.scrip.get(principal_id, 0)

    def can_afford_scrip(self, principal_id: str, amount: int) -> bool:
        """Check if principal can afford a scrip cost."""
        return self.get_scrip(principal_id) >= amount

    def deduct_scrip(self, principal_id: str, amount: int) -> bool:
        """Deduct scrip from principal. Returns False if insufficient funds."""
        if not self.can_afford_scrip(principal_id, amount):
            return False
        self.scrip[principal_id] -= amount
        self._log_scrip_event("scrip_deducted", {
            "principal_id": principal_id,
            "amount": amount,
            "new_balance": self.scrip[principal_id],
        })
        return True

    def credit_scrip(self, principal_id: str, amount: int) -> None:
        """Add scrip to principal (from sales, minting, etc.)."""
        if principal_id not in self.scrip:
            self.scrip[principal_id] = 0
        self.scrip[principal_id] += amount
        self._log_scrip_event("scrip_credited", {
            "principal_id": principal_id,
            "amount": amount,
            "new_balance": self.scrip[principal_id],
        })

    def transfer_scrip(self, from_id: str, to_id: str, amount: int) -> bool:
        """Transfer scrip between principals. Returns False if insufficient funds.

        Auto-creates recipient with 0 balance if not exists. This enables
        transfers to artifacts (contracts, firms) without explicit creation.
        """
        if amount <= 0:
            return False
        if not self.can_afford_scrip(from_id, amount):
            return False
        # Auto-create recipient if not exists (enables artifact wallets)
        if to_id not in self.scrip:
            self.scrip[to_id] = 0
        self.scrip[from_id] -= amount
        self.scrip[to_id] += amount
        self._log_scrip_event("scrip_transferred", {
            "from_id": from_id,
            "to_id": to_id,
            "amount": amount,
            "from_balance": self.scrip[from_id],
            "to_balance": self.scrip[to_id],
        })
        return True

    def principal_exists(self, principal_id: str) -> bool:
        """Check if a principal exists in the ledger (has any balance entry)."""
        return principal_id in self.scrip or principal_id in self.resources

    def ensure_principal(self, principal_id: str) -> None:
        """Ensure a principal exists with at least 0 balance.

        Useful for creating artifact wallets before transfers.
        """
        if principal_id not in self.scrip:
            self.scrip[principal_id] = 0
        if principal_id not in self.resources:
            self.resources[principal_id] = {}

    # ===== ASYNC SCRIP OPERATIONS (Thread-Safe) =====

    async def deduct_scrip_async(self, principal_id: str, amount: int) -> bool:
        """Async thread-safe deduct scrip from principal.

        Uses asyncio.Lock to ensure atomicity of check-then-deduct pattern.
        Returns False if insufficient funds.

        Args:
            principal_id: ID of the principal to deduct from
            amount: Amount of scrip to deduct

        Returns:
            True if successful, False if insufficient funds
        """
        async with self._scrip_lock:
            if not self.can_afford_scrip(principal_id, amount):
                return False
            self.scrip[principal_id] -= amount
            return True

    async def credit_scrip_async(self, principal_id: str, amount: int) -> None:
        """Async thread-safe add scrip to principal.

        Uses asyncio.Lock to ensure atomicity.

        Args:
            principal_id: ID of the principal to credit
            amount: Amount of scrip to add
        """
        async with self._scrip_lock:
            if principal_id not in self.scrip:
                self.scrip[principal_id] = 0
            self.scrip[principal_id] += amount

    async def transfer_scrip_async(self, from_id: str, to_id: str, amount: int) -> bool:
        """Async thread-safe transfer scrip between principals.

        Uses asyncio.Lock to ensure atomicity of check-then-transfer pattern.
        Auto-creates recipient with 0 balance if not exists.
        Returns False if insufficient funds.

        Args:
            from_id: ID of the source principal
            to_id: ID of the destination principal
            amount: Amount of scrip to transfer

        Returns:
            True if successful, False if insufficient funds or invalid amount
        """
        async with self._scrip_lock:
            if amount <= 0:
                return False
            if not self.can_afford_scrip(from_id, amount):
                return False
            # Auto-create recipient if not exists (enables artifact wallets)
            if to_id not in self.scrip:
                self.scrip[to_id] = 0
            self.scrip[from_id] -= amount
            self.scrip[to_id] += amount
            return True

    # ===== REPORTING =====

    def get_all_balances(self) -> dict[str, BalanceInfo]:
        """Get snapshot of all balances including all resources."""
        result: dict[str, BalanceInfo] = {}
        all_principals = set(self.resources.keys()) | set(self.scrip.keys())
        for pid in all_principals:
            result[pid] = {
                "scrip": self.scrip.get(pid, 0),
                "resources": dict(self.resources.get(pid, {})),
            }
        return result

    def get_all_scrip(self) -> dict[str, int]:
        """Get snapshot of all scrip balances."""
        return dict(self.scrip)

    def get_agent_principal_ids(self) -> list[str]:
        """Get list of agent principal IDs (excludes system principals).

        Used for UBI distribution - only real agents receive UBI, not
        system principals (those starting with 'SYSTEM' or 'kernel_').
        """
        return [
            pid for pid in self.scrip.keys()
            if not pid.startswith(("genesis_", "SYSTEM", "kernel_"))
        ]

    def distribute_ubi(self, amount: int, exclude: str | None = None) -> dict[str, int]:
        """Distribute scrip equally among all agent principals (UBI).

        Used for mint auction: winning bid is redistributed to all agents.

        Args:
            amount: Total scrip to distribute
            exclude: Optional principal ID to exclude (e.g., don't give UBI to winner)

        Returns:
            Dict mapping principal_id to amount received

        Note:
            - Only distributes to agents (not genesis artifacts)
            - Remainder from integer division goes to first recipients
            - If amount is 0 or no recipients, returns empty dict
        """
        recipients = self.get_agent_principal_ids()
        if exclude and exclude in recipients:
            recipients = [r for r in recipients if r != exclude]

        if not recipients or amount <= 0:
            return {}

        # Calculate per-recipient amount and remainder
        per_recipient = amount // len(recipients)
        remainder = amount % len(recipients)

        distribution: dict[str, int] = {}
        for i, pid in enumerate(recipients):
            # First 'remainder' recipients get 1 extra
            share = per_recipient + (1 if i < remainder else 0)
            if share > 0:
                self.credit_scrip(pid, share)
                distribution[pid] = share

        return distribution

    # ===== RATE LIMITING (Rolling Window) =====

    def check_resource_capacity(
        self,
        agent_id: str,
        resource: str,
        amount: float = 1.0,
    ) -> bool:
        """Check if agent has capacity for resource consumption.

        Args:
            agent_id: ID of the agent
            resource: Name of the resource
            amount: Amount to check (default: 1.0)

        Returns:
            True if the agent can use the requested amount
        """
        return self.rate_tracker.has_capacity(agent_id, resource, amount)

    def consume_resource(
        self,
        agent_id: str,
        resource: str,
        amount: float = 1.0,
    ) -> bool:
        """Consume resource capacity via RateTracker.

        Returns True if successful, False if insufficient capacity.

        Args:
            agent_id: ID of the agent
            resource: Name of the resource
            amount: Amount to consume (default: 1.0)

        Returns:
            True if successful, False if insufficient capacity
        """
        return self.rate_tracker.consume(agent_id, resource, amount)

    def get_resource_remaining(
        self,
        agent_id: str,
        resource: str,
    ) -> float:
        """Get remaining capacity for a resource.

        Args:
            agent_id: ID of the agent
            resource: Name of the resource

        Returns:
            Amount of resource still available in the current window
        """
        return self.rate_tracker.get_remaining(agent_id, resource)

    async def wait_for_resource(
        self,
        agent_id: str,
        resource: str,
        amount: float = 1.0,
        timeout: float | None = None,
    ) -> bool:
        """Wait until resource capacity is available.

        Returns True if capacity acquired, False if timeout.

        Args:
            agent_id: ID of the agent
            resource: Name of the resource
            amount: Amount needed (default: 1.0)
            timeout: Maximum seconds to wait (None = wait indefinitely)

        Returns:
            True if capacity was acquired, False if timeout occurred
        """
        return await self.rate_tracker.wait_for_capacity(
            agent_id, resource, amount, timeout
        )

    async def consume_resource_async(
        self,
        agent_id: str,
        resource: str,
        amount: float = 1.0,
    ) -> bool:
        """Async thread-safe consume resource capacity.

        Uses asyncio.Lock to ensure atomicity of check-then-consume pattern.
        Uses RateTracker if enabled.
        Returns True if successful, False if insufficient capacity.

        Args:
            agent_id: ID of the agent
            resource: Name of the resource
            amount: Amount to consume (default: 1.0)

        Returns:
            True if successful, False if insufficient capacity
        """
        async with self._resource_lock:
            return self.rate_tracker.consume(agent_id, resource, amount)

    # ===== LLM BUDGET (Plan #153) =====
    # Dollar-based budget constraint - THE primary LLM resource limit.

    def get_llm_budget(self, principal_id: str) -> float:
        """Get remaining LLM budget in dollars for a principal (Plan #153).

        Args:
            principal_id: ID of the principal

        Returns:
            Remaining budget in dollars
        """
        return self.get_resource(principal_id, "llm_budget")

    def can_afford_llm_call(self, principal_id: str, estimated_cost: float) -> bool:
        """Pre-flight check: can principal afford the estimated LLM cost? (Plan #153)

        Args:
            principal_id: ID of the principal
            estimated_cost: Estimated cost in dollars

        Returns:
            True if budget >= estimated_cost
        """
        return self.get_llm_budget(principal_id) >= estimated_cost

    def deduct_llm_cost(self, principal_id: str, actual_cost: float) -> bool:
        """Deduct actual LLM cost from principal's budget (Plan #153).

        Called after LLM call completes with the actual cost.

        Args:
            principal_id: ID of the principal
            actual_cost: Actual cost in dollars from the API

        Returns:
            True if successful (should always succeed post-call)
        """
        return self.spend_resource(principal_id, "llm_budget", actual_cost)

    async def deduct_llm_cost_async(self, principal_id: str, actual_cost: float) -> bool:
        """Async thread-safe deduct LLM cost from budget (Plan #153).

        Args:
            principal_id: ID of the principal
            actual_cost: Actual cost in dollars from the API

        Returns:
            True if successful
        """
        return await self.spend_resource_async(principal_id, "llm_budget", actual_cost)

    def get_llm_budget_info(self, principal_id: str) -> dict[str, float]:
        """Get LLM budget info including remaining and spent (Plan #153).

        Args:
            principal_id: ID of the principal

        Returns:
            Dict with 'remaining' budget amount
        """
        remaining = self.get_llm_budget(principal_id)
        return {
            "remaining": remaining,
        }
