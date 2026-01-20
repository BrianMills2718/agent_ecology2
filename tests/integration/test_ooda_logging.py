"""Integration tests for reasoning field propagation (Plan #88, updated by Plan #132).

Tests that the reasoning field is properly propagated through
the simulation runner to action events.
"""

import pytest
from unittest.mock import AsyncMock
from typing import Any

from src.agents.agent import Agent
from src.agents.models import FlatActionResponse, FlatAction


class TestReasoningPropagation:
    """Test reasoning field propagation through the runner."""

    @pytest.mark.asyncio
    async def test_thinking_result_has_reasoning(self) -> None:
        """ThinkingResult from _process_agent_thinking should include reasoning."""
        # This tests the data structure that feeds into _process_thinking_results

        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        # Mock LLM response with reasoning
        mock_response = FlatActionResponse(
            reasoning="My reasoning for this action",
            action=FlatAction(action_type="noop"),
        )

        agent.llm.generate_async = AsyncMock(return_value=mock_response)  # mock-ok: testing flow structure
        agent.llm.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }

        # Call propose_action_async directly
        world_state: dict[str, Any] = {"tick": 1, "balances": {"test": 100}}
        proposal = await agent.propose_action_async(world_state)

        # Verify structure matches what runner expects
        assert "action" in proposal
        assert "reasoning" in proposal
        assert proposal["reasoning"] == "My reasoning for this action"

        # This is the structure the runner uses:
        # reasoning = result.get("proposal", {}).get("reasoning", "")
        # The "proposal" key wraps this structure, so:
        result: dict[str, Any] = {"proposal": proposal}
        extracted = result.get("proposal", {}).get("reasoning", "")
        assert extracted == "My reasoning for this action"

    @pytest.mark.asyncio
    async def test_proposal_structure_for_execute(self) -> None:
        """Verify proposal structure is correct for _execute_proposals."""
        agent = Agent(agent_id="test", llm_model="gemini/gemini-3-flash-preview")

        mock_response = FlatActionResponse(
            reasoning="Detailed thinking about what to do",
            action=FlatAction(action_type="read_artifact", artifact_id="test"),
        )

        agent.llm.generate_async = AsyncMock(return_value=mock_response)  # mock-ok: testing flow structure
        agent.llm.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }

        world_state: dict[str, Any] = {"tick": 1}
        proposal = await agent.propose_action_async(world_state)

        # Simulate the structure created by _process_thinking_results
        action_proposal: dict[str, Any] = {
            "agent": agent,
            "proposal": proposal,  # This is the raw proposal from propose_action_async
            "thinking_cost": 150,
            "api_cost": 0.001,
        }

        # Simulate the extraction in _execute_proposals (Plan #132: standardized)
        extracted_proposal = action_proposal["proposal"]
        action_dict: dict[str, Any] = extracted_proposal["action"]
        action_dict["reasoning"] = extracted_proposal.get("reasoning", "")

        # Verify the reasoning is populated
        assert action_dict["reasoning"] == "Detailed thinking about what to do"

    @pytest.mark.asyncio
    async def test_end_to_end_reasoning_flow(self) -> None:
        """Full end-to-end test of reasoning propagation through the system.

        This tests the exact flow:
        1. propose_action_async returns reasoning
        2. _process_thinking_results stores it in proposal
        3. _execute_proposals extracts it as reasoning
        4. parse_intent_from_json creates ActionIntent with reasoning
        5. ActionIntent.to_dict includes reasoning
        """
        from src.world.actions import parse_intent_from_json
        import json

        agent = Agent(agent_id="test_agent", llm_model="gemini/gemini-3-flash-preview")

        mock_response = FlatActionResponse(
            reasoning="I am reading this to learn more",
            action=FlatAction(action_type="read_artifact", artifact_id="handbook"),
        )

        agent.llm.generate_async = AsyncMock(return_value=mock_response)  # mock-ok: testing flow
        agent.llm.last_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }

        world_state: dict[str, Any] = {"tick": 1}
        proposal = await agent.propose_action_async(world_state)

        # Simulate _process_thinking_results storing in proposals list
        action_proposal: dict[str, Any] = {
            "agent": agent,
            "proposal": proposal,
            "thinking_cost": 150,
            "api_cost": 0.001,
        }

        # Simulate _execute_proposals extracting reasoning (Plan #132: standardized)
        extracted_proposal = action_proposal["proposal"]
        action_dict = extracted_proposal["action"].copy()  # Copy to avoid mutation
        action_dict["reasoning"] = extracted_proposal.get("reasoning", "")

        # Verify reasoning is set BEFORE parsing
        assert action_dict["reasoning"] == "I am reading this to learn more", \
            f"Reasoning not set in action_dict! Keys: {action_dict.keys()}, reasoning in proposal: {'reasoning' in extracted_proposal}"

        # Now parse the intent
        action_json = json.dumps(action_dict)
        intent = parse_intent_from_json("test_agent", action_json)

        # Verify intent is not an error string
        assert not isinstance(intent, str), f"Intent parse failed: {intent}"

        # Verify reasoning is in intent
        assert intent.reasoning == "I am reading this to learn more"

        # Verify reasoning is in to_dict
        intent_dict = intent.to_dict()
        assert intent_dict["reasoning"] == "I am reading this to learn more"
