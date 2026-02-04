"""Workflow Hooks - Auto-invocation at workflow timing points (Plan #208)

Hooks enable agents to configure automatic artifact invocations at specific
points in the workflow cycle:
- pre_decision: Before LLM call (search, load context)
- post_decision: After LLM response, before action execution (validate)
- post_action: After action executed (log, notify)
- on_error: When action fails (recovery, alerting)

Hooks go through normal kernel path - contracts decide costs and permissions.
Agent is the caller - agent identity, agent pays.
"""

from __future__ import annotations

import re
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from ..world.artifacts import ArtifactStore


class ArtifactInvoker(Protocol):
    """Protocol for invoking artifacts.

    Any object that can invoke artifacts (e.g., World) should match this.
    """
    def invoke_artifact(
        self,
        invoker_id: str,
        artifact_id: str,
        method: str,
        args: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke an artifact method and return result dict."""
        ...

logger = logging.getLogger(__name__)


class HookTiming(str, Enum):
    """When hooks execute in the workflow cycle."""
    PRE_DECISION = "pre_decision"      # Before LLM call
    POST_DECISION = "post_decision"    # After LLM, before action execution
    POST_ACTION = "post_action"        # After action executed
    ON_ERROR = "on_error"              # When action fails


class HookErrorPolicy(str, Enum):
    """What to do when a hook fails."""
    SKIP = "skip"      # Continue to next hook
    FAIL = "fail"      # Abort workflow step
    RETRY = "retry"    # Retry the hook (with limit)


# Special injection targets
INJECT_PROMPT = "_prompt"          # Becomes the LLM prompt
INJECT_SYSTEM_PROMPT = "_system_prompt"  # Prepended to system prompt
INJECT_NULL = "null"               # Side effect only, no injection


@dataclass
class HookDefinition:
    """A single hook configuration.

    Attributes:
        artifact_id: ID of artifact to invoke
        method: Method to call on the artifact
        args: Arguments to pass (may contain {var} interpolation)
        inject_as: Where to inject result (context key, or special target)
        on_error: Error handling policy
        max_retries: Max retries if on_error is RETRY
    """
    artifact_id: str
    method: str
    args: dict[str, Any] = field(default_factory=dict)
    inject_as: str | None = None
    on_error: HookErrorPolicy = HookErrorPolicy.SKIP
    max_retries: int = 3

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HookDefinition:
        """Create HookDefinition from dict config."""
        return cls(
            artifact_id=data.get("artifact_id", ""),
            method=data.get("method", "run"),
            args=data.get("args", {}),
            inject_as=data.get("inject_as"),
            on_error=HookErrorPolicy(data.get("on_error", "skip")),
            max_retries=data.get("max_retries", 3),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "artifact_id": self.artifact_id,
            "method": self.method,
            "args": self.args,
            "inject_as": self.inject_as,
            "on_error": self.on_error.value,
            "max_retries": self.max_retries,
        }


@dataclass
class HooksConfig:
    """Hook configuration for an agent or workflow step.

    Hooks at different levels merge (agent + workflow + step).
    Execution order: agent-level → workflow-level → step-level.
    """
    pre_decision: list[HookDefinition] = field(default_factory=list)
    post_decision: list[HookDefinition] = field(default_factory=list)
    post_action: list[HookDefinition] = field(default_factory=list)
    on_error: list[HookDefinition] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> HooksConfig:
        """Create HooksConfig from dict config."""
        if not data:
            return cls()

        return cls(
            pre_decision=[
                HookDefinition.from_dict(h) for h in data.get("pre_decision", [])
            ],
            post_decision=[
                HookDefinition.from_dict(h) for h in data.get("post_decision", [])
            ],
            post_action=[
                HookDefinition.from_dict(h) for h in data.get("post_action", [])
            ],
            on_error=[
                HookDefinition.from_dict(h) for h in data.get("on_error", [])
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        result: dict[str, Any] = {}
        if self.pre_decision:
            result["pre_decision"] = [h.to_dict() for h in self.pre_decision]
        if self.post_decision:
            result["post_decision"] = [h.to_dict() for h in self.post_decision]
        if self.post_action:
            result["post_action"] = [h.to_dict() for h in self.post_action]
        if self.on_error:
            result["on_error"] = [h.to_dict() for h in self.on_error]
        return result

    def merge(self, other: HooksConfig) -> HooksConfig:
        """Merge with another HooksConfig (other's hooks come after self's)."""
        return HooksConfig(
            pre_decision=self.pre_decision + other.pre_decision,
            post_decision=self.post_decision + other.post_decision,
            post_action=self.post_action + other.post_action,
            on_error=self.on_error + other.on_error,
        )

    def get_hooks(self, timing: HookTiming) -> list[HookDefinition]:
        """Get hooks for a specific timing point."""
        if timing == HookTiming.PRE_DECISION:
            return self.pre_decision
        elif timing == HookTiming.POST_DECISION:
            return self.post_decision
        elif timing == HookTiming.POST_ACTION:
            return self.post_action
        elif timing == HookTiming.ON_ERROR:
            return self.on_error
        return []

    def is_empty(self) -> bool:
        """Check if no hooks are configured."""
        return not (self.pre_decision or self.post_decision or
                    self.post_action or self.on_error)


@dataclass
class HookResult:
    """Result from executing a single hook."""
    success: bool
    result: Any = None
    error: str | None = None
    inject_as: str | None = None

    @property
    def should_inject(self) -> bool:
        """Whether this result should be injected into context."""
        return (
            self.success and
            self.inject_as is not None and
            self.inject_as != INJECT_NULL
        )


# Type alias for hook completion callback
# Signature: (agent_id, timing, hook, result, duration_ms) -> None
HookCompletionCallback = "Callable[[str, HookTiming, HookDefinition, HookResult, float], None]"


class HookExecutor:
    """Executes hooks at workflow timing points.

    Handles:
    - Argument interpolation from context
    - Artifact invocation via executor
    - Result injection into context
    - Error handling per hook policy
    - Depth limit to prevent infinite loops
    - Observability via optional completion callback (Plan #208 Phase 4)
    """

    # Pattern for {variable} interpolation
    INTERPOLATION_PATTERN = re.compile(r'\{(\w+)\}')

    def __init__(
        self,
        artifact_store: ArtifactStore,
        invoker: ArtifactInvoker,
        max_depth: int = 5,
        on_hook_complete: Callable[
            [str, HookTiming, HookDefinition, HookResult, float], None
        ] | None = None,
    ):
        """Initialize hook executor.

        Args:
            artifact_store: Store for artifact lookup
            invoker: Object that can invoke artifacts (e.g., World)
            max_depth: Maximum hook recursion depth
            on_hook_complete: Optional callback called after each hook executes.
                Signature: (agent_id, timing, hook, result, duration_ms) -> None
                Used for observability (Plan #208 Phase 4).
        """
        self.artifact_store = artifact_store
        self.invoker = invoker
        self.max_depth = max_depth
        self._current_depth = 0
        self._on_hook_complete = on_hook_complete

    def interpolate_args(
        self,
        args: dict[str, Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Interpolate {variable} references in args from context.

        Args:
            args: Argument dict with potential {var} references
            context: Context dict to look up values from

        Returns:
            New dict with interpolated values
        """
        result: dict[str, Any] = {}
        for key, value in args.items():
            if isinstance(value, str):
                # Replace all {var} patterns
                def replace_var(match: re.Match[str]) -> str:
                    var_name = match.group(1)
                    var_value = context.get(var_name, f"{{{var_name}}}")
                    if isinstance(var_value, str):
                        return var_value
                    # Convert non-strings to string representation
                    return str(var_value)

                result[key] = self.INTERPOLATION_PATTERN.sub(replace_var, value)
            elif isinstance(value, dict):
                # Recursively interpolate nested dicts
                result[key] = self.interpolate_args(value, context)
            else:
                result[key] = value
        return result

    async def execute_hook(
        self,
        hook: HookDefinition,
        caller_id: str,
        context: dict[str, Any],
    ) -> HookResult:
        """Execute a single hook.

        Args:
            hook: Hook definition to execute
            caller_id: ID of the calling agent (for billing/permissions)
            context: Current context for arg interpolation

        Returns:
            HookResult with success status and result/error
        """
        # Check depth limit
        if self._current_depth >= self.max_depth:
            return HookResult(
                success=False,
                error=f"Hook depth limit ({self.max_depth}) exceeded",
                inject_as=hook.inject_as,
            )

        # Interpolate args from context
        interpolated_args = self.interpolate_args(hook.args, context)

        # Get the artifact
        artifact = self.artifact_store.get(hook.artifact_id)
        if artifact is None:
            return HookResult(
                success=False,
                error=f"Artifact '{hook.artifact_id}' not found",
                inject_as=hook.inject_as,
            )

        # Special case: reading data artifacts (Plan #191 subscriptions)
        # Data artifacts aren't executable, so we read content directly instead of invoking
        if not artifact.executable and hook.method == "read_content":
            return HookResult(
                success=True,
                result=artifact.content,
                inject_as=hook.inject_as,
            )

        # Execute via invoker
        try:
            self._current_depth += 1
            result = self.invoker.invoke_artifact(
                invoker_id=caller_id,
                artifact_id=hook.artifact_id,
                method=hook.method,
                args=list(interpolated_args.values()) if interpolated_args else [],
            )

            if result.get("success"):
                return HookResult(
                    success=True,
                    result=result.get("data"),
                    inject_as=hook.inject_as,
                )
            else:
                return HookResult(
                    success=False,
                    error=result.get("message", "Unknown error"),
                    inject_as=hook.inject_as,
                )
        except Exception as e:
            logger.warning(f"Hook {hook.artifact_id}.{hook.method} failed: {e}")
            return HookResult(
                success=False,
                error=str(e),
                inject_as=hook.inject_as,
            )
        finally:
            self._current_depth -= 1

    async def execute_hooks(
        self,
        hooks: list[HookDefinition],
        timing: HookTiming,
        caller_id: str,
        context: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        """Execute a list of hooks at a timing point.

        Args:
            hooks: List of hooks to execute
            timing: Timing point (for logging)
            caller_id: ID of the calling agent
            context: Current context dict (will be updated with injections)

        Returns:
            Tuple of (updated_context, should_continue)
            should_continue is False if a hook with on_error=fail failed
        """
        updated_context = dict(context)

        for hook in hooks:
            retries = 0
            while True:
                # Track execution time for observability
                start_time = time.perf_counter()
                result = await self.execute_hook(hook, caller_id, updated_context)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Call completion callback if registered (Plan #208 Phase 4)
                if self._on_hook_complete:
                    try:
                        self._on_hook_complete(
                            caller_id, timing, hook, result, duration_ms
                        )
                    except Exception as e:
                        logger.warning(f"Hook completion callback failed: {e}")

                if result.success:
                    # Inject result into context if configured
                    if result.should_inject and result.inject_as is not None:
                        if result.inject_as == INJECT_PROMPT:
                            updated_context["_hook_prompt"] = result.result
                        elif result.inject_as == INJECT_SYSTEM_PROMPT:
                            existing = updated_context.get("_hook_system_prompt", "")
                            updated_context["_hook_system_prompt"] = (
                                f"{existing}\n{result.result}" if existing else result.result
                            )
                        else:
                            updated_context[result.inject_as] = result.result

                    # INFO-level logging for successful hooks (Plan #208 Phase 4)
                    logger.info(
                        f"Hook {hook.artifact_id}.{hook.method} succeeded at {timing.value} "
                        f"({duration_ms:.1f}ms)"
                    )
                    break  # Success, move to next hook

                else:
                    # Hook failed
                    logger.warning(
                        f"Hook {hook.artifact_id}.{hook.method} failed at {timing.value}: "
                        f"{result.error} ({duration_ms:.1f}ms)"
                    )

                    if hook.on_error == HookErrorPolicy.FAIL:
                        # Abort workflow step
                        return updated_context, False

                    elif hook.on_error == HookErrorPolicy.RETRY:
                        retries += 1
                        if retries >= hook.max_retries:
                            logger.warning(
                                f"Hook {hook.artifact_id}.{hook.method} exceeded max retries"
                            )
                            break  # Give up, move to next hook
                        logger.info(
                            f"Hook {hook.artifact_id}.{hook.method} retrying "
                            f"({retries}/{hook.max_retries})"
                        )
                        # Loop continues for retry

                    else:  # SKIP
                        break  # Move to next hook

        return updated_context, True


def expand_subscribed_artifacts(
    subscribed: list[str],
    warn_deprecated: bool = True,
) -> HooksConfig:
    """Convert subscribed_artifacts to equivalent pre_decision hooks.

    Plan #191 unification: subscribed_artifacts is sugar for hooks.
    Plan #208 Phase 3: This function implements the unification.

    Note: subscribed_artifacts is now deprecated in favor of explicit hooks.
    Use hooks.pre_decision with method="read_content" instead.

    Args:
        subscribed: List of artifact IDs to subscribe to
        warn_deprecated: If True, emit deprecation warning (default True)

    Returns:
        HooksConfig with pre_decision hooks for each subscription
    """
    if subscribed and warn_deprecated:
        import warnings
        warnings.warn(
            "subscribed_artifacts is deprecated. Use hooks.pre_decision with "
            "artifact_id and method='read_content' instead. "
            "See Plan #208 for the new hooks system.",
            DeprecationWarning,
            stacklevel=3,  # Point to the caller's caller
        )

    pre_decision_hooks = []
    for artifact_id in subscribed:
        pre_decision_hooks.append(HookDefinition(
            artifact_id=artifact_id,
            method="read_content",
            args={},
            inject_as=f"subscribed_{artifact_id}",
            on_error=HookErrorPolicy.SKIP,
        ))

    return HooksConfig(pre_decision=pre_decision_hooks)
