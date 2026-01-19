"""Unified Resource Manager for agent ecology.

Consolidates three previously separate resource systems:
- Balance tracking (from Ledger.resources)
- Rate limiting (from RateTracker)
- Quota management (from World._quota_limits)

Plan #95: Unified Resource System
"""

from __future__ import annotations

from collections import defaultdict
from enum import Enum, auto
from typing import Any


class ResourceType(Enum):
    """Classification of resource behavior."""

    DEPLETABLE = auto()  # Once spent, gone forever (e.g., llm_budget in $)
    ALLOCATABLE = auto()  # Quota-based, reclaimable (e.g., disk bytes)
    RENEWABLE = auto()  # Rate-limited via rolling window (e.g., llm_tokens)


class ResourceManager:
    """Unified resource management for principals (agents/artifacts).

    Provides a single interface for:
    - Balance tracking (get/set/spend/credit)
    - Quota management (allocate/deallocate within limits)
    - Rate limiting (consume within rolling window limits)
    - Transfers between principals

    Example:
        rm = ResourceManager()
        rm.register_resource("llm_budget", ResourceType.DEPLETABLE, unit="dollars")
        rm.register_resource("disk", ResourceType.ALLOCATABLE, unit="bytes")
        rm.register_resource("llm_tokens", ResourceType.RENEWABLE, unit="tokens")

        rm.create_principal("agent_a", initial_resources={"llm_budget": 1.0})
        rm.set_quota("agent_a", "disk", 10000.0)
        rm.set_rate_limit("llm_tokens", max_per_window=1000.0)

        rm.spend("agent_a", "llm_budget", 0.10)  # Spend 10 cents
        rm.allocate("agent_a", "disk", 5000.0)  # Allocate 5KB
        rm.consume_rate("agent_a", "llm_tokens", 100.0)  # Consume 100 tokens
    """

    def __init__(self, rate_window_seconds: float = 60.0) -> None:
        """Initialize the resource manager.

        Args:
            rate_window_seconds: Rolling window duration for rate limiting.
        """
        self.rate_window_seconds = rate_window_seconds

        # Resource type registry: resource_name -> ResourceType
        self._resource_types: dict[str, ResourceType] = {}

        # Resource metadata: resource_name -> {"unit": str, ...}
        self._resource_meta: dict[str, dict[str, Any]] = {}

        # Balances: principal_id -> resource_name -> amount
        self._balances: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        # Quotas: principal_id -> resource_name -> limit
        self._quotas: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        # Rate limits: resource_name -> max_per_window
        self._rate_limits: dict[str, float] = {}

        # Rate usage: principal_id -> resource_name -> consumed_in_window
        # Note: For simplicity, this tracks current window usage.
        # A production system would use RateTracker's rolling window.
        self._rate_usage: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        # Set of known principals
        self._principals: set[str] = set()

    # ========== Resource Registration ==========

    def register_resource(
        self,
        name: str,
        resource_type: ResourceType,
        unit: str | None = None,
    ) -> None:
        """Register a resource type.

        Args:
            name: Unique resource identifier.
            resource_type: How this resource behaves.
            unit: Optional unit label (e.g., "dollars", "bytes").
        """
        self._resource_types[name] = resource_type
        self._resource_meta[name] = {"unit": unit}

    def get_resource_type(self, name: str) -> ResourceType | None:
        """Get the type of a registered resource.

        Args:
            name: Resource identifier.

        Returns:
            ResourceType if registered, None otherwise.
        """
        return self._resource_types.get(name)

    # ========== Principal Management ==========

    def create_principal(
        self,
        principal_id: str,
        initial_resources: dict[str, float] | None = None,
    ) -> None:
        """Create a principal (agent or artifact).

        Args:
            principal_id: Unique identifier for the principal.
            initial_resources: Optional initial resource balances.
        """
        self._principals.add(principal_id)

        if initial_resources:
            for resource, amount in initial_resources.items():
                self._balances[principal_id][resource] = amount

    def principal_exists(self, principal_id: str) -> bool:
        """Check if a principal exists.

        Args:
            principal_id: Principal to check.

        Returns:
            True if principal exists.
        """
        return principal_id in self._principals

    # ========== Balance Operations ==========

    def get_balance(self, principal_id: str, resource: str) -> float:
        """Get current balance for a resource.

        Args:
            principal_id: Principal to query.
            resource: Resource name.

        Returns:
            Current balance, 0.0 if principal or resource unknown.
        """
        if principal_id not in self._principals:
            return 0.0
        return self._balances[principal_id][resource]

    def set_balance(
        self, principal_id: str, resource: str, amount: float
    ) -> None:
        """Set balance directly.

        Args:
            principal_id: Principal to update.
            resource: Resource name.
            amount: New balance value.
        """
        self._balances[principal_id][resource] = amount

    def credit(
        self, principal_id: str, resource: str, amount: float
    ) -> None:
        """Add to a principal's balance.

        Args:
            principal_id: Principal to credit.
            resource: Resource name.
            amount: Amount to add.
        """
        self._balances[principal_id][resource] += amount

    def spend(
        self, principal_id: str, resource: str, amount: float
    ) -> bool:
        """Deduct from balance if sufficient.

        Args:
            principal_id: Principal to debit.
            resource: Resource name.
            amount: Amount to spend.

        Returns:
            True if spend succeeded, False if insufficient balance.
        """
        current = self._balances[principal_id][resource]
        if current < amount:
            return False
        self._balances[principal_id][resource] = current - amount
        return True

    def can_spend(
        self, principal_id: str, resource: str, amount: float
    ) -> bool:
        """Check if spend would succeed without actually spending.

        Args:
            principal_id: Principal to check.
            resource: Resource name.
            amount: Amount to check.

        Returns:
            True if balance is sufficient.
        """
        return self._balances[principal_id][resource] >= amount

    # ========== Quota Management (Allocatable Resources) ==========

    def set_quota(
        self, principal_id: str, resource: str, limit: float
    ) -> None:
        """Set quota limit for a principal.

        Args:
            principal_id: Principal to configure.
            resource: Resource name (should be ALLOCATABLE type).
            limit: Maximum allocation allowed.
        """
        self._quotas[principal_id][resource] = limit

    def get_quota(self, principal_id: str, resource: str) -> float:
        """Get quota limit for a principal.

        Args:
            principal_id: Principal to query.
            resource: Resource name.

        Returns:
            Quota limit, 0.0 if not set.
        """
        return self._quotas[principal_id][resource]

    def allocate(
        self, principal_id: str, resource: str, amount: float
    ) -> bool:
        """Allocate resource within quota limit.

        Args:
            principal_id: Principal requesting allocation.
            resource: Resource name.
            amount: Amount to allocate.

        Returns:
            True if allocation succeeded, False if would exceed quota.
        """
        current = self._balances[principal_id][resource]
        quota = self._quotas[principal_id][resource]

        if current + amount > quota:
            return False

        self._balances[principal_id][resource] = current + amount
        return True

    def deallocate(
        self, principal_id: str, resource: str, amount: float
    ) -> None:
        """Release allocated resource.

        Args:
            principal_id: Principal releasing allocation.
            resource: Resource name.
            amount: Amount to release.
        """
        current = self._balances[principal_id][resource]
        self._balances[principal_id][resource] = max(0.0, current - amount)

    def get_available_quota(
        self, principal_id: str, resource: str
    ) -> float:
        """Get remaining quota capacity.

        Args:
            principal_id: Principal to query.
            resource: Resource name.

        Returns:
            Remaining allocation capacity (quota - current usage).
        """
        quota = self._quotas[principal_id][resource]
        current = self._balances[principal_id][resource]
        return quota - current

    # ========== Rate Limiting (Renewable Resources) ==========

    def set_rate_limit(
        self, resource: str, max_per_window: float
    ) -> None:
        """Set rate limit for a renewable resource.

        Args:
            resource: Resource name (should be RENEWABLE type).
            max_per_window: Maximum consumption per window.
        """
        self._rate_limits[resource] = max_per_window

    def get_rate_limit(self, resource: str) -> float:
        """Get rate limit for a resource.

        Args:
            resource: Resource name.

        Returns:
            Rate limit, 0.0 if not set.
        """
        return self._rate_limits.get(resource, 0.0)

    def consume_rate(
        self, principal_id: str, resource: str, amount: float
    ) -> bool:
        """Consume rate-limited resource.

        Args:
            principal_id: Principal consuming.
            resource: Resource name.
            amount: Amount to consume.

        Returns:
            True if consumption succeeded, False if would exceed rate limit.
        """
        limit = self._rate_limits.get(resource, 0.0)
        current = self._rate_usage[principal_id][resource]

        if current + amount > limit:
            return False

        self._rate_usage[principal_id][resource] = current + amount
        return True

    def get_rate_remaining(
        self, principal_id: str, resource: str
    ) -> float:
        """Get remaining rate capacity for current window.

        Args:
            principal_id: Principal to query.
            resource: Resource name.

        Returns:
            Remaining capacity in current window.
        """
        limit = self._rate_limits.get(resource, 0.0)
        current = self._rate_usage[principal_id][resource]
        return limit - current

    def has_rate_capacity(
        self, principal_id: str, resource: str, amount: float
    ) -> bool:
        """Check if rate consumption would succeed.

        Args:
            principal_id: Principal to check.
            resource: Resource name.
            amount: Amount to check.

        Returns:
            True if within rate limit.
        """
        limit = self._rate_limits.get(resource, 0.0)
        current = self._rate_usage[principal_id][resource]
        return current + amount <= limit

    # ========== Transfers ==========

    def transfer(
        self,
        from_principal: str,
        to_principal: str,
        resource: str,
        amount: float,
    ) -> bool:
        """Transfer resource between principals.

        Creates recipient principal if it doesn't exist.

        Args:
            from_principal: Source principal.
            to_principal: Destination principal.
            resource: Resource to transfer.
            amount: Amount to transfer.

        Returns:
            True if transfer succeeded, False if insufficient balance.
        """
        # Check sender has sufficient balance
        if not self.can_spend(from_principal, resource, amount):
            return False

        # Create recipient if needed
        if not self.principal_exists(to_principal):
            self.create_principal(to_principal)

        # Execute transfer
        self.spend(from_principal, resource, amount)
        self.credit(to_principal, resource, amount)
        return True

    # ========== Reporting ==========

    def get_all_balances(self) -> dict[str, dict[str, float]]:
        """Get snapshot of all principal balances.

        Returns:
            Dict mapping principal_id -> resource -> balance.
            Only includes principals with non-zero balances.
        """
        result: dict[str, dict[str, float]] = {}
        for principal_id in self._principals:
            balances = dict(self._balances[principal_id])
            # Filter out zero balances
            non_zero = {k: v for k, v in balances.items() if v != 0.0}
            if non_zero:
                result[principal_id] = non_zero
        return result

    def get_all_quotas(self) -> dict[str, dict[str, float]]:
        """Get snapshot of all principal quotas.

        Returns:
            Dict mapping principal_id -> resource -> quota_limit.
            Only includes principals with set quotas.
        """
        result: dict[str, dict[str, float]] = {}
        for principal_id in self._principals:
            quotas = dict(self._quotas[principal_id])
            non_zero = {k: v for k, v in quotas.items() if v != 0.0}
            if non_zero:
                result[principal_id] = non_zero
        return result

    def get_principal_summary(
        self, principal_id: str
    ) -> dict[str, dict[str, float]]:
        """Get detailed resource summary for a principal.

        Args:
            principal_id: Principal to summarize.

        Returns:
            Dict with "balances", "quotas", and "available" keys.
        """
        balances = dict(self._balances[principal_id])
        quotas = dict(self._quotas[principal_id])

        # Calculate available quota for each resource with a quota
        available: dict[str, float] = {}
        for resource, quota in quotas.items():
            if quota > 0:
                available[resource] = quota - balances.get(resource, 0.0)

        return {
            "balances": balances,
            "quotas": quotas,
            "available": available,
        }
