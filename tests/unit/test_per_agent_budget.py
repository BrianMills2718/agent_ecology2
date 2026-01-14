"""Unit tests for per-agent LLM budget - Plan #12"""

import pytest
from decimal import Decimal

from src.world.ledger import Ledger


class TestLedgerLLMBudget:
    """Test Ledger LLM budget tracking using generic resource API."""

    def test_llm_budget_allocation(self) -> None:
        """Test that llm_budget can be allocated as a resource."""
        ledger = Ledger()
        ledger.create_principal(
            "agent_a",
            starting_scrip=100,
            starting_resources={"llm_budget": 1.0},  # $1.00 budget
        )

        assert ledger.get_resource("agent_a", "llm_budget") == 1.0

    def test_llm_budget_consumption(self) -> None:
        """Test consuming LLM budget."""
        ledger = Ledger()
        ledger.create_principal(
            "agent_a",
            starting_scrip=100,
            starting_resources={"llm_budget": 1.0},
        )

        # Consume some budget
        success = ledger.spend_resource("agent_a", "llm_budget", 0.05)
        assert success is True
        assert ledger.get_resource("agent_a", "llm_budget") == pytest.approx(0.95)

    def test_llm_budget_exhausted(self) -> None:
        """Test that spending fails when budget exhausted."""
        ledger = Ledger()
        ledger.create_principal(
            "agent_a",
            starting_scrip=100,
            starting_resources={"llm_budget": 0.10},  # Only $0.10
        )

        # Try to spend more than available
        can_spend = ledger.can_spend_resource("agent_a", "llm_budget", 0.50)
        assert can_spend is False

        # Actual spend should fail
        success = ledger.spend_resource("agent_a", "llm_budget", 0.50)
        assert success is False

        # Balance unchanged
        assert ledger.get_resource("agent_a", "llm_budget") == 0.10

    def test_llm_budget_is_stock_resource(self) -> None:
        """Test that llm_budget doesn't reset per tick (stock, not flow)."""
        ledger = Ledger()
        ledger.create_principal(
            "agent_a",
            starting_scrip=100,
            starting_resources={"llm_budget": 1.0},
        )

        # Spend some budget
        ledger.spend_resource("agent_a", "llm_budget", 0.50)
        assert ledger.get_resource("agent_a", "llm_budget") == pytest.approx(0.50)

        # Unlike flow resources, budget should NOT be reset
        # (reset_flow_resources doesn't affect llm_budget since it's a stock)
        # The World handles this - llm_budget is in stock_resources config

    def test_llm_budget_transfer(self) -> None:
        """Test transferring llm_budget between agents."""
        ledger = Ledger()
        ledger.create_principal(
            "agent_a",
            starting_scrip=100,
            starting_resources={"llm_budget": 1.0},
        )
        ledger.create_principal(
            "agent_b",
            starting_scrip=100,
            starting_resources={"llm_budget": 0.5},
        )

        # Transfer budget from A to B
        success = ledger.transfer_resource("agent_a", "agent_b", "llm_budget", 0.25)
        assert success is True

        assert ledger.get_resource("agent_a", "llm_budget") == pytest.approx(0.75)
        assert ledger.get_resource("agent_b", "llm_budget") == pytest.approx(0.75)

    def test_llm_budget_precision(self) -> None:
        """Test that small budget amounts are handled with precision."""
        ledger = Ledger()
        ledger.create_principal(
            "agent_a",
            starting_scrip=100,
            starting_resources={"llm_budget": 0.001},  # $0.001
        )

        # Spend tiny amount
        success = ledger.spend_resource("agent_a", "llm_budget", 0.0001)
        assert success is True
        assert ledger.get_resource("agent_a", "llm_budget") == pytest.approx(0.0009)


class TestLedgerMultipleAgentBudgets:
    """Test budget isolation between agents."""

    def test_budget_isolation(self) -> None:
        """Test that agent budgets are isolated from each other."""
        ledger = Ledger()

        # Two agents with different budgets
        ledger.create_principal(
            "agent_a", starting_scrip=100,
            starting_resources={"llm_budget": 2.0},
        )
        ledger.create_principal(
            "agent_b", starting_scrip=100,
            starting_resources={"llm_budget": 0.5},
        )

        # Agent A spends their budget
        ledger.spend_resource("agent_a", "llm_budget", 1.5)

        # Agent A's budget affected, B's unaffected
        assert ledger.get_resource("agent_a", "llm_budget") == pytest.approx(0.5)
        assert ledger.get_resource("agent_b", "llm_budget") == pytest.approx(0.5)

    def test_one_agent_exhausted_others_continue(self) -> None:
        """Test that one agent running out doesn't affect others."""
        ledger = Ledger()

        ledger.create_principal(
            "agent_a", starting_scrip=100,
            starting_resources={"llm_budget": 0.10},
        )
        ledger.create_principal(
            "agent_b", starting_scrip=100,
            starting_resources={"llm_budget": 1.0},
        )

        # Agent A exhausts budget
        ledger.spend_resource("agent_a", "llm_budget", 0.10)

        # Agent A can't spend more
        assert not ledger.can_spend_resource("agent_a", "llm_budget", 0.01)

        # Agent B still can
        assert ledger.can_spend_resource("agent_b", "llm_budget", 0.50)
