"""Tests for Plan #188: Agent Planning Pattern.

Tests deliberative planning where agents write explicit plans before executing.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.agents.planning import (
    Plan,
    PlanStep,
    PlanStatus,
    get_plan_artifact_id,
    create_plan_generation_prompt,
    step_to_action,
)


class TestPlanDataStructures:
    """Tests for Plan and PlanStep data structures."""

    def test_plan_step_creation(self) -> None:
        """Test PlanStep can be created with all fields."""
        step = PlanStep(
            order=1,
            action_type="invoke_artifact",
            target="genesis_mint",
            method="submit",
            args=["my_artifact"],
            rationale="Submit artifact for scoring",
        )
        assert step.order == 1
        assert step.action_type == "invoke_artifact"
        assert step.target == "genesis_mint"
        assert step.method == "submit"
        assert step.args == ["my_artifact"]
        assert step.rationale == "Submit artifact for scoring"

    def test_plan_creation(self) -> None:
        """Test Plan can be created with steps."""
        steps = [
            PlanStep(order=1, action_type="read_artifact", target="genesis_store"),
            PlanStep(order=2, action_type="write_artifact", target="my_tool"),
        ]
        plan = Plan(
            goal="Build a useful tool",
            approach="Iterative development",
            confidence=0.8,
            steps=steps,
        )
        assert plan.goal == "Build a useful tool"
        assert plan.confidence == 0.8
        assert len(plan.steps) == 2
        assert plan.status == PlanStatus.IN_PROGRESS
        assert plan.current_step == 1

    def test_plan_to_dict(self) -> None:
        """Test Plan serializes to dict correctly."""
        plan = Plan(
            goal="Test goal",
            approach="Test approach",
            confidence=0.9,
            steps=[PlanStep(order=1, action_type="noop", rationale="Testing")],
        )
        data = plan.to_dict()
        assert data["plan"]["goal"] == "Test goal"
        assert data["plan"]["confidence"] == 0.9
        assert data["execution"]["status"] == "in_progress"
        assert data["execution"]["current_step"] == 1

    def test_plan_from_dict(self) -> None:
        """Test Plan deserializes from dict correctly."""
        data = {
            "plan": {
                "goal": "From dict goal",
                "approach": "From dict approach",
                "confidence": 0.7,
                "steps": [
                    {"order": 1, "action_type": "read_artifact", "target": "test"}
                ],
                "fallback": {},
            },
            "execution": {
                "current_step": 1,
                "completed_steps": [],
                "status": "in_progress",
            },
        }
        plan = Plan.from_dict(data)
        assert plan.goal == "From dict goal"
        assert plan.confidence == 0.7
        assert len(plan.steps) == 1
        assert plan.steps[0].target == "test"

    def test_plan_roundtrip(self) -> None:
        """Test Plan serializes and deserializes correctly."""
        original = Plan(
            goal="Roundtrip test",
            approach="Full cycle",
            confidence=0.85,
            steps=[
                PlanStep(order=1, action_type="read_artifact", target="a"),
                PlanStep(order=2, action_type="invoke_artifact", target="b", method="run"),
            ],
            fallback={"if_step_1_fails": "Try alternative"},
        )
        data = original.to_dict()
        restored = Plan.from_dict(data)
        assert restored.goal == original.goal
        assert restored.confidence == original.confidence
        assert len(restored.steps) == len(original.steps)
        assert restored.fallback == original.fallback


class TestPlanExecution:
    """Tests for plan step execution and state management."""

    def test_get_current_step(self) -> None:
        """Test getting current step to execute."""
        plan = Plan(
            goal="Test",
            approach="Test",
            confidence=0.5,
            steps=[
                PlanStep(order=1, action_type="read_artifact"),
                PlanStep(order=2, action_type="write_artifact"),
            ],
        )
        step = plan.get_current_step()
        assert step is not None
        assert step.order == 1

    def test_get_current_step_none_when_completed(self) -> None:
        """Test get_current_step returns None when plan is completed."""
        plan = Plan(
            goal="Test",
            approach="Test",
            confidence=0.5,
            steps=[PlanStep(order=1, action_type="noop")],
            status=PlanStatus.COMPLETED,
        )
        assert plan.get_current_step() is None

    def test_mark_step_completed_advances(self) -> None:
        """Test marking step as completed advances to next step."""
        plan = Plan(
            goal="Test",
            approach="Test",
            confidence=0.5,
            steps=[
                PlanStep(order=1, action_type="read_artifact"),
                PlanStep(order=2, action_type="write_artifact"),
            ],
        )
        plan.mark_step_completed(1)
        assert 1 in plan.completed_steps
        assert plan.current_step == 2
        assert plan.status == PlanStatus.IN_PROGRESS

    def test_mark_last_step_completed_completes_plan(self) -> None:
        """Test marking last step as completed completes the plan."""
        plan = Plan(
            goal="Test",
            approach="Test",
            confidence=0.5,
            steps=[
                PlanStep(order=1, action_type="read_artifact"),
                PlanStep(order=2, action_type="write_artifact"),
            ],
        )
        plan.mark_step_completed(1)
        plan.mark_step_completed(2)
        assert plan.status == PlanStatus.COMPLETED

    def test_mark_step_failed(self) -> None:
        """Test marking step as failed sets plan status."""
        plan = Plan(
            goal="Test",
            approach="Test",
            confidence=0.5,
            steps=[PlanStep(order=1, action_type="noop")],
        )
        plan.mark_step_failed(1)
        assert plan.status == PlanStatus.FAILED


class TestStepToAction:
    """Tests for converting plan steps to action dicts."""

    def test_read_artifact_step(self) -> None:
        """Test read_artifact step conversion."""
        step = PlanStep(order=1, action_type="read_artifact", target="my_artifact")
        action = step_to_action(step)
        assert action["action_type"] == "read_artifact"
        assert action["artifact_id"] == "my_artifact"

    def test_invoke_artifact_step(self) -> None:
        """Test invoke_artifact step conversion."""
        step = PlanStep(
            order=1,
            action_type="invoke_artifact",
            target="genesis_mint",
            method="submit",
            args=["artifact_id"],
        )
        action = step_to_action(step)
        assert action["action_type"] == "invoke_artifact"
        assert action["artifact_id"] == "genesis_mint"
        assert action["method"] == "submit"
        assert action["args"] == ["artifact_id"]

    def test_transfer_scrip_step(self) -> None:
        """Test transfer_scrip step conversion."""
        step = PlanStep(
            order=1,
            action_type="transfer_scrip",
            target="other_agent",
            args=[50],
        )
        action = step_to_action(step)
        assert action["action_type"] == "transfer_scrip"
        assert action["to_id"] == "other_agent"
        assert action["amount"] == 50


class TestPlanArtifactId:
    """Tests for plan artifact ID generation."""

    def test_get_plan_artifact_id(self) -> None:
        """Test plan artifact ID format."""
        assert get_plan_artifact_id("alpha_3") == "alpha_3_plan"
        assert get_plan_artifact_id("my_agent") == "my_agent_plan"


class TestPlanGenerationPrompt:
    """Tests for plan generation prompt creation."""

    def test_prompt_includes_agent_id(self) -> None:
        """Test prompt includes agent ID."""
        prompt = create_plan_generation_prompt("alpha_3", {}, 5)
        assert "alpha_3" in prompt

    def test_prompt_includes_max_steps(self) -> None:
        """Test prompt mentions max steps."""
        prompt = create_plan_generation_prompt("alpha_3", {}, 3)
        assert "3 or fewer" in prompt

    def test_prompt_includes_action_types(self) -> None:
        """Test prompt lists available action types."""
        prompt = create_plan_generation_prompt("alpha_3", {}, 5)
        assert "read_artifact" in prompt
        assert "write_artifact" in prompt
        assert "invoke_artifact" in prompt


class TestPlanningConfig:
    """Tests for planning configuration."""

    def test_planning_config_defaults(self) -> None:
        """Test PlanningConfig has correct defaults."""
        from src.config_schema import PlanningConfig

        config = PlanningConfig()
        assert config.enabled is False
        assert config.max_steps == 5
        assert config.replan_on_failure is True

    def test_planning_config_validation(self) -> None:
        """Test PlanningConfig validates max_steps range."""
        from src.config_schema import PlanningConfig
        from pydantic import ValidationError

        # Valid range
        config = PlanningConfig(max_steps=10)
        assert config.max_steps == 10

        # Below minimum
        with pytest.raises(ValidationError):
            PlanningConfig(max_steps=0)

        # Above maximum
        with pytest.raises(ValidationError):
            PlanningConfig(max_steps=25)
