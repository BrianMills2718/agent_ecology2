"""Tests for cognitive schema and reasoning field propagation (Plan #88)."""

import pytest
from typing import Any
from unittest.mock import AsyncMock, patch

from src.agents.agent import Agent
from src.agents.models import (
    FlatActionResponse,
    FlatAction,
    FlatOODAResponse,
    OODAResponse,
)
from src.agents.schema import ActionType


class TestReasoningFieldPropagation:
    """Test that thought_process is properly passed as reasoning to actions."""

    @pytest.mark.asyncio
    async def test_propose_action_async_returns_thought_process(self) -> None:
        """propose_action_async should return thought_process in result dict."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        # Mock LLM response with thought_process
        mock_response = FlatActionResponse(
            thought_process="This is my reasoning for this action",
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

        # Verify thought_process is in result at top level
        assert "thought_process" in result, f"Result keys: {result.keys()}"
        assert result["thought_process"] == "This is my reasoning for this action"

    @pytest.mark.asyncio
    async def test_proposal_structure_has_thought_process(self) -> None:
        """Verify the proposal dict structure includes thought_process."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        mock_response = FlatActionResponse(
            thought_process="My detailed thinking",
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
        assert "thought_process" in result
        assert "usage" in result

        # Verify thought_process can be extracted
        thought_process = result.get("thought_process", "")
        assert thought_process == "My detailed thinking"


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


class TestOODASchema:
    """Test OODA cognitive schema functionality (Plan #88)."""

    def test_ooda_response_model_fields(self) -> None:
        """OODAResponse should have situation_assessment and action_rationale."""
        from src.agents.models import NoopAction

        ooda = OODAResponse(
            situation_assessment="I see 5 agents active with 100 scrip each",
            action_rationale="Reading the handbook first to understand available actions",
            action=NoopAction(),
        )

        assert ooda.situation_assessment == "I see 5 agents active with 100 scrip each"
        assert ooda.action_rationale == "Reading the handbook first to understand available actions"
        assert ooda.action.action_type == "noop"

    def test_flat_ooda_response_converts_to_ooda_response(self) -> None:
        """FlatOODAResponse should convert to OODAResponse properly."""
        flat_ooda = FlatOODAResponse(
            situation_assessment="Market analysis: escrow has 3 items",
            action_rationale="Buy cheapest item to resell at profit",
            action=FlatAction(action_type="invoke_artifact", artifact_id="escrow", method="purchase", args=["item1"]),
        )

        ooda = flat_ooda.to_ooda_response()

        assert ooda.situation_assessment == "Market analysis: escrow has 3 items"
        assert ooda.action_rationale == "Buy cheapest item to resell at profit"
        assert ooda.action.action_type == "invoke_artifact"

    @pytest.mark.asyncio
    async def test_ooda_mode_returns_ooda_fields(self) -> None:
        """When cognitive_schema=ooda, propose_action_async returns OODA fields."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        # Mock OODA response
        mock_ooda = FlatOODAResponse(
            situation_assessment="Current state analysis here",
            action_rationale="Noop because learning phase",
            action=FlatAction(action_type="noop"),
        )

        agent.llm.generate_async = AsyncMock(return_value=mock_ooda)  # mock-ok: testing schema selection, not LLM
        agent.llm.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }

        world_state: dict[str, Any] = {"tick": 1, "balances": {"test": 100}}

        # Patch config to use OODA schema
        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.return_value = "ooda"
            result = await agent.propose_action_async(world_state)

        # Verify OODA fields are present
        assert "situation_assessment" in result
        assert "action_rationale" in result
        assert result["situation_assessment"] == "Current state analysis here"
        assert result["action_rationale"] == "Noop because learning phase"

        # Verify thought_process is a combination for backwards compat
        assert "thought_process" in result
        assert "Current state analysis here" in result["thought_process"]
        assert "Noop because learning phase" in result["thought_process"]

    @pytest.mark.asyncio
    async def test_simple_mode_returns_thought_process_only(self) -> None:
        """When cognitive_schema=simple, propose_action_async returns only thought_process."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        # Mock simple response
        mock_simple = FlatActionResponse(
            thought_process="Simple reasoning here",
            action=FlatAction(action_type="noop"),
        )

        agent.llm.generate_async = AsyncMock(return_value=mock_simple)  # mock-ok: testing schema selection, not LLM
        agent.llm.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }

        world_state: dict[str, Any] = {"tick": 1, "balances": {"test": 100}}

        # Patch config to use simple schema (default)
        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.return_value = "simple"
            result = await agent.propose_action_async(world_state)

        # Verify only thought_process is present, not OODA fields
        assert "thought_process" in result
        assert result["thought_process"] == "Simple reasoning here"
        assert "situation_assessment" not in result
        assert "action_rationale" not in result

    @pytest.mark.asyncio
    async def test_config_toggle_switches_schema(self) -> None:
        """Cognitive schema config should switch between simple and OODA models."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        # Track which response model was requested
        requested_models: list[type] = []

        async def capture_generate(prompt: str, response_model: type) -> Any:
            requested_models.append(response_model)
            if response_model == FlatOODAResponse:
                return FlatOODAResponse(
                    situation_assessment="test",
                    action_rationale="test",
                    action=FlatAction(action_type="noop"),
                )
            else:
                return FlatActionResponse(
                    thought_process="test",
                    action=FlatAction(action_type="noop"),
                )

        agent.llm.generate_async = capture_generate  # mock-ok: testing model selection logic
        agent.llm.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }

        world_state: dict[str, Any] = {"tick": 1, "balances": {"test": 100}}

        # Test with simple schema
        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.return_value = "simple"
            await agent.propose_action_async(world_state)

        assert requested_models[-1] == FlatActionResponse

        # Test with OODA schema
        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.return_value = "ooda"
            await agent.propose_action_async(world_state)

        assert requested_models[-1] == FlatOODAResponse
