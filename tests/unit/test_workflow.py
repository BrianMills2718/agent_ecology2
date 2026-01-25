"""Unit tests for agent workflow execution engine.

Tests for Plan #69: Agent Workflow Phase 1
Per ADR-0013: Configurable Agent Workflows
"""

from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock  # mock-ok: LLM calls expensive


class TestWorkflowStepExecution:
    """Tests for individual workflow step execution."""

    def test_code_step_executes(self) -> None:
        """Code step runs Python expression and returns result."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType

        step = WorkflowStep(
            name="test",
            step_type=StepType.CODE,
            code="result = 1 + 1",
        )
        runner = WorkflowRunner()
        context: dict[str, Any] = {}

        result = runner.execute_step(step, context)

        assert result["success"] is True
        assert context.get("result") == 2

    def test_code_step_sets_context(self) -> None:
        """Code step can modify context dict for subsequent steps."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType

        step = WorkflowStep(
            name="prepare",
            step_type=StepType.CODE,
            code="memories = ['learned trading', 'built artifact']",
        )
        runner = WorkflowRunner()
        context: dict[str, Any] = {}

        runner.execute_step(step, context)

        assert context["memories"] == ["learned trading", "built artifact"]

    def test_code_step_accesses_context(self) -> None:
        """Code step can read from existing context."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType

        step = WorkflowStep(
            name="compute",
            step_type=StepType.CODE,
            code="doubled = value * 2",
        )
        runner = WorkflowRunner()
        context: dict[str, Any] = {"value": 21}

        runner.execute_step(step, context)

        assert context["doubled"] == 42

    def test_code_step_error_returns_failure(self) -> None:
        """Code step that raises exception returns error result."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType

        step = WorkflowStep(
            name="bad",
            step_type=StepType.CODE,
            code="raise ValueError('intentional error')",
        )
        runner = WorkflowRunner()
        context: dict[str, Any] = {}

        result = runner.execute_step(step, context)

        assert result["success"] is False
        assert "error" in result
        assert "intentional error" in result["error"]


class TestLLMStepExecution:
    """Tests for LLM prompt step execution."""

    def test_llm_step_reads_prompt(self) -> None:
        """LLM step reads prompt content from provided source."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType

        step = WorkflowStep(
            name="think",
            step_type=StepType.LLM,
            prompt="What should I do next?",
        )
        # mock-ok: LLM calls are expensive, mock for unit test
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(
            reasoning="I should build something",
            action=MagicMock(model_dump=lambda: {"action_type": "noop"})
        )
        runner = WorkflowRunner(llm_provider=mock_llm)
        context: dict[str, Any] = {}

        result = runner.execute_step(step, context)

        assert result["success"] is True
        mock_llm.generate.assert_called_once()
        # Verify prompt was passed
        call_args = mock_llm.generate.call_args
        assert "What should I do next?" in call_args[0][0]

    def test_llm_step_with_context_interpolation(self) -> None:
        """LLM step interpolates context values into prompt."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType

        step = WorkflowStep(
            name="think",
            step_type=StepType.LLM,
            prompt="Agent {agent_id} has {balance} scrip. What next?",
        )
        # mock-ok: LLM calls are expensive
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(
            reasoning="Save money",
            action=MagicMock(model_dump=lambda: {"action_type": "noop"})
        )
        runner = WorkflowRunner(llm_provider=mock_llm)
        context: dict[str, Any] = {"agent_id": "alpha", "balance": 100}

        runner.execute_step(step, context)

        call_args = mock_llm.generate.call_args
        prompt = call_args[0][0]
        assert "Agent alpha" in prompt
        assert "100 scrip" in prompt

    def test_llm_step_stores_response_in_context(self) -> None:
        """LLM step stores response in context for subsequent steps."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType
        from src.agents.models import ActionResponse, WriteArtifactAction

        step = WorkflowStep(
            name="think",
            step_type=StepType.LLM,
            prompt="What should I do?",
        )
        # mock-ok: LLM calls are expensive
        mock_llm = MagicMock()
        # Create real response objects so model_dump works
        action = WriteArtifactAction(action_type="write_artifact", artifact_id="test", content="data")
        response = ActionResponse(reasoning="Build an artifact", action=action)
        mock_llm.generate.return_value = response
        runner = WorkflowRunner(llm_provider=mock_llm)
        context: dict[str, Any] = {}

        runner.execute_step(step, context)

        # Response stored under step name
        assert "think" in context
        assert context["think"]["reasoning"] == "Build an artifact"


class TestConditionalExecution:
    """Tests for conditional step execution (run_if)."""

    def test_run_if_condition_true(self) -> None:
        """Step runs when run_if condition evaluates to true."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType

        step = WorkflowStep(
            name="periodic",
            step_type=StepType.CODE,
            code="ran = True",
            run_if="tick % 10 == 0",
        )
        runner = WorkflowRunner()
        context: dict[str, Any] = {"tick": 10}

        result = runner.execute_step(step, context)

        assert result["success"] is True
        assert context.get("ran") is True

    def test_run_if_condition_false(self) -> None:
        """Step is skipped when run_if condition evaluates to false."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType

        step = WorkflowStep(
            name="periodic",
            step_type=StepType.CODE,
            code="ran = True",
            run_if="tick % 10 == 0",
        )
        runner = WorkflowRunner()
        context: dict[str, Any] = {"tick": 5}

        result = runner.execute_step(step, context)

        assert result["success"] is True
        assert result.get("skipped") is True
        assert "ran" not in context


class TestErrorHandling:
    """Tests for workflow error handling policies."""

    def test_error_retry_succeeds_on_second_attempt(self) -> None:
        """Step retries on failure and succeeds on second attempt."""
        from src.agents.workflow import (
            WorkflowRunner, WorkflowStep, StepType, ErrorPolicy
        )

        step = WorkflowStep(
            name="flaky",
            step_type=StepType.LLM,
            prompt="Do something",
            on_failure=ErrorPolicy.RETRY,
            max_retries=3,
        )
        # mock-ok: Testing retry logic
        mock_llm = MagicMock()
        # First call fails, second succeeds
        mock_llm.generate.side_effect = [
            Exception("Network error"),
            MagicMock(
                reasoning="Success",
                action=MagicMock(model_dump=lambda: {"action_type": "noop"})
            ),
        ]
        runner = WorkflowRunner(llm_provider=mock_llm)
        context: dict[str, Any] = {}

        result = runner.execute_step(step, context)

        assert result["success"] is True
        assert mock_llm.generate.call_count == 2

    def test_error_skip_continues_workflow(self) -> None:
        """Step with skip policy allows workflow to continue on failure."""
        from src.agents.workflow import (
            WorkflowRunner, WorkflowStep, StepType, ErrorPolicy
        )

        step = WorkflowStep(
            name="optional",
            step_type=StepType.CODE,
            code="raise RuntimeError('oops')",
            on_failure=ErrorPolicy.SKIP,
        )
        runner = WorkflowRunner()
        context: dict[str, Any] = {}

        result = runner.execute_step(step, context)

        assert result["success"] is False
        assert result.get("skipped_due_to_error") is True
        assert "error" in result

    def test_error_fail_stops_workflow(self) -> None:
        """Step with fail policy stops workflow execution."""
        from src.agents.workflow import (
            WorkflowRunner, WorkflowStep, StepType, ErrorPolicy
        )

        step = WorkflowStep(
            name="critical",
            step_type=StepType.CODE,
            code="raise RuntimeError('critical failure')",
            on_failure=ErrorPolicy.FAIL,
        )
        runner = WorkflowRunner()
        context: dict[str, Any] = {}

        result = runner.execute_step(step, context)

        assert result["success"] is False
        assert result.get("workflow_should_stop") is True


class TestWorkflowExecution:
    """Tests for full workflow execution."""

    def test_empty_workflow_completes(self) -> None:
        """Empty workflow completes without error."""
        from src.agents.workflow import WorkflowRunner, WorkflowConfig

        config = WorkflowConfig(steps=[])
        runner = WorkflowRunner()

        result = runner.run_workflow(config, context={})

        assert result["success"] is True
        assert result.get("action") is None

    def test_sequential_steps_execute_in_order(self) -> None:
        """Workflow steps execute in defined order."""
        from src.agents.workflow import (
            WorkflowRunner, WorkflowConfig, WorkflowStep, StepType
        )

        steps = [
            WorkflowStep(name="first", step_type=StepType.CODE, code="order.append(1)"),
            WorkflowStep(name="second", step_type=StepType.CODE, code="order.append(2)"),
            WorkflowStep(name="third", step_type=StepType.CODE, code="order.append(3)"),
        ]
        config = WorkflowConfig(steps=steps)
        runner = WorkflowRunner()
        context: dict[str, Any] = {"order": []}

        runner.run_workflow(config, context)

        assert context["order"] == [1, 2, 3]

    def test_workflow_returns_final_action(self) -> None:
        """Workflow returns action from last LLM step."""
        from src.agents.workflow import (
            WorkflowRunner, WorkflowConfig, WorkflowStep, StepType
        )
        from src.agents.models import ActionResponse, ReadArtifactAction

        steps = [
            WorkflowStep(name="prepare", step_type=StepType.CODE, code="ready = True"),
            WorkflowStep(name="decide", step_type=StepType.LLM, prompt="What action?"),
        ]
        config = WorkflowConfig(steps=steps)
        # mock-ok: Testing workflow integration
        mock_llm = MagicMock()
        # Create real response objects so model_dump works
        action = ReadArtifactAction(action_type="read_artifact", artifact_id="test")
        response = ActionResponse(reasoning="I should read", action=action)
        mock_llm.generate.return_value = response
        runner = WorkflowRunner(llm_provider=mock_llm)

        result = runner.run_workflow(config, context={})

        assert result["success"] is True
        assert result["action"]["action_type"] == "read_artifact"

    def test_workflow_stops_on_critical_error(self) -> None:
        """Workflow stops when step with FAIL policy errors."""
        from src.agents.workflow import (
            WorkflowRunner, WorkflowConfig, WorkflowStep, StepType, ErrorPolicy
        )

        steps = [
            WorkflowStep(name="first", step_type=StepType.CODE, code="order.append(1)"),
            WorkflowStep(
                name="critical",
                step_type=StepType.CODE,
                code="raise RuntimeError('stop')",
                on_failure=ErrorPolicy.FAIL
            ),
            WorkflowStep(name="never", step_type=StepType.CODE, code="order.append(3)"),
        ]
        config = WorkflowConfig(steps=steps)
        runner = WorkflowRunner()
        context: dict[str, Any] = {"order": []}

        result = runner.run_workflow(config, context)

        assert result["success"] is False
        assert context["order"] == [1]  # Third step never ran


class TestWorkflowConfig:
    """Tests for workflow configuration parsing."""

    def test_parse_workflow_from_dict(self) -> None:
        """WorkflowConfig can be created from dict (YAML-like structure)."""
        from src.agents.workflow import WorkflowConfig, StepType

        config_dict = {
            "steps": [
                {"name": "think", "type": "llm", "prompt": "What to do?"},
                {"name": "act", "type": "llm", "prompt": "Execute action"},
            ],
            "error_handling": {
                "default_on_failure": "retry",
                "max_retries": 3,
            },
        }

        config = WorkflowConfig.from_dict(config_dict)

        assert len(config.steps) == 2
        assert config.steps[0].name == "think"
        assert config.steps[0].step_type == StepType.LLM
        assert config.default_on_failure.value == "retry"

    def test_parse_code_step_from_dict(self) -> None:
        """Code step parsed correctly from dict."""
        from src.agents.workflow import WorkflowConfig, StepType

        config_dict = {
            "steps": [
                {
                    "name": "prepare",
                    "type": "code",
                    "code": "memories = search_memory(goal)",
                    "run_if": "tick > 1",
                },
            ],
        }

        config = WorkflowConfig.from_dict(config_dict)

        step = config.steps[0]
        assert step.step_type == StepType.CODE
        assert step.code == "memories = search_memory(goal)"
        assert step.run_if == "tick > 1"


class TestTransitionEvaluation:
    """Tests for Plan #157 Phase 4: LLM-Informed State Transitions."""

    def test_evaluate_transition_with_llm(self) -> None:
        """Transition evaluation calls LLM and returns decision."""
        from src.agents.workflow import WorkflowRunner
        from src.agents.models import TransitionEvaluationResponse

        # mock-ok: LLM calls are expensive
        mock_llm = MagicMock()
        mock_llm.generate.return_value = TransitionEvaluationResponse(
            decision="pivot",
            reasoning="Stuck on same artifact for 5 attempts",
            next_focus="Try building a simpler utility"
        )

        runner = WorkflowRunner(llm_provider=mock_llm)
        context = {
            "time_remaining": "1m 30s",
            "success_rate": "2/10",
            "revenue_earned": 0.0,
            "action_history": "1. write_artifact(tool) -> FAILED\n2. write_artifact(tool) -> FAILED",
            "last_action_result": "Error: Invalid syntax",
        }

        result = runner.evaluate_transition(context)

        assert result["success"] is True
        assert result["decision"] == "pivot"
        assert "Stuck" in result["reasoning"]
        assert result["next_focus"] == "Try building a simpler utility"
        mock_llm.generate.assert_called_once()

    def test_evaluate_transition_fallback_without_llm(self) -> None:
        """Transition evaluation uses fallback heuristics when no LLM."""
        from src.agents.workflow import WorkflowRunner

        runner = WorkflowRunner()  # No LLM provider
        context = {
            "action_history": "1. write_artifact(tool)\n2. write_artifact(tool)\n3. write_artifact(tool)",
            "failed_actions": 3,
            "successful_actions": 0,
            "actions_taken": 3,
        }

        result = runner.evaluate_transition(context)

        assert result["success"] is True
        assert result["decision"] == "pivot"
        assert "Repeated" in result["reasoning"]

    def test_evaluate_transition_continue_on_success(self) -> None:
        """Fallback returns continue when recent actions successful."""
        from src.agents.workflow import WorkflowRunner

        runner = WorkflowRunner()  # No LLM provider
        context = {
            "action_history": "1. write_artifact(tool1)\n2. read_artifact(doc)\n3. invoke_artifact(helper)",
            "failed_actions": 0,
            "successful_actions": 3,
            "actions_taken": 3,
        }

        result = runner.evaluate_transition(context)

        assert result["success"] is True
        # With all successes and no failures, we ship (good time to capture value)
        assert result["decision"] == "ship"

    def test_transition_step_executes_and_maps_state(self) -> None:
        """Transition step evaluates and maps decision to state transition."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType
        from src.agents.state_machine import WorkflowStateMachine, StateConfig
        from src.agents.models import TransitionEvaluationResponse

        # Create state machine with reflecting state
        state_config = StateConfig(
            states=["reflecting", "implementing", "observing", "shipping"],
            initial_state="reflecting",
            transitions=[],  # Allow any transition in permissive mode
        )
        state_machine = WorkflowStateMachine(state_config)

        # Create transition step with map
        step = WorkflowStep(
            name="decide",
            step_type=StepType.TRANSITION,
            prompt="Should you continue, pivot, or ship?",
            transition_map={
                "continue": "implementing",
                "pivot": "observing",
                "ship": "shipping",
            },
        )

        # mock-ok: LLM calls are expensive
        mock_llm = MagicMock()
        mock_llm.generate.return_value = TransitionEvaluationResponse(
            decision="ship",
            reasoning="Artifact works, move on",
            next_focus=""
        )

        runner = WorkflowRunner(llm_provider=mock_llm)
        context: dict[str, Any] = {
            "time_remaining": "30s",
            "success_rate": "5/5",
            "revenue_earned": 10.0,
            "action_history": "(none)",
            "last_action_result": "Success",
        }

        result = runner.execute_step(step, context, state_machine)

        assert result["success"] is True
        assert result["decision"] == "ship"
        assert state_machine.current_state == "shipping"
        assert result["state_transition"]["to"] == "shipping"
        assert result["state_transition"]["success"] is True

    def test_transition_step_stores_result_in_context(self) -> None:
        """Transition step stores decision in context for subsequent steps."""
        from src.agents.workflow import WorkflowRunner, WorkflowStep, StepType
        from src.agents.models import TransitionEvaluationResponse

        step = WorkflowStep(
            name="reflect_decision",
            step_type=StepType.TRANSITION,
        )

        # mock-ok: LLM calls are expensive
        mock_llm = MagicMock()
        mock_llm.generate.return_value = TransitionEvaluationResponse(
            decision="continue",
            reasoning="Making good progress",
            next_focus=""
        )

        runner = WorkflowRunner(llm_provider=mock_llm)
        context: dict[str, Any] = {}

        runner.execute_step(step, context)

        assert "reflect_decision" in context
        assert context["reflect_decision"]["decision"] == "continue"
        assert context["reflect_decision"]["reasoning"] == "Making good progress"

    def test_parse_transition_step_from_dict(self) -> None:
        """Transition step parsed correctly from YAML-like dict."""
        from src.agents.workflow import WorkflowConfig, StepType

        config_dict = {
            "steps": [
                {
                    "name": "strategic_reflect",
                    "type": "transition",
                    "in_state": "reflecting",
                    "prompt": "Should you continue, pivot, or ship?",
                    "transition_map": {
                        "continue": "implementing",
                        "pivot": "observing",
                        "ship": "shipping",
                    },
                },
            ],
        }

        config = WorkflowConfig.from_dict(config_dict)

        step = config.steps[0]
        assert step.step_type == StepType.TRANSITION
        assert step.name == "strategic_reflect"
        assert step.in_state == ["reflecting"]
        assert step.transition_map == {
            "continue": "implementing",
            "pivot": "observing",
            "ship": "shipping",
        }


class TestTransitionEvaluationResponse:
    """Tests for TransitionEvaluationResponse model."""

    def test_valid_decisions(self) -> None:
        """Model accepts valid decision values."""
        from src.agents.models import TransitionEvaluationResponse

        for decision in ["continue", "pivot", "ship"]:
            response = TransitionEvaluationResponse(
                decision=decision,  # type: ignore
                reasoning="Test reasoning"
            )
            assert response.decision == decision

    def test_next_focus_optional(self) -> None:
        """next_focus field is optional with empty default."""
        from src.agents.models import TransitionEvaluationResponse

        response = TransitionEvaluationResponse(
            decision="continue",
            reasoning="Keep going"
        )
        assert response.next_focus == ""


class TestWorkflowArtifacts:
    """Tests for Plan #146 Phase 3: Workflow Artifact Support."""

    def test_workflow_step_with_prompt_artifact_id(self) -> None:
        """WorkflowStep can reference a prompt artifact instead of inline prompt."""
        from src.agents.workflow import WorkflowStep, StepType

        step = WorkflowStep(
            name="decide",
            step_type=StepType.LLM,
            prompt_artifact_id="alice_observe_prompt",
        )

        assert step.prompt_artifact_id == "alice_observe_prompt"
        assert step.prompt is None

    def test_workflow_step_allows_either_prompt_or_artifact(self) -> None:
        """WorkflowStep accepts either inline prompt or prompt_artifact_id."""
        from src.agents.workflow import WorkflowStep, StepType

        # Inline prompt
        step1 = WorkflowStep(
            name="inline",
            step_type=StepType.LLM,
            prompt="What should I do?",
        )
        assert step1.prompt == "What should I do?"
        assert step1.prompt_artifact_id is None

        # Artifact reference
        step2 = WorkflowStep(
            name="artifact",
            step_type=StepType.LLM,
            prompt_artifact_id="genesis_prompt_library#observe_base",
        )
        assert step2.prompt is None
        assert step2.prompt_artifact_id == "genesis_prompt_library#observe_base"

    def test_workflow_step_requires_prompt_or_artifact_for_llm(self) -> None:
        """LLM step requires either prompt or prompt_artifact_id."""
        from src.agents.workflow import WorkflowStep, StepType

        with pytest.raises(ValueError, match="requires 'prompt' or 'prompt_artifact_id'"):
            WorkflowStep(
                name="invalid",
                step_type=StepType.LLM,
                # Neither prompt nor prompt_artifact_id specified
            )

    def test_workflow_step_transition_mode(self) -> None:
        """WorkflowStep supports transition_mode field."""
        from src.agents.workflow import WorkflowStep, StepType

        step = WorkflowStep(
            name="observe",
            step_type=StepType.LLM,
            prompt="Observe the environment",
            transition_mode="llm",
            transition_prompt_artifact_id="alice_transition_prompt",
        )

        assert step.transition_mode == "llm"
        assert step.transition_prompt_artifact_id == "alice_transition_prompt"

    def test_parse_prompt_artifact_id_from_dict(self) -> None:
        """prompt_artifact_id parsed correctly from YAML-like dict."""
        from src.agents.workflow import WorkflowConfig, StepType

        config_dict = {
            "steps": [
                {
                    "name": "observe",
                    "type": "llm",
                    "prompt_artifact_id": "alice_observe_prompt",
                },
            ],
        }

        config = WorkflowConfig.from_dict(config_dict)

        step = config.steps[0]
        assert step.step_type == StepType.LLM
        assert step.prompt_artifact_id == "alice_observe_prompt"
        assert step.prompt is None

    def test_parse_transition_mode_from_dict(self) -> None:
        """transition_mode and transition_prompt_artifact_id parsed from dict."""
        from src.agents.workflow import WorkflowConfig

        config_dict = {
            "steps": [
                {
                    "name": "decide_state",
                    "type": "llm",
                    "prompt": "What next?",
                    "transition_mode": "llm",
                    "transition_prompt_artifact_id": "alice_transition_prompt",
                },
            ],
        }

        config = WorkflowConfig.from_dict(config_dict)

        step = config.steps[0]
        assert step.transition_mode == "llm"
        assert step.transition_prompt_artifact_id == "alice_transition_prompt"

    def test_parse_invalid_transition_mode_ignored(self) -> None:
        """Invalid transition_mode values are ignored (set to None)."""
        from src.agents.workflow import WorkflowConfig

        config_dict = {
            "steps": [
                {
                    "name": "decide",
                    "type": "llm",
                    "prompt": "What?",
                    "transition_mode": "invalid_mode",  # Not llm, condition, or auto
                },
            ],
        }

        config = WorkflowConfig.from_dict(config_dict)

        step = config.steps[0]
        assert step.transition_mode is None

    def test_parse_valid_transition_modes(self) -> None:
        """All valid transition modes are parsed correctly."""
        from src.agents.workflow import WorkflowConfig

        for mode in ["llm", "condition", "auto"]:
            config_dict = {
                "steps": [
                    {
                        "name": f"step_{mode}",
                        "type": "llm",
                        "prompt": "Test",
                        "transition_mode": mode,
                    },
                ],
            }

            config = WorkflowConfig.from_dict(config_dict)
            assert config.steps[0].transition_mode == mode


class TestAgentWorkflowArtifactField:
    """Tests for Plan #146 Phase 3: Agent workflow_artifact_id field."""

    def test_agent_workflow_artifact_id_default_none(self) -> None:
        """Agent workflow_artifact_id defaults to None."""
        from src.agents.agent import Agent

        agent = Agent(agent_id="test_agent")

        assert agent.workflow_artifact_id is None
        assert agent.has_workflow_artifact is False

    def test_agent_workflow_artifact_id_setter(self) -> None:
        """Agent workflow_artifact_id can be set."""
        from src.agents.agent import Agent

        agent = Agent(agent_id="test_agent")

        agent.workflow_artifact_id = "alice_workflow"

        assert agent.workflow_artifact_id == "alice_workflow"
        assert agent.has_workflow_artifact is True

    def test_agent_workflow_artifact_id_from_config(self) -> None:
        """Agent loads workflow_artifact_id from artifact config."""
        import json
        from datetime import datetime, timezone
        from src.agents.agent import Agent
        from src.world.artifacts import Artifact

        now = datetime.now(timezone.utc).isoformat()
        # Create an artifact with workflow_artifact_id in config
        # Agent artifacts need has_standing=True and can_execute=True
        artifact = Artifact(
            id="test_artifact",
            type="agent",
            content=json.dumps({
                "agent_id": "alice",
                "workflow_artifact_id": "alice_workflow",
                "llm_model": "gpt-4",
            }),
            created_by="genesis",
            created_at=now,
            updated_at=now,
            has_standing=True,
            can_execute=True,
        )

        agent = Agent.from_artifact(artifact)

        assert agent.workflow_artifact_id == "alice_workflow"
        assert agent.has_workflow_artifact is True
