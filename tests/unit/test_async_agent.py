"""Tests for async agent thinking functionality."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


from src.agents.agent import Agent
from src.agents.models import FlatActionResponse, FlatAction


class TestAgentAsyncMethod:
    """Test that Agent has async propose_action method."""

    def test_agent_has_async_method(self) -> None:
        """Agent should have propose_action_async method."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")
        assert hasattr(agent, "propose_action_async")
        assert asyncio.iscoroutinefunction(agent.propose_action_async)

    def test_agent_has_sync_method(self) -> None:
        """Agent should still have synchronous propose_action method."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")
        assert hasattr(agent, "propose_action")
        assert not asyncio.iscoroutinefunction(agent.propose_action)


class TestAsyncProposalBasics:
    """Test basic async proposal functionality."""

    @pytest.mark.asyncio
    async def test_async_method_returns_dict(self) -> None:
        """Async method should return ActionResult dict."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        # Mock the LLM provider's generate_async method
        mock_response = FlatActionResponse(
            thought_process="test thinking",
            action=FlatAction(action_type="noop"),
        )

        agent.llm.generate_async = AsyncMock(return_value=mock_response)
        agent.llm.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }

        world_state = {"tick": 1, "balances": {"test": 100}}
        result = await agent.propose_action_async(world_state)

        assert isinstance(result, dict)
        assert "action" in result or "error" in result

    @pytest.mark.asyncio
    async def test_async_returns_usage_stats(self) -> None:
        """Async method should return token usage statistics."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        mock_response = FlatActionResponse(
            thought_process="test",
            action=FlatAction(action_type="noop"),
        )

        agent.llm.generate_async = AsyncMock(return_value=mock_response)
        agent.llm.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }

        world_state = {"tick": 1, "balances": {"test": 100}}
        result = await agent.propose_action_async(world_state)

        assert "usage" in result
        assert result["usage"]["input_tokens"] == 100
        assert result["usage"]["output_tokens"] == 50


class TestParallelThinking:
    """Test that multiple agents can think in parallel."""

    @pytest.mark.asyncio
    async def test_multiple_agents_parallel(self) -> None:
        """Multiple agents should be able to think concurrently."""
        agents = [
            Agent(agent_id=f"agent_{i}", llm_model="gemini/gemini-3-flash-preview")
            for i in range(3)
        ]

        mock_response = FlatActionResponse(
            thought_process="parallel thinking",
            action=FlatAction(action_type="noop"),
        )

        for agent in agents:
            agent.llm.generate_async = AsyncMock(return_value=mock_response)
            agent.llm.last_usage = {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "cost": 0.001,
            }

        world_state = {
            "tick": 1,
            "balances": {f"agent_{i}": 100 for i in range(3)},
        }

        # Run all agents in parallel
        results = await asyncio.gather(
            *[agent.propose_action_async(world_state) for agent in agents]
        )

        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
            assert "action" in result or "error" in result


class TestAsyncErrorHandling:
    """Test error handling in async methods."""

    @pytest.mark.asyncio
    async def test_async_handles_llm_failure(self) -> None:
        """Async method should handle LLM failures gracefully."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        agent.llm.generate_async = AsyncMock(side_effect=Exception("LLM Error"))

        world_state = {"tick": 1, "balances": {"test": 100}}
        result = await agent.propose_action_async(world_state)

        assert "error" in result
        assert "LLM" in result["error"]

    @pytest.mark.asyncio
    async def test_async_handles_validation_error(self) -> None:
        """Async method should handle Pydantic validation errors."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        from pydantic import ValidationError

        # Create a proper ValidationError by trying to validate bad data
        try:
            FlatActionResponse(thought_process="test", action="not_a_flat_action")  # type: ignore
        except ValidationError as e:
            validation_error = e

        agent.llm.generate_async = AsyncMock(side_effect=validation_error)
        agent.llm.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }

        world_state = {"tick": 1, "balances": {"test": 100}}
        result = await agent.propose_action_async(world_state)

        assert "error" in result
        assert "Pydantic validation failed" in result["error"]
