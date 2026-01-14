"""Integration tests for per-agent LLM budget - Plan #12"""

import pytest
import tempfile
from pathlib import Path

from src.world.world import World
from src.world.simulation_engine import SimulationEngine


class TestPerAgentBudgetIntegration:
    """Integration tests for per-agent budget enforcement."""

    def test_budget_isolation(self) -> None:
        """Test that agent budgets are isolated - one exhausted doesn't affect others."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "agent_rich", "starting_scrip": 100, "llm_budget": 2.0},
                {"id": "agent_poor", "starting_scrip": 100, "llm_budget": 0.10},
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Verify initial allocations
        assert world.ledger.get_resource("agent_rich", "llm_budget") == pytest.approx(2.0)
        assert world.ledger.get_resource("agent_poor", "llm_budget") == pytest.approx(0.10)

        # Agent poor spends most of their budget
        world.ledger.spend_resource("agent_poor", "llm_budget", 0.09)

        # Agent rich unaffected
        assert world.ledger.get_resource("agent_rich", "llm_budget") == pytest.approx(2.0)
        assert world.ledger.get_resource("agent_poor", "llm_budget") == pytest.approx(0.01)

    def test_no_per_agent_budget_when_zero(self) -> None:
        """Test that per-agent budget is not enforced when set to 0."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "budget": {"per_agent_budget": 0.0},  # No per-agent enforcement
            "principals": [
                {"id": "agent_a", "starting_scrip": 100},
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # No llm_budget resource should be allocated
        assert world.ledger.get_resource("agent_a", "llm_budget") == 0.0
        # But the resource dict shouldn't have the key
        assert "llm_budget" not in world.ledger.resources.get("agent_a", {})

    def test_per_agent_config_override(self) -> None:
        """Test that per-principal llm_budget overrides default."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "budget": {"per_agent_budget": 1.0},  # Default $1.00
            "principals": [
                {"id": "agent_default", "starting_scrip": 100},  # Uses default
                {"id": "agent_custom", "starting_scrip": 100, "llm_budget": 5.0},  # Custom
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        assert world.ledger.get_resource("agent_default", "llm_budget") == pytest.approx(1.0)
        assert world.ledger.get_resource("agent_custom", "llm_budget") == pytest.approx(5.0)


class TestSimulationEnginePerAgentCosts:
    """Test SimulationEngine per-agent cost tracking."""

    def test_per_agent_cost_tracking(self) -> None:
        """Test that costs are tracked per agent."""
        engine = SimulationEngine()

        # Track costs for different agents
        engine.track_api_cost(0.05, agent_id="agent_a")
        engine.track_api_cost(0.10, agent_id="agent_b")
        engine.track_api_cost(0.03, agent_id="agent_a")

        # Verify per-agent tracking
        assert engine.get_agent_cost("agent_a") == pytest.approx(0.08)
        assert engine.get_agent_cost("agent_b") == pytest.approx(0.10)
        assert engine.get_agent_cost("agent_c") == 0.0  # No activity

        # Global tracking still works
        assert engine.cumulative_api_cost == pytest.approx(0.18)

    def test_backward_compatible_tracking(self) -> None:
        """Test that tracking without agent_id still works."""
        engine = SimulationEngine()

        # Track without agent_id (backward compatible)
        engine.track_api_cost(0.05)
        engine.track_api_cost(0.10)

        # Global tracking works
        assert engine.cumulative_api_cost == pytest.approx(0.15)

        # No per-agent costs recorded
        assert engine.per_agent_costs == {}


class TestBudgetTrading:
    """Test that llm_budget can be transferred/traded."""

    def test_budget_transfer(self) -> None:
        """Test transferring llm_budget between agents."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        config = {
            "world": {"max_ticks": 10},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
            "logging": {"output_file": output_file},
            "principals": [
                {"id": "agent_a", "starting_scrip": 100, "llm_budget": 2.0},
                {"id": "agent_b", "starting_scrip": 100, "llm_budget": 0.5},
            ],
            "rights": {
                "default_quotas": {"compute": 1000.0, "disk": 10000.0}
            },
        }
        world = World(config)

        # Agent A transfers budget to Agent B
        success = world.ledger.transfer_resource("agent_a", "agent_b", "llm_budget", 0.5)
        assert success is True

        assert world.ledger.get_resource("agent_a", "llm_budget") == pytest.approx(1.5)
        assert world.ledger.get_resource("agent_b", "llm_budget") == pytest.approx(1.0)
