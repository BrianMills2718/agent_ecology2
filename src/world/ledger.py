"""Ledger for tracking resources and scrip (economic currency)

Two separate accounting systems:
1. Compute - Real resource (LLM tokens per tick). Resets each tick.
2. Scrip - Economic currency. Persistent. Earned/spent through trade.

See docs/RESOURCE_MODEL.md for full design rationale.
"""

from __future__ import annotations

import math
from typing import Any, TypedDict


class BalanceInfo(TypedDict):
    """Type for balance information per principal."""

    compute: int
    scrip: int


class Ledger:
    """
    Tracks two types of balances per principal:

    - compute: LLM tokens remaining this tick (resets each tick to compute_quota)
    - scrip: Persistent economic currency (earned/spent, never resets)
    """

    compute: dict[str, int]
    scrip: dict[str, int]

    def __init__(self) -> None:
        # Compute: LLM tokens remaining this tick (resets each tick)
        self.compute = {}
        # Scrip: persistent currency (accumulates/depletes)
        self.scrip = {}

    def create_principal(
        self, principal_id: str, starting_scrip: int, starting_compute: int = 0
    ) -> None:
        """Create a new principal with starting balances"""
        self.scrip[principal_id] = starting_scrip
        self.compute[principal_id] = starting_compute

    # ===== COMPUTE (LLM Token Budget) =====

    def get_compute(self, principal_id: str) -> int:
        """Get remaining compute (LLM tokens) this tick"""
        return self.compute.get(principal_id, 0)

    def can_spend_compute(self, principal_id: str, amount: int) -> bool:
        """Check if principal has enough compute for an action"""
        return self.get_compute(principal_id) >= amount

    def spend_compute(self, principal_id: str, amount: int) -> bool:
        """Spend compute on an action. Returns False if insufficient."""
        if not self.can_spend_compute(principal_id, amount):
            return False
        self.compute[principal_id] -= amount
        return True

    def reset_compute(self, principal_id: str, compute_quota: int) -> None:
        """Reset compute to quota at start of tick (use it or lose it)"""
        self.compute[principal_id] = compute_quota

    # ===== SCRIP (Economic Currency) =====

    def get_scrip(self, principal_id: str) -> int:
        """Get scrip balance (persistent economic currency)"""
        return self.scrip.get(principal_id, 0)

    def can_afford_scrip(self, principal_id: str, amount: int) -> bool:
        """Check if principal can afford a scrip cost"""
        return self.get_scrip(principal_id) >= amount

    def deduct_scrip(self, principal_id: str, amount: int) -> bool:
        """Deduct scrip from principal. Returns False if insufficient funds."""
        if not self.can_afford_scrip(principal_id, amount):
            return False
        self.scrip[principal_id] -= amount
        return True

    def credit_scrip(self, principal_id: str, amount: int) -> None:
        """Add scrip to principal (from sales, minting, etc.)"""
        if principal_id not in self.scrip:
            self.scrip[principal_id] = 0
        self.scrip[principal_id] += amount

    def transfer_scrip(self, from_id: str, to_id: str, amount: int) -> bool:
        """Transfer scrip between principals. Returns False if insufficient funds."""
        if amount <= 0:
            return False
        if not self.can_afford_scrip(from_id, amount):
            return False
        if to_id not in self.scrip:
            return False  # recipient must exist
        self.scrip[from_id] -= amount
        self.scrip[to_id] += amount
        return True

    # ===== BACKWARD COMPAT (deprecated - use new names) =====

    def get_flow(self, principal_id: str) -> int:
        """DEPRECATED: Use get_compute()"""
        return self.get_compute(principal_id)

    def can_spend_flow(self, principal_id: str, amount: int) -> bool:
        """DEPRECATED: Use can_spend_compute()"""
        return self.can_spend_compute(principal_id, amount)

    def spend_flow(self, principal_id: str, amount: int) -> bool:
        """DEPRECATED: Use spend_compute()"""
        return self.spend_compute(principal_id, amount)

    def reset_flow(self, principal_id: str, quota: int) -> None:
        """DEPRECATED: Use reset_compute()"""
        self.reset_compute(principal_id, quota)

    def get_all_flow(self) -> dict[str, int]:
        """DEPRECATED: Use get_all_compute()"""
        return self.get_all_compute()

    # ===== REPORTING =====

    def get_all_balances(self) -> dict[str, BalanceInfo]:
        """Get snapshot of all balances (both compute and scrip)"""
        result: dict[str, BalanceInfo] = {}
        all_principals = set(self.compute.keys()) | set(self.scrip.keys())
        for pid in all_principals:
            result[pid] = {
                "compute": self.compute.get(pid, 0),
                "scrip": self.scrip.get(pid, 0),
            }
        return result

    def get_all_scrip(self) -> dict[str, int]:
        """Get snapshot of all scrip balances"""
        return dict(self.scrip)

    def get_all_compute(self) -> dict[str, int]:
        """Get snapshot of all compute balances"""
        return dict(self.compute)

    def calculate_thinking_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        rate_input: float,
        rate_output: float,
    ) -> int:
        """
        Calculate thinking cost based on token usage and rates.

        Thinking consumes COMPUTE (real LLM tokens), not scrip.

        Args:
            input_tokens: Number of input (prompt) tokens
            output_tokens: Number of output (completion) tokens
            rate_input: Compute units per 1K input tokens
            rate_output: Compute units per 1K output tokens

        Returns:
            Total thinking cost in compute units (rounded up)
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
        """
        Calculate and deduct thinking cost from principal's COMPUTE.

        Thinking consumes actual LLM tokens (compute), not scrip.

        Returns:
            (success, cost): Whether deduction succeeded and the cost amount
        """
        cost = self.calculate_thinking_cost(
            input_tokens, output_tokens, rate_input, rate_output
        )
        success = self.spend_compute(principal_id, cost)
        return success, cost
