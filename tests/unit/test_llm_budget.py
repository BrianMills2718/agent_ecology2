"""Tests for LLM budget trading functionality.

Plan #30: LLM Budget Trading
Tests the ability to transfer LLM budget between principals.
"""

import pytest
from decimal import Decimal

from src.world.world import World
from src.world.kernel_interface import KernelState, KernelActions


@pytest.mark.plans([30])
class TestLLMBudgetTransfer:
    """Test LLM budget transfer at kernel level."""

    def test_transfer_success(self, test_world: World) -> None:
        """Test successful LLM budget transfer between agents."""
        test_world.ledger.create_principal("alice", starting_scrip=100)
        test_world.ledger.create_principal("bob", starting_scrip=100)

        # Give alice some LLM budget
        test_world.ledger.set_resource("alice", "llm_budget", 1000.0)
        test_world.ledger.set_resource("bob", "llm_budget", 500.0)

        # Transfer via kernel interface
        actions = KernelActions(test_world)
        success = actions.transfer_llm_budget("alice", "bob", 200.0)

        assert success is True
        assert test_world.ledger.get_resource("alice", "llm_budget") == 800.0
        assert test_world.ledger.get_resource("bob", "llm_budget") == 700.0

    def test_insufficient_budget(self, test_world: World) -> None:
        """Test that transfer fails if sender has insufficient budget."""
        test_world.ledger.create_principal("alice", starting_scrip=100)
        test_world.ledger.create_principal("bob", starting_scrip=100)

        # Alice has only 100 budget
        test_world.ledger.set_resource("alice", "llm_budget", 100.0)
        test_world.ledger.set_resource("bob", "llm_budget", 500.0)

        actions = KernelActions(test_world)
        success = actions.transfer_llm_budget("alice", "bob", 200.0)

        assert success is False
        # Balances unchanged
        assert test_world.ledger.get_resource("alice", "llm_budget") == 100.0
        assert test_world.ledger.get_resource("bob", "llm_budget") == 500.0

    def test_negative_amount_rejected(self, test_world: World) -> None:
        """Test that negative transfer amounts are rejected."""
        test_world.ledger.create_principal("alice", starting_scrip=100)
        test_world.ledger.create_principal("bob", starting_scrip=100)

        test_world.ledger.set_resource("alice", "llm_budget", 1000.0)

        actions = KernelActions(test_world)
        success = actions.transfer_llm_budget("alice", "bob", -50.0)

        assert success is False

    def test_zero_amount_rejected(self, test_world: World) -> None:
        """Test that zero transfer amounts are rejected."""
        test_world.ledger.create_principal("alice", starting_scrip=100)
        test_world.ledger.create_principal("bob", starting_scrip=100)

        test_world.ledger.set_resource("alice", "llm_budget", 1000.0)

        actions = KernelActions(test_world)
        success = actions.transfer_llm_budget("alice", "bob", 0.0)

        assert success is False


@pytest.mark.plans([30])
class TestGetLLMBudget:
    """Test LLM budget query at kernel level."""

    def test_get_budget(self, test_world: World) -> None:
        """Test querying LLM budget via kernel state."""
        test_world.ledger.create_principal("alice", starting_scrip=100)
        test_world.ledger.set_resource("alice", "llm_budget", 1000.0)

        state = KernelState(test_world)
        budget = state.get_llm_budget("alice")

        assert budget == 1000.0

    def test_get_budget_nonexistent_principal(self, test_world: World) -> None:
        """Test querying budget for non-existent principal returns 0."""
        state = KernelState(test_world)
        budget = state.get_llm_budget("nonexistent")

        assert budget == 0.0
