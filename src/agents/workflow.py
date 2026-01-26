"""Configurable agent workflow execution engine.

Implements ADR-0013: Configurable Agent Workflows (Phase 1).

Workflows are ordered lists of steps that execute sequentially. Each step
can be either a code step (Python expression) or an LLM step (prompt).

Extended with state machine support (Plan #82) for VSM-aligned agents:
- States define distinct operational modes (e.g., "planning", "executing")
- Transitions validate state changes
- Steps can be conditional on current state

Plan #222: Artifact-aware workflow engine
- Workflow conditions can invoke artifacts for dynamic decisions
- Supports InvokeSpec for transition conditions
- Enables cognitive self-modification via artifacts

Usage:
    from src.agents.workflow import WorkflowRunner, WorkflowConfig

    config = WorkflowConfig.from_dict(agent_workflow_config)
    runner = WorkflowRunner(llm_provider=agent.llm, world=world)
    result = runner.run_workflow(config, context={"agent_id": "alpha", ...})

    if result["success"]:
        action = result["action"]  # Action to execute
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

from src.agents.safe_eval import SafeExpressionError, safe_eval_condition

if TYPE_CHECKING:
    from llm_provider import LLMProvider
    from src.world.world import World

from .state_machine import StateConfig, WorkflowStateMachine

logger = logging.getLogger(__name__)

# Plan #157 Phase 4: Default transition evaluation prompt template
DEFAULT_TRANSITION_PROMPT = """=== TRANSITION EVALUATION ===
Time remaining: {time_remaining} | Success rate: {success_rate} | Revenue: {revenue_earned:+.0f}

## RECENT ACTIONS
{action_history}

## LAST RESULT
{last_action_result}

## DECISION REQUIRED
Based on your performance and time remaining, choose ONE:

A) CONTINUE - You're making progress, worth continuing
   - Recent actions show improvement
   - Close to completing something valuable

B) PIVOT - You're stuck, try something different
   - Same errors repeating (3+ times)
   - No progress despite multiple attempts
   - Time is running out, need a simpler approach

C) SHIP - Current work is good enough, move on
   - Artifact works (even if imperfect)
   - Don't over-optimize, capture the value

Respond with exactly one of: continue, pivot, or ship
"""


class StepType(str, Enum):
    """Type of workflow step."""

    CODE = "code"
    LLM = "llm"
    TRANSITION = "transition"  # Plan #157: LLM-informed transition evaluation


class ErrorPolicy(str, Enum):
    """How to handle step errors."""

    RETRY = "retry"  # Retry the step
    SKIP = "skip"  # Skip and continue workflow
    FAIL = "fail"  # Stop workflow execution


@dataclass
class InvokeSpec:
    """Specification for invoking an artifact during workflow execution.

    Plan #222: Enables workflow decisions to be delegated to artifacts.
    When a workflow condition or prompt uses InvokeSpec, the workflow runner
    invokes the specified artifact and uses its return value.

    Attributes:
        artifact_id: ID of the artifact to invoke
        method: Method name to call on the artifact
        args: Additional arguments to pass (context is always passed)
        fallback: Value to use if invocation fails (REQUIRED for resilience)
    """

    artifact_id: str
    method: str
    args: list[Any] = field(default_factory=list)
    fallback: Any = None  # Required per R2 in Plan #222

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InvokeSpec":
        """Create InvokeSpec from dictionary (parsed YAML).

        Expected format:
            invoke: "artifact_id"
            method: "method_name"
            args: []  # optional
            fallback: true  # required
        """
        return cls(
            artifact_id=data["invoke"],
            method=data["method"],
            args=data.get("args", []),
            fallback=data.get("fallback"),
        )

    @classmethod
    def is_invoke_spec(cls, data: Any) -> bool:
        """Check if data represents an InvokeSpec (dict with 'invoke' key)."""
        return isinstance(data, dict) and "invoke" in data


@dataclass
class WorkflowStep:
    """A single step in a workflow.

    Attributes:
        name: Unique name for this step (used for context storage)
        step_type: Type of step (code, llm, or transition)
        code: Python code to execute (for code steps)
        prompt: Prompt text, template, or InvokeSpec dict (for llm and transition steps)
                Plan #222 Phase 3: Can be an InvokeSpec dict to generate prompts dynamically
        prompt_artifact_id: Reference to prompt artifact (Plan #146 Phase 3)
        run_if: Optional condition - step only runs if this evaluates to True
        on_failure: Error handling policy for this step
        max_retries: Maximum retry attempts (for RETRY policy)
        in_state: Only run if state machine is in one of these states
        transition_to: Transition to this state after step completes
        transition_map: For transition steps - maps decisions to target states
        transition_mode: How to determine next state - "llm", "condition", or "auto" (Plan #146)
        transition_prompt_artifact_id: Prompt artifact for LLM transitions (Plan #146)
        transition_source: InvokeSpec for artifact-based transition decisions (Plan #222 Phase 4)
    """

    name: str
    step_type: StepType
    code: str | None = None
    prompt: str | dict[str, Any] | None = None  # Plan #222: Can be InvokeSpec dict
    # Plan #146 Phase 3: Reference to prompt artifact instead of inline prompt
    prompt_artifact_id: str | None = None
    run_if: str | None = None
    on_failure: ErrorPolicy = ErrorPolicy.FAIL
    max_retries: int = 3
    in_state: list[str] | None = None  # State condition
    transition_to: str | None = None  # State to transition to after step
    # Plan #157: Transition step configuration
    transition_map: dict[str, str] | None = None  # Maps decision -> target state
    # Plan #146 Phase 3: LLM-controlled transitions
    transition_mode: str | None = None  # "llm" | "condition" | "auto"
    transition_prompt_artifact_id: str | None = None  # Prompt artifact for LLM transitions
    # Plan #222 Phase 4: Artifact-based transition decisions
    transition_source: dict[str, Any] | None = None  # InvokeSpec for artifact-based decisions

    def __post_init__(self) -> None:
        """Validate step configuration."""
        if self.step_type == StepType.CODE and not self.code:
            raise ValueError(f"Code step '{self.name}' requires 'code' field")
        # LLM steps need either inline prompt, prompt_artifact_id, or InvokeSpec (Plan #222)
        if self.step_type == StepType.LLM and not self.prompt and not self.prompt_artifact_id:
            raise ValueError(f"LLM step '{self.name}' requires 'prompt' or 'prompt_artifact_id'")
        # Transition steps can use default prompt, so prompt is optional


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

            # Plan #157: Parse transition_map for transition steps
            transition_map = step_dict.get("transition_map")
            if transition_map and not isinstance(transition_map, dict):
                transition_map = None  # Ensure it's a dict

            # Plan #146 Phase 3: Parse transition mode
            transition_mode = step_dict.get("transition_mode")
            if transition_mode and transition_mode not in ("llm", "condition", "auto"):
                transition_mode = None  # Invalid value, ignore

            step = WorkflowStep(
                name=step_dict["name"],
                step_type=step_type,
                code=step_dict.get("code"),
                prompt=step_dict.get("prompt"),
                prompt_artifact_id=step_dict.get("prompt_artifact_id"),  # Plan #146
                run_if=step_dict.get("run_if"),
                on_failure=on_failure,
                max_retries=step_dict.get("max_retries", default_max_retries),
                in_state=in_state,
                transition_to=step_dict.get("transition_to"),
                transition_map=transition_map,
                transition_mode=transition_mode,  # Plan #146
                transition_prompt_artifact_id=step_dict.get("transition_prompt_artifact_id"),  # Plan #146
                transition_source=step_dict.get("transition_source"),  # Plan #222 Phase 4
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

    Plan #222: Supports artifact invocation for workflow decisions via world reference.

    Attributes:
        llm_provider: Optional LLM provider for LLM steps
        world: Optional World reference for artifact invocation
    """

    def __init__(
        self,
        llm_provider: "LLMProvider | None" = None,
        world: "World | None" = None,
    ) -> None:
        """Initialize workflow runner.

        Args:
            llm_provider: LLM provider for executing LLM steps
            world: World reference for artifact invocation (Plan #222)
        """
        self.llm_provider = llm_provider
        self.world = world
        # Per-run cache for invoke results (Plan #222)
        self._invoke_cache: dict[str, Any] = {}

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

        # Plan #222: Clear invoke cache at start of each workflow run
        self._invoke_cache = {}

        # Initialize state machine if configured
        state_machine: WorkflowStateMachine | None = None
        if config.state_machine:
            # Plan #222: Pass invoke resolver for artifact-based conditions
            state_machine = WorkflowStateMachine(
                config.state_machine,
                context,
                invoke_resolver=self._create_invoke_resolver(context),
            )
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

    def _create_invoke_resolver(
        self,
        base_context: dict[str, Any],
    ) -> "Callable[[str, str, list[Any], dict[str, Any], Any], Any]":
        """Create an invoke resolver function for the state machine.

        Plan #222: Returns a callable that resolves InvokeSpec conditions by
        calling artifacts and caching results per-run.

        Args:
            base_context: Base context with agent_id and other info

        Returns:
            Resolver function (artifact_id, method, args, context, fallback) -> result
        """
        def resolver(
            artifact_id: str,
            method: str,
            args: list[Any],
            context: dict[str, Any],
            fallback: Any,
        ) -> Any:
            return self._resolve_invoke(artifact_id, method, args, context, fallback)

        return resolver

    def _resolve_invoke(
        self,
        artifact_id: str,
        method: str,
        args: list[Any],
        context: dict[str, Any],
        fallback: Any,
    ) -> Any:
        """Invoke an artifact and return result, with caching.

        Plan #222: Central method for artifact invocation in workflows.
        Results are cached per-run to avoid repeated invocations.

        Args:
            artifact_id: ID of the artifact to invoke
            method: Method name to call
            args: Additional arguments (context is passed automatically)
            context: Workflow context
            fallback: Value to return if invocation fails

        Returns:
            Result from artifact or fallback on error
        """
        # Check cache first (per-run caching as per Plan #222 design decision)
        cache_key = f"{artifact_id}:{method}:{str(args)}"
        if cache_key in self._invoke_cache:
            logger.debug(f"Invoke cache hit: {cache_key}")
            return self._invoke_cache[cache_key]

        # Need world reference to invoke artifacts
        if not self.world:
            logger.debug(
                f"No world reference for invoke {artifact_id}.{method}, using fallback"
            )
            return fallback

        # Get agent_id from context for the invoker
        agent_id = context.get("agent_id", "unknown")

        try:
            # Build context to pass to artifact (Plan #222 standard context)
            invoke_context = {
                "agent_id": agent_id,
                "current_state": context.get("_current_state", ""),
                "balance": context.get("balance", 0),
                "success_rate": context.get("success_rate", 0.0),
                "recent_actions": context.get("action_history", ""),
                "last_result": context.get("last_action_result", {}),
            }

            # Call artifact via world
            result = self.world.invoke_artifact(
                invoker_id=agent_id,
                artifact_id=artifact_id,
                method=method,
                args=args + [invoke_context],  # Pass context as last arg
            )

            # Extract result value
            if hasattr(result, "success") and hasattr(result, "data"):
                # ActionResult-like object
                value = result.data if result.success else fallback
            else:
                # Raw result
                value = result

            # Cache and return
            self._invoke_cache[cache_key] = value
            logger.debug(f"Invoke {artifact_id}.{method} returned: {value}")
            return value

        except Exception as e:
            logger.warning(
                f"Invoke {artifact_id}.{method} failed: {e}, using fallback {fallback}"
            )
            return fallback

    def _resolve_invoke_spec(
        self,
        spec: InvokeSpec,
        context: dict[str, Any],
    ) -> Any:
        """Resolve an InvokeSpec by invoking the artifact.

        Plan #222: Convenience wrapper around _resolve_invoke.

        Args:
            spec: InvokeSpec with artifact_id, method, args, fallback
            context: Workflow context

        Returns:
            Result from artifact or fallback
        """
        return self._resolve_invoke(
            artifact_id=spec.artifact_id,
            method=spec.method,
            args=spec.args,
            context=context,
            fallback=spec.fallback,
        )

    def _resolve_prompt(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> str | None:
        """Resolve the prompt for an LLM step from various sources.

        Plan #222 Phase 3: Supports dynamic prompt generation via artifact invocation.

        Prompt resolution order:
        1. If step.prompt is an InvokeSpec dict, invoke artifact to get prompt
        2. If step.prompt_artifact_id is set, read prompt from artifact
        3. If step.prompt is a string, use it directly

        Args:
            step: WorkflowStep with prompt configuration
            context: Workflow context for interpolation and invoke

        Returns:
            Resolved prompt string, or None if resolution fails
        """
        # Case 1: Prompt is an InvokeSpec dict (Plan #222 Phase 3)
        if isinstance(step.prompt, dict) and InvokeSpec.is_invoke_spec(step.prompt):
            spec = InvokeSpec.from_dict(step.prompt)
            result = self._resolve_invoke_spec(spec, context)
            if result is not None and isinstance(result, str):
                logger.debug(f"Step '{step.name}' prompt resolved via InvokeSpec")
                return result
            elif result is not None:
                # Artifact returned non-string, try to convert
                logger.warning(
                    f"Step '{step.name}' InvokeSpec returned non-string: {type(result)}, "
                    "converting to string"
                )
                return str(result)
            else:
                # Fallback was None
                logger.warning(f"Step '{step.name}' InvokeSpec returned None")
                return None

        # Case 2: Prompt artifact reference (Plan #146 Phase 3)
        if step.prompt_artifact_id:
            if not self.world:
                logger.warning(
                    f"Step '{step.name}' has prompt_artifact_id but no world reference"
                )
                # Fall through to step.prompt as fallback
            else:
                try:
                    result = self.world.read_artifact(
                        requester_id=context.get("agent_id", "workflow"),
                        artifact_id=step.prompt_artifact_id,
                    )
                    # read_artifact returns dict directly or {"success": False, ...}
                    if result.get("success", True) is not False:
                        # Artifact content is the prompt
                        prompt_content = result.get("content", "")
                        if isinstance(prompt_content, str):
                            logger.debug(
                                f"Step '{step.name}' prompt loaded from artifact "
                                f"'{step.prompt_artifact_id}'"
                            )
                            return prompt_content
                except Exception as e:
                    logger.warning(
                        f"Failed to load prompt artifact '{step.prompt_artifact_id}': {e}"
                    )
                    # Fall through to step.prompt as fallback

        # Case 3: Static prompt string
        if isinstance(step.prompt, str):
            return step.prompt

        return None

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
        elif step.step_type == StepType.TRANSITION:
            result = self._execute_transition_step(step, context, state_machine)
            # Transition step handles its own state transitions via transition_map
            return result
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

        Plan #222 Phase 3: Supports dynamic prompts via artifact invocation.
        Resolves prompt from multiple sources, interpolates context, calls LLM.
        """
        if not self.llm_provider:
            return {"success": False, "error": "No LLM provider configured"}

        # Plan #222 Phase 3: Resolve prompt from various sources
        raw_prompt = self._resolve_prompt(step, context)
        if not raw_prompt:
            return {"success": False, "error": "LLM step missing prompt (resolution failed)"}

        # Interpolate context into prompt
        try:
            prompt = raw_prompt.format(**context)
        except KeyError as e:
            # Missing context variable - use prompt as-is
            logger.debug(f"Prompt interpolation missing key {e}, using raw prompt")
            prompt = raw_prompt

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
                    "reasoning": response.reasoning,
                    "action": response.action.model_dump(),
                }
                context[step.name] = result_data

                logger.debug(f"LLM step '{step.name}' executed successfully")
                return {
                    "success": True,
                    "reasoning": response.reasoning,
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

    def _execute_transition_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
        state_machine: WorkflowStateMachine | None = None,
    ) -> dict[str, Any]:
        """Execute a transition evaluation step.

        Plan #157 Phase 4: Uses LLM to decide whether to continue, pivot, or ship.
        Plan #222 Phase 4: Can use artifact invocation instead of LLM for decisions.
        Then maps the decision to a state transition via transition_map.

        Args:
            step: Transition step to execute
            context: Shared context (modified in place)
            state_machine: Optional state machine for state transitions

        Returns:
            Result dict with decision, reasoning, and state_transition info
        """
        decision: str
        reasoning: str = ""
        next_focus: str = ""

        # Plan #222 Phase 4: Check for artifact-based transition
        if step.transition_source and InvokeSpec.is_invoke_spec(step.transition_source):
            spec = InvokeSpec.from_dict(step.transition_source)
            result = self._resolve_invoke_spec(spec, context)

            if result is not None:
                # Artifact returned a decision
                if isinstance(result, str):
                    decision = result
                    reasoning = f"Artifact {spec.artifact_id}.{spec.method} decided: {decision}"
                    logger.debug(
                        f"Transition step '{step.name}' decision from artifact: {decision}"
                    )
                elif isinstance(result, dict):
                    # Artifact may return structured response
                    decision = str(result.get("decision", result.get("state", "continue")))
                    reasoning = str(result.get("reasoning", f"From {spec.artifact_id}"))
                    next_focus = str(result.get("next_focus", ""))
                else:
                    decision = str(result)
                    reasoning = f"Artifact {spec.artifact_id}.{spec.method} returned: {result}"
            else:
                # Fallback was None or invocation failed
                logger.warning(
                    f"Transition step '{step.name}' artifact invocation failed, "
                    f"using fallback: {spec.fallback}"
                )
                decision = str(spec.fallback) if spec.fallback else "continue"
                reasoning = f"Fallback (artifact {spec.artifact_id} unavailable)"
        else:
            # Standard LLM-based transition evaluation
            # Resolve prompt (may be InvokeSpec, artifact reference, or static string)
            resolved_prompt = self._resolve_prompt(step, context)

            # Evaluate transition using LLM
            eval_result = self.evaluate_transition(context, resolved_prompt)

            if not eval_result.get("success"):
                return {
                    "success": False,
                    "error": eval_result.get("error", "Transition evaluation failed"),
                }

            decision = eval_result.get("decision", "continue")
            reasoning = eval_result.get("reasoning", "")
            next_focus = eval_result.get("next_focus", "")

        # Store evaluation result in context
        context[step.name] = {
            "decision": decision,
            "reasoning": reasoning,
            "next_focus": next_focus,
        }

        # Determine target state from transition_map
        target_state: str | None = None
        if step.transition_map:
            # Plan #222: Normalize decision to lowercase for boolean string matching
            # Python str(True/False) returns "True"/"False" but YAML uses "true"/"false"
            decision_key = decision.lower() if decision in ("True", "False") else decision
            target_state = step.transition_map.get(decision_key)
        elif step.transition_to:
            # Fallback to static transition_to if no map
            target_state = step.transition_to

        # Perform state transition if applicable
        result: dict[str, Any] = {
            "success": True,
            "decision": decision,
            "reasoning": reasoning,
            "next_focus": next_focus,
        }

        if target_state and state_machine:
            if state_machine.transition_to(target_state, context):
                context["_current_state"] = state_machine.current_state
                result["state_transition"] = {
                    "to": target_state,
                    "success": True,
                    "decision": decision,
                }
                logger.debug(
                    f"Transition step '{step.name}': {decision} -> {target_state}"
                )
            else:
                logger.warning(
                    f"Transition step '{step.name}': {decision} -> {target_state} failed"
                )
                result["state_transition"] = {
                    "to": target_state,
                    "success": False,
                    "decision": decision,
                }

        return result

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

    def evaluate_transition(
        self,
        context: dict[str, Any],
        prompt_template: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate whether to continue, pivot, or ship using LLM judgment.

        Plan #157 Phase 4: Replace hardcoded state transitions with LLM reasoning.
        Instead of `balance >= 20` deciding transitions, the LLM evaluates progress.

        Args:
            context: Workflow context with metrics (time_remaining, action_history, etc.)
            prompt_template: Optional custom prompt template. Uses DEFAULT_TRANSITION_PROMPT if None.

        Returns:
            Dict with:
                - success: Whether evaluation succeeded
                - decision: "continue", "pivot", or "ship"
                - reasoning: LLM's reasoning for the decision
                - next_focus: If pivoting, what to focus on next
                - error: Error message if evaluation failed
        """
        if not self.llm_provider:
            # No LLM - fall back to hardcoded logic
            return self._fallback_transition_evaluation(context)

        # Build prompt from template
        template = prompt_template or DEFAULT_TRANSITION_PROMPT
        try:
            prompt = template.format(**context)
        except KeyError as e:
            logger.debug(f"Transition prompt missing key {e}, using defaults")
            # Fill in missing keys with defaults
            safe_context = {
                "time_remaining": context.get("time_remaining", "(unknown)"),
                "success_rate": context.get("success_rate", "0/0"),
                "revenue_earned": context.get("revenue_earned", 0.0),
                "action_history": context.get("action_history", "(No actions yet)"),
                "last_action_result": context.get("last_action_result", "(No previous action)"),
            }
            prompt = template.format(**safe_context)

        try:
            from .models import TransitionEvaluationResponse

            response = self.llm_provider.generate(
                prompt,
                response_model=TransitionEvaluationResponse,
            )

            logger.debug(f"Transition evaluation: {response.decision} - {response.reasoning}")
            return {
                "success": True,
                "decision": response.decision,
                "reasoning": response.reasoning,
                "next_focus": response.next_focus,
            }

        except Exception as e:
            logger.warning(f"Transition evaluation failed: {e}, using fallback")
            return self._fallback_transition_evaluation(context)

    def _fallback_transition_evaluation(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Fallback transition evaluation when LLM is unavailable.

        Uses simple heuristics based on context metrics.
        """
        # Analyze action history for repeated patterns
        action_history = context.get("action_history", "")
        failed_actions = context.get("failed_actions", 0)
        successful_actions = context.get("successful_actions", 0)
        actions_taken = context.get("actions_taken", 0)

        # Count repeated patterns in action history
        repeated_count = 0
        if isinstance(action_history, str):
            lines = action_history.strip().split("\n")
            if len(lines) >= 3:
                # Check last 3 actions for same artifact
                recent = lines[-3:]
                artifact_ids = []
                for line in recent:
                    # Extract artifact_id from patterns like "write_artifact(my_tool)"
                    if "(" in line and ")" in line:
                        start = line.find("(") + 1
                        end = line.find(")")
                        artifact_ids.append(line[start:end])
                if len(set(artifact_ids)) == 1 and artifact_ids[0]:
                    repeated_count = 3

        # Decision logic
        if repeated_count >= 3:
            return {
                "success": True,
                "decision": "pivot",
                "reasoning": "Repeated attempts on same artifact without progress",
                "next_focus": "Try a different, simpler artifact",
            }
        elif successful_actions > 0 and failed_actions == 0:
            return {
                "success": True,
                "decision": "ship",
                "reasoning": "Recent actions successful, good time to ship",
                "next_focus": "",
            }
        else:
            return {
                "success": True,
                "decision": "continue",
                "reasoning": "Continue current approach",
                "next_focus": "",
            }
