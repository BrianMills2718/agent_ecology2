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
            thought_process="I should build something",
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
            thought_process="Save money",
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
        response = ActionResponse(thought_process="Build an artifact", action=action)
        mock_llm.generate.return_value = response
        runner = WorkflowRunner(llm_provider=mock_llm)
        context: dict[str, Any] = {}

        runner.execute_step(step, context)

        # Response stored under step name
        assert "think" in context
        assert context["think"]["thought_process"] == "Build an artifact"


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
                thought_process="Success",
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
        response = ActionResponse(thought_process="I should read", action=action)
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
