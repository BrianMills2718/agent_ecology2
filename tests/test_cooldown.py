"""Unit tests for agent cooldown mechanism."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from agents.agent import Agent


class TestAgentCooldown:
    """Tests for Agent cooldown mechanism."""

    @patch("agents.agent.LLMProvider")
    def test_agent_starts_no_cooldown(self, mock_llm_provider: MagicMock) -> None:
        """Agent initializes with cooldown_ticks set to 0."""
        agent = Agent(agent_id="test_agent")
        assert agent.cooldown_ticks == 0

    @patch("agents.agent.LLMProvider")
    def test_is_on_cooldown_false_when_zero(self, mock_llm_provider: MagicMock) -> None:
        """is_on_cooldown returns False when cooldown_ticks is 0."""
        agent = Agent(agent_id="test_agent")
        agent.cooldown_ticks = 0
        assert agent.is_on_cooldown() is False

    @patch("agents.agent.LLMProvider")
    def test_is_on_cooldown_true_when_positive(self, mock_llm_provider: MagicMock) -> None:
        """is_on_cooldown returns True when cooldown_ticks is greater than 0."""
        agent = Agent(agent_id="test_agent")
        agent.cooldown_ticks = 5
        assert agent.is_on_cooldown() is True

        agent.cooldown_ticks = 1
        assert agent.is_on_cooldown() is True

    @patch("agents.agent.LLMProvider")
    def test_decrement_cooldown_reduces(self, mock_llm_provider: MagicMock) -> None:
        """decrement_cooldown reduces cooldown_ticks by 1."""
        agent = Agent(agent_id="test_agent")
        agent.cooldown_ticks = 5

        agent.decrement_cooldown()
        assert agent.cooldown_ticks == 4

        agent.decrement_cooldown()
        assert agent.cooldown_ticks == 3

    @patch("agents.agent.LLMProvider")
    def test_decrement_cooldown_stops_at_zero(self, mock_llm_provider: MagicMock) -> None:
        """decrement_cooldown does not go below 0."""
        agent = Agent(agent_id="test_agent")
        agent.cooldown_ticks = 1

        agent.decrement_cooldown()
        assert agent.cooldown_ticks == 0

        # Calling decrement again should keep it at 0
        agent.decrement_cooldown()
        assert agent.cooldown_ticks == 0

        # Multiple decrements at zero
        for _ in range(5):
            agent.decrement_cooldown()
        assert agent.cooldown_ticks == 0

    @patch("agents.agent.LLMProvider")
    def test_cooldown_set_from_output_tokens(self, mock_llm_provider: MagicMock) -> None:
        """cooldown_ticks can be set externally (simulating run.py behavior)."""
        agent = Agent(agent_id="test_agent")

        # Simulate setting cooldown based on output tokens
        # (This is done by run.py, we just verify the attribute works correctly)
        output_tokens = 500
        cooldown_ticks = output_tokens // 100  # Example formula: 1 tick per 100 tokens
        agent.cooldown_ticks = cooldown_ticks

        assert agent.cooldown_ticks == 5
        assert agent.is_on_cooldown() is True

        # Decrement and verify
        for i in range(5):
            assert agent.is_on_cooldown() is True
            agent.decrement_cooldown()

        assert agent.is_on_cooldown() is False
        assert agent.cooldown_ticks == 0


class TestCooldownEdgeCases:
    """Edge case tests for cooldown mechanism."""

    @patch("agents.agent.LLMProvider")
    def test_cooldown_with_large_value(self, mock_llm_provider: MagicMock) -> None:
        """Cooldown works with large values."""
        agent = Agent(agent_id="test_agent")
        agent.cooldown_ticks = 1000

        assert agent.is_on_cooldown() is True
        agent.decrement_cooldown()
        assert agent.cooldown_ticks == 999

    @patch("agents.agent.LLMProvider")
    def test_cooldown_transitions(self, mock_llm_provider: MagicMock) -> None:
        """Verify transitions from cooldown to active state."""
        agent = Agent(agent_id="test_agent")

        # Start active
        assert agent.is_on_cooldown() is False

        # Enter cooldown
        agent.cooldown_ticks = 2
        assert agent.is_on_cooldown() is True

        # Tick 1
        agent.decrement_cooldown()
        assert agent.is_on_cooldown() is True
        assert agent.cooldown_ticks == 1

        # Tick 2 - should exit cooldown
        agent.decrement_cooldown()
        assert agent.is_on_cooldown() is False
        assert agent.cooldown_ticks == 0
