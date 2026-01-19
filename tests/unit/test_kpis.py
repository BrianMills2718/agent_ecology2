"""Unit tests for ecosystem health KPIs."""

from __future__ import annotations

import pytest


class TestGiniCoefficient:
    """Tests for Gini coefficient calculation."""

    def test_gini_coefficient_equal(self) -> None:
        """All equal balances should give Gini of 0."""
        from src.dashboard.kpis import calculate_gini_coefficient

        # All agents have equal wealth
        balances = [100, 100, 100, 100]
        gini = calculate_gini_coefficient(balances)
        assert gini == pytest.approx(0.0, abs=0.01)

    def test_gini_coefficient_concentrated(self) -> None:
        """One agent has all wealth should give Gini close to 1."""
        from src.dashboard.kpis import calculate_gini_coefficient

        # One agent has everything, others have nothing
        balances = [0, 0, 0, 1000]
        gini = calculate_gini_coefficient(balances)
        # For 4 agents with perfect inequality, Gini = (n-1)/n = 0.75
        # But with one having all, it approaches 1 as n increases
        assert gini >= 0.7  # Should be high inequality

    def test_gini_coefficient_moderate(self) -> None:
        """Moderate inequality should give intermediate Gini."""
        from src.dashboard.kpis import calculate_gini_coefficient

        # Some inequality but not extreme
        balances = [50, 100, 150, 200]
        gini = calculate_gini_coefficient(balances)
        assert 0.1 < gini < 0.5  # Moderate inequality

    def test_gini_coefficient_empty(self) -> None:
        """Empty balances should return 0."""
        from src.dashboard.kpis import calculate_gini_coefficient

        balances: list[int] = []
        gini = calculate_gini_coefficient(balances)
        assert gini == 0.0

    def test_gini_coefficient_single(self) -> None:
        """Single agent should return 0 (perfect equality by definition)."""
        from src.dashboard.kpis import calculate_gini_coefficient

        balances = [1000]
        gini = calculate_gini_coefficient(balances)
        assert gini == 0.0


class TestScripVelocity:
    """Tests for scrip velocity calculation."""

    def test_scrip_velocity_calculation(self) -> None:
        """Velocity = transfers / total_scrip / time."""
        from src.dashboard.kpis import calculate_scrip_velocity

        total_transfers = 500
        total_scrip = 1000
        elapsed_seconds = 100.0

        velocity = calculate_scrip_velocity(total_transfers, total_scrip, elapsed_seconds)
        # velocity = 500 / 1000 / 100 = 0.005
        assert velocity == pytest.approx(0.005, abs=0.0001)

    def test_scrip_velocity_zero_scrip(self) -> None:
        """Zero total scrip should return 0 (avoid division by zero)."""
        from src.dashboard.kpis import calculate_scrip_velocity

        velocity = calculate_scrip_velocity(100, 0, 100.0)
        assert velocity == 0.0

    def test_scrip_velocity_zero_time(self) -> None:
        """Zero elapsed time should return 0 (avoid division by zero)."""
        from src.dashboard.kpis import calculate_scrip_velocity

        velocity = calculate_scrip_velocity(100, 1000, 0.0)
        assert velocity == 0.0


class TestFrozenCount:
    """Tests for counting frozen agents."""

    def test_frozen_count_none(self) -> None:
        """No agents frozen should return 0."""
        from src.dashboard.kpis import count_frozen_agents

        # All agents have LLM tokens available
        agents = [
            {"llm_tokens_used": 50.0, "llm_tokens_quota": 100.0},
            {"llm_tokens_used": 80.0, "llm_tokens_quota": 100.0},
        ]
        count = count_frozen_agents(agents)
        assert count == 0

    def test_frozen_count_some(self) -> None:
        """Some frozen agents should be counted correctly."""
        from src.dashboard.kpis import count_frozen_agents

        agents = [
            {"llm_tokens_used": 50.0, "llm_tokens_quota": 100.0},   # Active
            {"llm_tokens_used": 100.0, "llm_tokens_quota": 100.0},  # Frozen
            {"llm_tokens_used": 150.0, "llm_tokens_quota": 100.0},  # Frozen (over quota)
        ]
        count = count_frozen_agents(agents)
        assert count == 2

    def test_frozen_count_all(self) -> None:
        """All frozen agents should be counted."""
        from src.dashboard.kpis import count_frozen_agents

        agents = [
            {"llm_tokens_used": 100.0, "llm_tokens_quota": 100.0},
            {"llm_tokens_used": 100.0, "llm_tokens_quota": 100.0},
        ]
        count = count_frozen_agents(agents)
        assert count == 2


class TestActiveAgentRatio:
    """Tests for active agent ratio calculation."""

    def test_active_ratio_all_active(self) -> None:
        """All agents active should return 1.0."""
        from src.dashboard.kpis import calculate_active_agent_ratio

        # All agents have recent actions (within threshold events)
        current_tick = 10
        agents = [
            {"last_action_tick": 9},
            {"last_action_tick": 8},
            {"last_action_tick": 10},
        ]
        ratio = calculate_active_agent_ratio(agents, current_tick, threshold_events=5)
        assert ratio == pytest.approx(1.0)

    def test_active_ratio_none_active(self) -> None:
        """No agents active should return 0.0."""
        from src.dashboard.kpis import calculate_active_agent_ratio

        current_tick = 100
        agents = [
            {"last_action_tick": 10},  # 90 events ago
            {"last_action_tick": 5},   # 95 events ago
        ]
        ratio = calculate_active_agent_ratio(agents, current_tick, threshold_events=5)
        assert ratio == pytest.approx(0.0)

    def test_active_ratio_empty(self) -> None:
        """No agents should return 0.0."""
        from src.dashboard.kpis import calculate_active_agent_ratio

        ratio = calculate_active_agent_ratio([], current_tick=10, threshold_events=5)
        assert ratio == 0.0


class TestMedianScrip:
    """Tests for median scrip calculation."""

    def test_median_scrip_odd_count(self) -> None:
        """Odd number of agents should return middle value."""
        from src.dashboard.kpis import calculate_median_scrip

        balances = [100, 200, 300]
        median = calculate_median_scrip(balances)
        assert median == 200

    def test_median_scrip_even_count(self) -> None:
        """Even number of agents should return average of middle two."""
        from src.dashboard.kpis import calculate_median_scrip

        balances = [100, 200, 300, 400]
        median = calculate_median_scrip(balances)
        assert median == 250  # (200 + 300) / 2

    def test_median_scrip_empty(self) -> None:
        """Empty list should return 0."""
        from src.dashboard.kpis import calculate_median_scrip

        median = calculate_median_scrip([])
        assert median == 0


class TestEcosystemKPIs:
    """Integration tests for full KPI calculation."""

    def test_calculate_kpis_basic(self) -> None:
        """Basic KPI calculation from parser state."""
        from src.dashboard.kpis import calculate_kpis, EcosystemKPIs
        from src.dashboard.parser import SimulationState, AgentState

        # Create minimal state
        state = SimulationState()
        state.current_tick = 10
        state.api_cost_spent = 0.05
        state.api_cost_limit = 1.0
        state.start_time = "2026-01-13T00:00:00"

        # Add agents with different scrip balances
        state.agents = {
            "alice": AgentState(agent_id="alice", scrip=100, llm_tokens_used=50.0, llm_tokens_quota=100.0),
            "bob": AgentState(agent_id="bob", scrip=200, llm_tokens_used=100.0, llm_tokens_quota=100.0),  # Frozen
            "carol": AgentState(agent_id="carol", scrip=300, llm_tokens_used=30.0, llm_tokens_quota=100.0),
        }

        kpis = calculate_kpis(state)

        assert isinstance(kpis, EcosystemKPIs)
        assert kpis.total_scrip == 600
        assert kpis.median_scrip == 200
        assert kpis.frozen_agent_count == 1
        assert kpis.gini_coefficient >= 0  # Just check it's calculated


@pytest.mark.plans(76)
class TestAgentMetrics:
    """Tests for per-agent metrics (Plan #76)"""

    def test_compute_agent_metrics(self) -> None:
        """KPI calculation for individual agents."""
        from src.dashboard.kpis import compute_agent_metrics, AgentMetrics
        from src.dashboard.parser import SimulationState, AgentState

        # Create state with agent that has action history
        state = SimulationState()
        state.current_tick = 20

        agent = AgentState(
            agent_id="alpha",
            scrip=500,
            llm_tokens_used=80.0,
            llm_tokens_quota=100.0,
            action_count=15,
            last_action_tick=18,
        )
        state.agents = {"alpha": agent}

        metrics = compute_agent_metrics(state, "alpha")

        assert isinstance(metrics, AgentMetrics)
        assert metrics.total_actions == 15
        assert metrics.last_action_tick == 18
        assert metrics.ticks_since_action == 2  # 20 - 18
        assert metrics.is_frozen is False
        assert metrics.scrip_balance == 500

    def test_dormancy_calculation(self) -> None:
        """Ticks since last action calculated correctly."""
        from src.dashboard.kpis import compute_agent_metrics
        from src.dashboard.parser import SimulationState, AgentState

        state = SimulationState()
        state.current_tick = 100

        # Agent that hasn't acted in a while
        agent = AgentState(
            agent_id="dormant",
            scrip=100,
            llm_tokens_used=0.0,
            llm_tokens_quota=100.0,
            action_count=5,
            last_action_tick=50,  # 50 ticks ago
        )
        state.agents = {"dormant": agent}

        metrics = compute_agent_metrics(state, "dormant")
        assert metrics.ticks_since_action == 50

    def test_success_rate_calculation(self) -> None:
        """Agent success rate calculated from action history."""
        from src.dashboard.kpis import compute_agent_metrics
        from src.dashboard.parser import SimulationState, AgentState

        state = SimulationState()
        state.current_tick = 10

        # Agent with tracked successes/failures
        agent = AgentState(
            agent_id="mixed",
            scrip=100,
            llm_tokens_used=50.0,
            llm_tokens_quota=100.0,
            action_count=10,
            action_successes=7,
            action_failures=3,
            last_action_tick=10,
        )
        state.agents = {"mixed": agent}

        metrics = compute_agent_metrics(state, "mixed")
        assert metrics.success_rate == pytest.approx(0.7)  # 7/10

    def test_frozen_agent_detection(self) -> None:
        """Frozen agent correctly identified in metrics."""
        from src.dashboard.kpis import compute_agent_metrics
        from src.dashboard.parser import SimulationState, AgentState

        state = SimulationState()
        state.current_tick = 10

        # Frozen agent (used all tokens)
        agent = AgentState(
            agent_id="frozen",
            scrip=100,
            llm_tokens_used=100.0,
            llm_tokens_quota=100.0,
            action_count=5,
            last_action_tick=8,
        )
        state.agents = {"frozen": agent}

        metrics = compute_agent_metrics(state, "frozen")
        assert metrics.is_frozen is True

    def test_agent_not_found(self) -> None:
        """Returns None for unknown agent."""
        from src.dashboard.kpis import compute_agent_metrics
        from src.dashboard.parser import SimulationState

        state = SimulationState()
        state.agents = {}

        metrics = compute_agent_metrics(state, "nonexistent")
        assert metrics is None
