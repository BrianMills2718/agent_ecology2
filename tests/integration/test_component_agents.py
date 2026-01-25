"""Integration tests for prompt component system (Plan #150).

Tests the full component injection path: Agent config -> ComponentRegistry -> Workflow.
Verifies that components specified in agent.yaml get injected into workflow prompts.

Run with: pytest tests/integration/test_component_agents.py -v
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

from src.agents.agent import Agent
from src.agents.loader import load_agents
from src.agents.component_loader import (
    ComponentRegistry,
    load_agent_components,
    inject_components_into_workflow,
)
from src.agents.models import FlatActionResponse, FlatAction


@pytest.mark.plans([150])
class TestAgentWithComponentsLoads:
    """Test that agents with components configuration load successfully."""

    def test_agent_with_components_loads(self) -> None:
        """Agent with components loads successfully."""
        # Load agents from actual config (alpha_3 has components)
        agents = load_agents()

        # Find alpha_3 which has components configured
        alpha_3_config = None
        for agent in agents:
            if agent["id"] == "alpha_3":
                alpha_3_config = agent
                break

        # alpha_3 should have components
        assert alpha_3_config is not None, "alpha_3 agent not found"
        assert "components" in alpha_3_config
        assert "traits" in alpha_3_config["components"]
        assert "buy_before_build" in alpha_3_config["components"]["traits"]

    def test_agent_without_components_loads(self) -> None:
        """Agent without components loads without error."""
        # Create an agent without components
        agent = Agent(
            agent_id="no_components",
            llm_model="gemini/gemini-3-flash-preview",
            system_prompt="Test agent without components",
        )

        # Should not have workflow with components
        assert agent._workflow_config is None or "components" not in (agent._workflow_config or {})


@pytest.mark.plans([150])
class TestTraitChangesPrompt:
    """Test that trait components actually modify prompt text."""

    def test_trait_changes_prompt(self, tmp_path: Path) -> None:
        """Trait actually modifies prompt text."""
        # Create a test component
        traits_dir = tmp_path / "traits"
        traits_dir.mkdir()
        (traits_dir / "test_trait.yaml").write_text(
            yaml.dump({
                "name": "test_trait",
                "type": "trait",
                "inject_into": ["observe"],
                "prompt_fragment": "\nTEST_MARKER: Check the store first!",
            })
        )

        # Load the component
        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()

        # Create a workflow with an observe step
        workflow = {
            "steps": [
                {
                    "name": "observe",
                    "type": "llm",
                    "prompt": "=== OBSERVE ===\nLook around.",
                },
            ]
        }

        # Inject the trait
        traits = registry.get_traits(["test_trait"])
        result = inject_components_into_workflow(workflow, traits=traits)

        # Verify the prompt was modified
        assert "TEST_MARKER" in result["steps"][0]["prompt"]
        assert "Check the store first!" in result["steps"][0]["prompt"]
        # Original content still present
        assert "Look around." in result["steps"][0]["prompt"]

    def test_multiple_traits_all_inject(self, tmp_path: Path) -> None:
        """Multiple traits all inject into matching steps."""
        traits_dir = tmp_path / "traits"
        traits_dir.mkdir()

        (traits_dir / "trait_a.yaml").write_text(
            yaml.dump({
                "name": "trait_a",
                "type": "trait",
                "inject_into": ["ideate"],
                "prompt_fragment": "\nTRAIT_A_CONTENT",
            })
        )

        (traits_dir / "trait_b.yaml").write_text(
            yaml.dump({
                "name": "trait_b",
                "type": "trait",
                "inject_into": ["ideate"],
                "prompt_fragment": "\nTRAIT_B_CONTENT",
            })
        )

        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()

        workflow = {
            "steps": [
                {
                    "name": "ideate",
                    "type": "llm",
                    "prompt": "=== IDEATE ===\nGenerate ideas.",
                },
            ]
        }

        traits = registry.get_traits(["trait_a", "trait_b"])
        result = inject_components_into_workflow(workflow, traits=traits)

        # Both traits should be present
        prompt = result["steps"][0]["prompt"]
        assert "TRAIT_A_CONTENT" in prompt
        assert "TRAIT_B_CONTENT" in prompt


@pytest.mark.plans([150])
class TestRealComponentFiles:
    """Test the actual component files in _components directory."""

    def test_buy_before_build_trait_exists(self) -> None:
        """buy_before_build trait exists and has correct structure."""
        registry = ComponentRegistry()
        registry.load_all()

        trait = registry.get_trait("buy_before_build")
        assert trait is not None
        assert "ideate" in trait.inject_into or "observe" in trait.inject_into
        assert len(trait.prompt_fragment) > 0

    def test_economic_participant_trait_exists(self) -> None:
        """economic_participant trait exists and has correct structure."""
        registry = ComponentRegistry()
        registry.load_all()

        trait = registry.get_trait("economic_participant")
        assert trait is not None
        assert len(trait.prompt_fragment) > 0

    def test_facilitate_transactions_goal_exists(self) -> None:
        """facilitate_transactions goal exists and has correct structure."""
        registry = ComponentRegistry()
        registry.load_all()

        goal = registry.get_goal("facilitate_transactions")
        assert goal is not None
        assert len(goal.prompt_fragment) > 0


@pytest.mark.plans([150])
class TestComponentWorkflowIntegration:
    """Test component integration with workflow runner."""

    def test_agent_workflow_with_injected_components(self, tmp_path: Path) -> None:
        """Agent workflow uses components when configured."""
        # Create test component
        traits_dir = tmp_path / "traits"
        traits_dir.mkdir()
        (traits_dir / "injected.yaml").write_text(
            yaml.dump({
                "name": "injected",
                "type": "trait",
                "inject_into": ["decide"],
                "prompt_fragment": "\nINJECTED_COMPONENT_TEXT",
            })
        )

        registry = ComponentRegistry(components_dir=tmp_path)
        registry.load_all()

        # Create workflow and inject components
        workflow_config = {
            "steps": [
                {
                    "name": "decide",
                    "type": "llm",
                    "prompt": "Make a decision.",
                },
            ]
        }

        traits = registry.get_traits(["injected"])
        modified_workflow = inject_components_into_workflow(workflow_config, traits=traits)

        # Create agent with modified workflow
        agent = Agent(
            agent_id="test_agent",
            llm_model="gemini/gemini-3-flash-preview",
            system_prompt="Test agent",
        )
        agent._workflow_config = modified_workflow

        # mock-ok: LLM calls are expensive, mock for integration test
        mock_response = FlatActionResponse(
            reasoning="Testing",
            action=FlatAction(action_type="noop"),
        )
        agent.llm.generate = MagicMock(return_value=mock_response)

        # Execute workflow
        world_state = {"event_number": 1, "balances": {"test_agent": 100}, "artifacts": []}
        result = agent.run_workflow(world_state)

        assert result["success"] is True

        # Verify the injected text was part of the prompt sent to LLM
        call_args = agent.llm.generate.call_args
        if call_args:
            prompt = call_args[0][0] if call_args[0] else ""
            assert "INJECTED_COMPONENT_TEXT" in prompt
