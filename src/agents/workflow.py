"""Configurable agent workflow execution engine.

Implements ADR-0013: Configurable Agent Workflows (Phase 1).

Workflows are ordered lists of steps that execute sequentially. Each step
can be either a code step (Python expression) or an LLM step (prompt).

Extended with state machine support (Plan #82) for VSM-aligned agents:
- States define distinct operational modes (e.g., "planning", "executing")
- Transitions validate state changes
- Steps can be conditional on current state

Usage:
    from src.agents.workflow import WorkflowRunner, WorkflowConfig

    config = WorkflowConfig.from_dict(agent_workflow_config)
    runner = WorkflowRunner(llm_provider=agent.llm)
    result = runner.run_workflow(config, context={"agent_id": "alpha", ...})

    if result["success"]:
        action = result["action"]  # Action to execute
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

from src.agents.safe_eval import SafeExpressionError, safe_eval_condition

if TYPE_CHECKING:
    from llm_provider import LLMProvider

from .state_machine import StateConfig, WorkflowStateMachine

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """Type of workflow step."""

    CODE = "code"
    LLM = "llm"


class ErrorPolicy(str, Enum):
    """How to handle step errors."""

    RETRY = "retry"  # Retry the step
    SKIP = "skip"  # Skip and continue workflow
    FAIL = "fail"  # Stop workflow execution


@dataclass
class WorkflowStep:
    """A single step in a workflow.

    Attributes:
        name: Unique name for this step (used for context storage)
        step_type: Type of step (code or llm)
        code: Python code to execute (for code steps)
        prompt: Prompt text or template (for llm steps)
        run_if: Optional condition - step only runs if this evaluates to True
        on_failure: Error handling policy for this step
        max_retries: Maximum retry attempts (for RETRY policy)
        in_state: Only run if state machine is in one of these states
        transition_to: Transition to this state after step completes
    """

    name: str
    step_type: StepType
    code: str | None = None
    prompt: str | None = None
    run_if: str | None = None
    on_failure: ErrorPolicy = ErrorPolicy.FAIL
    max_retries: int = 3
    in_state: list[str] | None = None  # State condition
    transition_to: str | None = None  # State to transition to after step

    def __post_init__(self) -> None:
        """Validate step configuration."""
        if self.step_type == StepType.CODE and not self.code:
            raise ValueError(f"Code step '{self.name}' requires 'code' field")
        if self.step_type == StepType.LLM and not self.prompt:
            raise ValueError(f"LLM step '{self.name}' requires 'prompt' field")


@dataclass
class WorkflowConfig:
    """Configuration for a complete workflow.

    Attributes:
        steps: Ordered list of steps to execute
        default_on_failure: Default error policy for steps without explicit policy
        default_max_retries: Default max retries for steps with RETRY policy
        state_machine: Optional state machine configuration
    """

    steps: list[WorkflowStep] = field(default_factory=list)
    default_on_failure: ErrorPolicy = ErrorPolicy.RETRY
    default_max_retries: int = 3
    state_machine: StateConfig | None = None

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> WorkflowConfig:
        """Create WorkflowConfig from dictionary (e.g., parsed YAML).

        Args:
            config: Dictionary with workflow configuration

        Returns:
            WorkflowConfig instance
        """
        # Parse error handling defaults
        error_handling = config.get("error_handling", {})
        default_on_failure_str = error_handling.get("default_on_failure", "retry")
        default_on_failure = ErrorPolicy(default_on_failure_str)
        default_max_retries = error_handling.get("max_retries", 3)

        # Parse state machine config if present
        state_machine: StateConfig | None = None
        if "state_machine" in config:
            state_machine = StateConfig.from_dict(config["state_machine"])

        # Parse steps
        steps: list[WorkflowStep] = []
        for step_dict in config.get("steps", []):
            step_type = StepType(step_dict.get("type", "code"))

            # Get error policy for this step
            on_failure_str = step_dict.get("on_failure", default_on_failure_str)
            on_failure = ErrorPolicy(on_failure_str)

            # Parse state conditions
            in_state = step_dict.get("in_state")
            if isinstance(in_state, str):
                in_state = [in_state]  # Single state -> list

            step = WorkflowStep(
                name=step_dict["name"],
                step_type=step_type,
                code=step_dict.get("code"),
                prompt=step_dict.get("prompt"),
                run_if=step_dict.get("run_if"),
                on_failure=on_failure,
                max_retries=step_dict.get("max_retries", default_max_retries),
                in_state=in_state,
                transition_to=step_dict.get("transition_to"),
            )
            steps.append(step)

        return cls(
            steps=steps,
            default_on_failure=default_on_failure,
            default_max_retries=default_max_retries,
            state_machine=state_machine,
        )


class WorkflowRunner:
    """Executes workflow steps sequentially.

    The runner maintains a context dict that steps can read from and write to.
    Code steps execute Python expressions with the context as local variables.
    LLM steps call the LLM with an interpolated prompt and store results.

    Attributes:
        llm_provider: Optional LLM provider for LLM steps
    """

    def __init__(self, llm_provider: "LLMProvider | None" = None) -> None:
        """Initialize workflow runner.

        Args:
            llm_provider: LLM provider for executing LLM steps
        """
        self.llm_provider = llm_provider

    def run_workflow(
        self,
        config: WorkflowConfig,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a complete workflow.

        Args:
            config: Workflow configuration
            context: Initial context (modified in place by steps)

        Returns:
            Result dict with:
                - success: Whether workflow completed successfully
                - action: Final action (from last LLM step), or None
                - error: Error message if failed
                - step_results: Results from each step
                - state: Final state (if state machine configured)
        """
        step_results: list[dict[str, Any]] = []
        last_action: dict[str, Any] | None = None

        # Initialize state machine if configured
        state_machine: WorkflowStateMachine | None = None
        if config.state_machine:
            state_machine = WorkflowStateMachine(config.state_machine, context)
            # Add current state to context for step access
            context["_current_state"] = state_machine.current_state
            context.update(state_machine.to_context())

        for step in config.steps:
            result = self.execute_step(step, context, state_machine)
            step_results.append({"step": step.name, **result})

            # Check if we should stop
            if result.get("workflow_should_stop"):
                return {
                    "success": False,
                    "action": None,
                    "error": result.get("error", "Workflow stopped"),
                    "step_results": step_results,
                    "state": state_machine.current_state if state_machine else None,
                }

            # Track action from LLM steps
            if result.get("success") and step.step_type == StepType.LLM:
                if "action" in result:
                    last_action = result["action"]

        # Update context with final state
        if state_machine:
            context.update(state_machine.to_context())

        return {
            "success": True,
            "action": last_action,
            "step_results": step_results,
            "state": state_machine.current_state if state_machine else None,
        }

    def execute_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
        state_machine: WorkflowStateMachine | None = None,
    ) -> dict[str, Any]:
        """Execute a single workflow step.

        Args:
            step: Step to execute
            context: Shared context (modified in place)
            state_machine: Optional state machine for state-aware execution

        Returns:
            Result dict with success, error, skipped flags
        """
        # Check state condition (in_state)
        if step.in_state and state_machine:
            if not state_machine.in_state(*step.in_state):
                logger.debug(
                    f"Step '{step.name}' skipped (not in state {step.in_state}, "
                    f"current={state_machine.current_state})"
                )
                return {"success": True, "skipped": True, "reason": "state_condition"}

        # Check run_if condition using safe expression evaluator (Plan #123)
        if step.run_if:
            try:
                should_run = safe_eval_condition(step.run_if, context)
                if not should_run:
                    logger.debug(f"Step '{step.name}' skipped (run_if=False)")
                    return {"success": True, "skipped": True}
            except SafeExpressionError as e:
                logger.warning(f"Step '{step.name}' run_if eval failed: {e}")
                return {"success": True, "skipped": True}

        # Execute based on step type
        if step.step_type == StepType.CODE:
            result = self._execute_code_step(step, context)
        elif step.step_type == StepType.LLM:
            result = self._execute_llm_step(step, context)
        else:
            return {"success": False, "error": f"Unknown step type: {step.step_type}"}

        # Handle state transition after successful step
        if result.get("success") and step.transition_to and state_machine:
            if state_machine.transition_to(step.transition_to, context):
                context["_current_state"] = state_machine.current_state
                result["state_transition"] = {
                    "to": step.transition_to,
                    "success": True,
                }
            else:
                logger.warning(
                    f"Step '{step.name}' transition to '{step.transition_to}' failed"
                )
                result["state_transition"] = {
                    "to": step.transition_to,
                    "success": False,
                }

        return result

    def _execute_code_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a code step.

        Runs Python code with context as local variables.
        Any variables assigned become part of the context.
        """
        if not step.code:
            return {"success": False, "error": "Code step missing code"}

        try:
            # Execute code with context as locals
            # Use exec to allow statements, capture new variables
            local_vars = dict(context)
            exec(step.code, {}, local_vars)  # noqa: S102

            # Update context with any new/modified variables
            for key, value in local_vars.items():
                if key not in context or context[key] != value:
                    context[key] = value

            logger.debug(f"Code step '{step.name}' executed successfully")
            return {"success": True}

        except Exception as e:
            logger.warning(f"Code step '{step.name}' failed: {e}")
            return self._handle_step_error(step, str(e))

    def _execute_llm_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an LLM step.

        Interpolates context into prompt, calls LLM, stores response.
        """
        if not step.prompt:
            return {"success": False, "error": "LLM step missing prompt"}

        if not self.llm_provider:
            return {"success": False, "error": "No LLM provider configured"}

        # Interpolate context into prompt
        try:
            prompt = step.prompt.format(**context)
        except KeyError as e:
            # Missing context variable - use prompt as-is
            logger.debug(f"Prompt interpolation missing key {e}, using raw prompt")
            prompt = step.prompt

        # Execute with retry logic
        attempts = 0
        last_error: str | None = None

        while attempts <= step.max_retries:
            try:
                # Import here to avoid circular deps
                from .models import ActionResponse, FlatActionResponse

                # Call LLM
                response = self.llm_provider.generate(
                    prompt,
                    response_model=FlatActionResponse
                    if "gemini" in getattr(self.llm_provider, "model", "").lower()
                    else ActionResponse,
                )

                # Convert FlatActionResponse if needed
                if hasattr(response, "to_action_response"):
                    response = response.to_action_response()

                # Store response in context under step name
                result_data = {
                    "thought_process": response.thought_process,
                    "action": response.action.model_dump(),
                }
                context[step.name] = result_data

                logger.debug(f"LLM step '{step.name}' executed successfully")
                return {
                    "success": True,
                    "thought_process": response.thought_process,
                    "action": response.action.model_dump(),
                }

            except Exception as e:
                last_error = str(e)
                attempts += 1
                if attempts <= step.max_retries and step.on_failure == ErrorPolicy.RETRY:
                    logger.debug(
                        f"LLM step '{step.name}' attempt {attempts} failed: {e}, retrying"
                    )
                    continue
                break

        # All retries exhausted or non-retry policy
        logger.warning(f"LLM step '{step.name}' failed after {attempts} attempts: {last_error}")
        return self._handle_step_error(step, last_error or "Unknown error")

    def _handle_step_error(
        self,
        step: WorkflowStep,
        error: str,
    ) -> dict[str, Any]:
        """Handle step error according to policy.

        Returns appropriate result based on step's on_failure policy.
        """
        if step.on_failure == ErrorPolicy.SKIP:
            return {
                "success": False,
                "error": error,
                "skipped_due_to_error": True,
            }
        elif step.on_failure == ErrorPolicy.FAIL:
            return {
                "success": False,
                "error": error,
                "workflow_should_stop": True,
            }
        else:
            # RETRY exhausted - treat as failure
            return {
                "success": False,
                "error": error,
                "workflow_should_stop": True,
            }
