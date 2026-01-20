"""Integration tests for agent workflow execution.

Tests the full workflow execution path: Agent -> WorkflowRunner -> LLM/Code steps.
Maps to acceptance criteria in meta/acceptance_gates/agent_workflow.yaml.

Run with: pytest tests/integration/test_agent_workflow.py -v
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.agents.agent import Agent
from src.agents.workflow import WorkflowRunner, WorkflowConfig
from src.agents.models import FlatActionResponse, FlatAction


@pytest.mark.feature("agent_workflow")
class TestAgentRunsWorkflow:
    """AC-1: Agent runs simple workflow."""

    def test_agent_runs_workflow_with_code_and_llm_steps(self) -> None:
        """Agent executes a workflow with both code and LLM steps."""
        # Create agent with workflow config
        workflow_config = {
            "steps": [
                {
                    "name": "setup",
                    "type": "code",
                    "code": "ready = True",
                },
                {
                    "name": "decide",
                    "type": "llm",
                    "prompt": "You are {agent_id}. Ready: {ready}. Choose an action.",
                },
            ]
        }

        agent = Agent(
            agent_id="test_agent",
            llm_model="gemini/gemini-3-flash-preview",
            system_prompt="Test agent",
        )
        agent._workflow_config = workflow_config

        # mock-ok: LLM calls are expensive, mock for integration test
        mock_response = FlatActionResponse(
            reasoning="Testing workflow",
            action=FlatAction(action_type="noop"),
        )
        agent.llm.generate = MagicMock(return_value=mock_response)

        # Execute workflow
        world_state = {"tick": 1, "balances": {"test_agent": 100}, "artifacts": []}
        result = agent.run_workflow(world_state)

        # Verify workflow executed
        assert result["success"] is True
        assert result["action"] is not None
        assert agent.llm.generate.called


@pytest.mark.feature("agent_workflow")
class TestWorkflowProducesAction:
    """AC-2: Workflow produces valid action."""

    def test_workflow_produces_valid_action_response(self) -> None:
        """Workflow LLM step returns a valid action that can be executed."""
        workflow_config = {
            "steps": [
                {
                    "name": "act",
                    "type": "llm",
                    "prompt": "Choose an action.",
                },
            ]
        }

        agent = Agent(
            agent_id="test_agent",
            llm_model="gemini/gemini-3-flash-preview",
            system_prompt="Test agent",
        )
        agent._workflow_config = workflow_config

        # mock-ok: LLM calls are expensive
        mock_response = FlatActionResponse(
            reasoning="Reading handbook",
            action=FlatAction(
                action_type="read_artifact",
                artifact_id="genesis_handbook",
            ),
        )
        agent.llm.generate = MagicMock(return_value=mock_response)

        world_state = {"tick": 1, "balances": {"test_agent": 100}, "artifacts": []}
        result = agent.run_workflow(world_state)

        assert result["success"] is True
        action = result["action"]
        assert action is not None
        # Action is a dict from workflow's model_dump()
        assert action["action_type"] == "read_artifact"
        assert action["artifact_id"] == "genesis_handbook"


@pytest.mark.feature("agent_workflow")
class TestWorkflowCodeStepSetsContext:
    """AC-2: Workflow with code step that sets context for LLM step."""

    def test_code_step_context_available_to_llm_step(self) -> None:
        """Code step sets variables that LLM step can access via prompt interpolation."""
        workflow_config = {
            "steps": [
                {
                    "name": "analyze",
                    "type": "code",
                    "code": "priority_action = 'create' if balance > 50 else 'observe'",
                },
                {
                    "name": "decide",
                    "type": "llm",
                    "prompt": "Priority action is {priority_action}. Execute it.",
                },
            ]
        }

        agent = Agent(
            agent_id="test_agent",
            llm_model="gemini/gemini-3-flash-preview",
            system_prompt="Test agent",
        )
        agent._workflow_config = workflow_config

        # mock-ok: LLM calls are expensive
        mock_response = FlatActionResponse(
            reasoning="Executing priority",
            action=FlatAction(action_type="noop"),
        )
        agent.llm.generate = MagicMock(return_value=mock_response)

        world_state = {"tick": 1, "balances": {"test_agent": 100}, "artifacts": []}
        result = agent.run_workflow(world_state)

        assert result["success"] is True
        # Verify the prompt included the interpolated value
        call_args = agent.llm.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "create" in prompt  # balance > 50, so priority_action = 'create'


@pytest.mark.feature("agent_workflow")
class TestWorkflowErrorReturned:
    """AC-4, AC-5: Errors returned to agent."""

    def test_code_step_error_returned_to_agent(self) -> None:
        """When code step raises exception, error is returned (not crashed)."""
        workflow_config = {
            "steps": [
                {
                    "name": "bad_code",
                    "type": "code",
                    "code": "raise ValueError('Intentional error')",
                    "on_failure": "fail",
                },
            ]
        }

        runner = WorkflowRunner(llm_provider=None)
        config = WorkflowConfig.from_dict(workflow_config)
        context: dict[str, Any] = {"agent_id": "test"}

        result = runner.run_workflow(config, context)

        assert result["success"] is False
        assert "error" in result or any(
            "error" in str(r) for r in result.get("step_results", [])
        )

    def test_llm_step_error_returned_to_agent(self) -> None:
        """When LLM step fails, error is returned to agent."""
        workflow_config = {
            "steps": [
                {
                    "name": "llm_call",
                    "type": "llm",
                    "prompt": "Do something",
                    "on_failure": "fail",
                },
            ]
        }

        # mock-ok: Testing error path
        mock_llm = MagicMock()
        mock_llm.generate.side_effect = Exception("LLM API error")

        runner = WorkflowRunner(llm_provider=mock_llm)
        config = WorkflowConfig.from_dict(workflow_config)
        context: dict[str, Any] = {"agent_id": "test"}

        result = runner.run_workflow(config, context)

        assert result["success"] is False


@pytest.mark.feature("agent_workflow")
class TestAgentFallbackWithoutWorkflow:
    """Test that agents without workflow fall back to propose_action."""

    def test_agent_without_workflow_uses_propose_action(self) -> None:
        """Agent with no workflow config falls back to legacy propose_action."""
        agent = Agent(
            agent_id="test_agent",
            llm_model="gemini/gemini-3-flash-preview",
            system_prompt="Test agent",
        )
        # No workflow config set

        assert agent.has_workflow is False

        # mock-ok: LLM calls are expensive
        mock_response = FlatActionResponse(
            reasoning="Legacy path",
            action=FlatAction(action_type="noop"),
        )
        agent.llm.generate = MagicMock(return_value=mock_response)

        world_state = {"tick": 1, "balances": {"test_agent": 100}, "artifacts": []}
        result = agent.run_workflow(world_state)

        # Should still succeed via fallback
        assert result["success"] is True
