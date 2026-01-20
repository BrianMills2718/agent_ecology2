"""Tests for reasoning field and failure tracking (Plan #88, updated by Plan #132)."""

import pytest
from typing import Any
from unittest.mock import AsyncMock

from src.agents.agent import Agent
from src.agents.models import (
    FlatActionResponse,
    FlatAction,
)
from src.agents.schema import ActionType


class TestReasoningFieldPropagation:
    """Test that reasoning is properly passed to actions (Plan #132)."""

    @pytest.mark.asyncio
    async def test_propose_action_async_returns_reasoning(self) -> None:
        """propose_action_async should return reasoning in result dict."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        # Mock LLM response with reasoning
        mock_response = FlatActionResponse(
            reasoning="This is my reasoning for this action",
            action=FlatAction(action_type="noop"),
        )

        agent.llm.generate_async = AsyncMock(return_value=mock_response)  # mock-ok: testing proposal structure, not LLM
        agent.llm.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }

        world_state = {"tick": 1, "balances": {"test": 100}}
        result = await agent.propose_action_async(world_state)

        # Verify reasoning is in result at top level
        assert "reasoning" in result, f"Result keys: {result.keys()}"
        assert result["reasoning"] == "This is my reasoning for this action"

    @pytest.mark.asyncio
    async def test_proposal_structure_has_reasoning(self) -> None:
        """Verify the proposal dict structure includes reasoning."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        mock_response = FlatActionResponse(
            reasoning="My detailed thinking",
            action=FlatAction(action_type="read_artifact", artifact_id="test_artifact"),
        )

        agent.llm.generate_async = AsyncMock(return_value=mock_response)  # mock-ok: testing proposal structure, not LLM
        agent.llm.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }

        world_state = {"tick": 1}
        result = await agent.propose_action_async(world_state)

        # Verify full structure
        assert "action" in result
        assert "reasoning" in result
        assert "usage" in result

        # Verify reasoning can be extracted
        reasoning = result.get("reasoning", "")
        assert reasoning == "My detailed thinking"


class TestRecentFailuresTracking:
    """Test that recent failures are tracked and shown in prompts (Plan #88)."""

    def test_failure_history_initialized_empty(self) -> None:
        """Agent should start with empty failure history."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")
        assert agent.failure_history == []

    def test_failure_added_on_failed_action(self) -> None:
        """set_last_result should add failures to history."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        # Simulate a failed action
        action_type: ActionType = "read_artifact"
        agent.set_last_result(action_type, success=False, message="Artifact not found: foo")

        assert len(agent.failure_history) == 1
        assert "read_artifact" in agent.failure_history[0]
        assert "Artifact not found: foo" in agent.failure_history[0]

    def test_success_does_not_add_to_failures(self) -> None:
        """set_last_result should not add successful actions to failure history."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        # Simulate a successful action
        action_type: ActionType = "read_artifact"
        agent.set_last_result(action_type, success=True, message="Read successful")

        assert len(agent.failure_history) == 0

    def test_failure_history_respects_max_limit(self) -> None:
        """Failure history should be capped at configured max."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")
        agent._failure_history_max = 3  # Override for testing

        # Add more failures than the max
        for i in range(5):
            agent.set_last_result("noop", success=False, message=f"Failure {i}")

        # Should only keep the last 3
        assert len(agent.failure_history) == 3
        assert "Failure 2" in agent.failure_history[0]
        assert "Failure 3" in agent.failure_history[1]
        assert "Failure 4" in agent.failure_history[2]

    def test_failures_appear_in_prompt(self) -> None:
        """Recent failures should appear in agent prompts."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        # Add a failure
        agent.set_last_result("read_artifact", success=False, message="Access denied")

        # Build prompt
        world_state: dict[str, Any] = {"tick": 1, "balances": {"test": 100}}
        prompt = agent.build_prompt(world_state)

        # Check that failure section appears
        assert "Recent Failures" in prompt
        assert "read_artifact" in prompt
        assert "Access denied" in prompt

    def test_no_failures_section_when_empty(self) -> None:
        """Prompt should not have failures section when history is empty."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        world_state: dict[str, Any] = {"tick": 1, "balances": {"test": 100}}
        prompt = agent.build_prompt(world_state)

        assert "Recent Failures" not in prompt
