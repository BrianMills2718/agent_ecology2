"""Ledger for tracking resources and scrip (economic currency)

Two separate systems:
1. Resources - Generic resource tracking (llm_tokens, disk, bandwidth, etc.)
   - Flow resources: Reset each tick to quota (e.g., llm_tokens)
   - Stock resources: Finite pool, never reset (e.g., disk)
2. Scrip - Economic currency. Persistent. Earned/spent through trade.

Resources are defined in config and can be extended without code changes.
Principals can be any string ID - agents OR artifacts.

See docs/RESOURCE_MODEL.md for full design rationale.
"""

from __future__ import annotations

import math
from typing import Any, TypedDict


class BalanceInfo(TypedDict):
    """Type for balance information per principal."""
    scrip: int
    resources: dict[str, float]


class LegacyBalanceInfo(TypedDict):
    """Legacy balance format for backward compatibility."""
    compute: int
    scrip: int


class Ledger:
    """
    Tracks resources and scrip per principal.

    - resources: Generic resource balances {principal: {resource: amount}}
    - scrip: Economic currency (special - used for trading)

    Resources can be:
    - Flow: Reset each tick (llm_tokens, bandwidth)
    - Stock: Never reset (disk, api_budget)
    """

    resources: dict[str, dict[str, float]]
    scrip: dict[str, int]

    def __init__(self) -> None:
        # Generic resources: {principal_id: {resource_name: amount}}
        self.resources = {}
        # Scrip: persistent currency (accumulates/depletes)
        self.scrip = {}

    def create_principal(
        self,
        principal_id: str,
        starting_scrip: int,
        starting_resources: dict[str, float] | None = None,
        starting_compute: int = 0,  # Backward compat
    ) -> None:
        """Create a new principal with starting balances."""
        self.scrip[principal_id] = starting_scrip
        self.resources[principal_id] = starting_resources.copy() if starting_resources else {}
        # Backward compat: if starting_compute provided, set llm_tokens
        if starting_compute > 0:
            self.resources[principal_id]["llm_tokens"] = float(starting_compute)

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
        self.resources[principal_id][resource] = self.get_resource(principal_id, resource) - amount
        return True

    def credit_resource(self, principal_id: str, resource: str, amount: float) -> None:
        """Add to a resource balance."""
        if principal_id not in self.resources:
            self.resources[principal_id] = {}
        current = self.resources[principal_id].get(resource, 0.0)
        self.resources[principal_id][resource] = current + amount

    def set_resource(self, principal_id: str, resource: str, amount: float) -> None:
        """Set a resource to a specific value (used for tick reset)."""
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
        self.resources[from_id][resource] = self.get_resource(from_id, resource) - amount
        self.resources[to_id][resource] = self.get_resource(to_id, resource) + amount
        return True

    def get_all_resources(self, principal_id: str) -> dict[str, float]:
        """Get all resource balances for a principal."""
        return dict(self.resources.get(principal_id, {}))

    def reset_flow_resources(self, principal_id: str, quotas: dict[str, float]) -> None:
        """Reset flow resources to their quotas at tick start."""
        if principal_id not in self.resources:
            self.resources[principal_id] = {}
        for resource, quota in quotas.items():
            self.resources[principal_id][resource] = quota

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
        return True

    def credit_scrip(self, principal_id: str, amount: int) -> None:
        """Add scrip to principal (from sales, minting, etc.)."""
        if principal_id not in self.scrip:
            self.scrip[principal_id] = 0
        self.scrip[principal_id] += amount

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

    # ===== BACKWARD COMPATIBILITY (compute = llm_tokens) =====

    def get_compute(self, principal_id: str) -> int:
        """DEPRECATED: Use get_resource(principal_id, 'llm_tokens')."""
        return int(self.get_resource(principal_id, "llm_tokens"))

    def can_spend_compute(self, principal_id: str, amount: int) -> bool:
        """DEPRECATED: Use can_spend_resource(principal_id, 'llm_tokens', amount)."""
        return self.can_spend_resource(principal_id, "llm_tokens", float(amount))

    def spend_compute(self, principal_id: str, amount: int) -> bool:
        """DEPRECATED: Use spend_resource(principal_id, 'llm_tokens', amount)."""
        return self.spend_resource(principal_id, "llm_tokens", float(amount))

    def reset_compute(self, principal_id: str, compute_quota: int) -> None:
        """DEPRECATED: Use set_resource(principal_id, 'llm_tokens', quota)."""
        self.set_resource(principal_id, "llm_tokens", float(compute_quota))

    def get_flow(self, principal_id: str) -> int:
        """DEPRECATED: Use get_resource(principal_id, 'llm_tokens')."""
        return self.get_compute(principal_id)

    def can_spend_flow(self, principal_id: str, amount: int) -> bool:
        """DEPRECATED: Use can_spend_resource()."""
        return self.can_spend_compute(principal_id, amount)

    def spend_flow(self, principal_id: str, amount: int) -> bool:
        """DEPRECATED: Use spend_resource()."""
        return self.spend_compute(principal_id, amount)

    def reset_flow(self, principal_id: str, quota: int) -> None:
        """DEPRECATED: Use set_resource()."""
        self.reset_compute(principal_id, quota)

    def get_all_flow(self) -> dict[str, int]:
        """DEPRECATED: Use get_all_compute()."""
        return self.get_all_compute()

    def get_all_compute(self) -> dict[str, int]:
        """Get snapshot of all llm_tokens balances (backward compat)."""
        result: dict[str, int] = {}
        for pid, resources in self.resources.items():
            result[pid] = int(resources.get("llm_tokens", 0))
        return result

    # ===== REPORTING =====

    def get_all_balances(self) -> dict[str, LegacyBalanceInfo]:
        """Get snapshot of all balances (legacy format for backward compat)."""
        result: dict[str, LegacyBalanceInfo] = {}
        all_principals = set(self.resources.keys()) | set(self.scrip.keys())
        for pid in all_principals:
            result[pid] = {
                "compute": int(self.get_resource(pid, "llm_tokens")),
                "scrip": self.scrip.get(pid, 0),
            }
        return result

    def get_all_balances_full(self) -> dict[str, BalanceInfo]:
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

    # ===== THINKING COST (LLM tokens) =====

    def calculate_thinking_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        rate_input: float,
        rate_output: float,
    ) -> int:
        """Calculate thinking cost based on token usage and rates.

        Thinking consumes llm_tokens resource.

        Args:
            input_tokens: Number of input (prompt) tokens
            output_tokens: Number of output (completion) tokens
            rate_input: Cost units per 1K input tokens
            rate_output: Cost units per 1K output tokens

        Returns:
            Total thinking cost in llm_tokens units (rounded up)
        """
        input_cost = (input_tokens / 1000) * rate_input
        output_cost = (output_tokens / 1000) * rate_output
        return math.ceil(input_cost + output_cost)

    def deduct_thinking_cost(
        self,
        principal_id: str,
        input_tokens: int,
        output_tokens: int,
        rate_input: float,
        rate_output: float,
    ) -> tuple[bool, int]:
        """Calculate and deduct thinking cost from principal's llm_tokens.

        Returns:
            (success, cost): Whether deduction succeeded and the cost amount
        """
        cost = self.calculate_thinking_cost(
            input_tokens, output_tokens, rate_input, rate_output
        )
        success = self.spend_resource(principal_id, "llm_tokens", float(cost))
        return success, cost
