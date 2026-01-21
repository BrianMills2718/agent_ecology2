"""Reflex system for fast agent decisions (Plan #143).

Reflexes are Python scripts that run BEFORE the LLM. If a reflex returns
an action, it executes immediately (0 latency, 0 inference cost). If not,
the agent falls back to LLM reasoning.

Key design principles:
- Reflexes are NOT developer-hardcoded - they are agent-created artifacts
- Agents can create, modify, and trade reflexes
- This enables evolutionary optimization of agent behavior

Usage:
    from src.agents.reflex import ReflexExecutor, ReflexContext

    # Build context from world state
    context = build_reflex_context(agent_id, world_state)

    # Execute reflex code
    executor = ReflexExecutor()
    result = executor.execute(reflex_code, context)

    if result.action is not None:
        # Use reflex action (skip LLM)
        return result.action
    else:
        # Fall back to LLM
        return agent.propose_action(world_state)
"""

from __future__ import annotations

import logging
import signal
import sys
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from ..config import get

if TYPE_CHECKING:
    from ..world.world import World

logger = logging.getLogger(__name__)


# Timeout exception for reflex execution
class ReflexTimeoutError(Exception):
    """Raised when reflex execution exceeds timeout."""

    pass


@dataclass
class ReflexContext:
    """Context passed to reflex functions.

    Contains a fast-to-build subset of world state that reflexes
    can use to make decisions without expensive queries.
    """

    agent_id: str
    tick: int
    balance: int

    # Resource state
    llm_tokens_remaining: int = 0
    disk_remaining: int = 0

    # Recent events (last N)
    recent_events: list[dict[str, Any]] = field(default_factory=list)

    # Pending items requiring response
    pending_purchases: list[dict[str, Any]] = field(default_factory=list)
    pending_contracts: list[dict[str, Any]] = field(default_factory=list)

    # Agent's owned artifacts
    owned_artifacts: list[str] = field(default_factory=list)

    # Additional context that may be useful
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for passing to reflex function."""
        return {
            "agent_id": self.agent_id,
            "tick": self.tick,
            "balance": self.balance,
            "llm_tokens_remaining": self.llm_tokens_remaining,
            "disk_remaining": self.disk_remaining,
            "recent_events": self.recent_events,
            "pending_purchases": self.pending_purchases,
            "pending_contracts": self.pending_contracts,
            "owned_artifacts": self.owned_artifacts,
            **self.extra,
        }


@dataclass
class ReflexResult:
    """Result from reflex execution."""

    # Action to execute (None = fall back to LLM)
    action: dict[str, Any] | None = None

    # Whether reflex fired (vs error/timeout)
    fired: bool = False

    # Error message if execution failed
    error: str | None = None

    # Execution time in milliseconds
    execution_time_ms: float = 0.0


class ReflexExecutor:
    """Executes reflex code in a sandboxed environment.

    The executor runs reflex code with a strict timeout to ensure
    fast execution. If the reflex times out or errors, it returns
    None to fall back to LLM reasoning.

    Security note: Reflex code runs in a restricted environment
    with limited built-ins. It cannot import modules or access
    the filesystem directly.
    """

    def __init__(
        self,
        timeout_ms: float | None = None,
        allowed_builtins: set[str] | None = None,
    ):
        """Initialize executor.

        Args:
            timeout_ms: Execution timeout in milliseconds (default from config)
            allowed_builtins: Set of allowed built-in names (default: safe set)
        """
        reflex_config = get("reflex", {})
        self.timeout_ms = timeout_ms or reflex_config.get("timeout_ms", 100.0)
        self.timeout_seconds = self.timeout_ms / 1000.0

        # Safe built-ins that reflexes can use
        self.allowed_builtins = allowed_builtins or {
            # Basic types
            "True",
            "False",
            "None",
            # Comparison
            "abs",
            "all",
            "any",
            "bool",
            "int",
            "float",
            "str",
            "len",
            "min",
            "max",
            "sum",
            "round",
            # Collections
            "list",
            "dict",
            "set",
            "tuple",
            "range",
            "enumerate",
            "zip",
            "sorted",
            "reversed",
            # Type checking
            "isinstance",
            "type",
            "hasattr",
            "getattr",
        }

    def execute(
        self,
        reflex_code: str,
        context: ReflexContext,
    ) -> ReflexResult:
        """Execute reflex code and return result.

        Args:
            reflex_code: Python code containing a `reflex(context)` function
            context: ReflexContext with agent state

        Returns:
            ReflexResult with action (or None) and execution metadata
        """
        import time

        start_time = time.perf_counter()

        try:
            # Build restricted globals
            restricted_builtins = {
                name: getattr(__builtins__ if isinstance(__builtins__, dict) else __builtins__, name, None)
                for name in self.allowed_builtins
                if hasattr(__builtins__ if isinstance(__builtins__, dict) else __builtins__, name)
            }

            # Handle case where __builtins__ is a dict (not a module)
            if isinstance(__builtins__, dict):
                for name in self.allowed_builtins:
                    if name in __builtins__:
                        restricted_builtins[name] = __builtins__[name]

            # Add safe built-ins as a dict
            safe_globals: dict[str, Any] = {
                "__builtins__": restricted_builtins,
                "__name__": "__reflex__",
            }

            # Compile the reflex code
            try:
                compiled = compile(reflex_code, "<reflex>", "exec")
            except SyntaxError as e:
                return ReflexResult(
                    error=f"Syntax error in reflex code: {e}",
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                )

            # Execute with timeout (Unix only - Windows doesn't support SIGALRM)
            if sys.platform != "win32":
                # Set up timeout handler
                def timeout_handler(signum: int, frame: Any) -> None:
                    raise ReflexTimeoutError(
                        f"Reflex execution timed out after {self.timeout_ms}ms"
                    )

                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.setitimer(signal.ITIMER_REAL, self.timeout_seconds)

            try:
                # Execute the reflex code to define the function
                exec(compiled, safe_globals)

                # Check that reflex function was defined
                if "reflex" not in safe_globals:
                    return ReflexResult(
                        error="Reflex code must define a 'reflex(context)' function",
                        execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    )

                reflex_fn = safe_globals["reflex"]
                if not callable(reflex_fn):
                    return ReflexResult(
                        error="'reflex' must be a callable function",
                        execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    )

                # Call the reflex function
                result = reflex_fn(context.to_dict())

            finally:
                if sys.platform != "win32":
                    # Cancel the timer and restore old handler
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    signal.signal(signal.SIGALRM, old_handler)

            execution_time_ms = (time.perf_counter() - start_time) * 1000

            # Validate result
            if result is None:
                # Reflex chose not to act - fall back to LLM
                return ReflexResult(
                    action=None,
                    fired=False,
                    execution_time_ms=execution_time_ms,
                )

            if not isinstance(result, dict):
                return ReflexResult(
                    error=f"Reflex must return dict or None, got {type(result).__name__}",
                    execution_time_ms=execution_time_ms,
                )

            # Validate action has required fields
            if "action_type" not in result:
                return ReflexResult(
                    error="Reflex action must have 'action_type' field",
                    execution_time_ms=execution_time_ms,
                )

            return ReflexResult(
                action=result,
                fired=True,
                execution_time_ms=execution_time_ms,
            )

        except ReflexTimeoutError as e:
            return ReflexResult(
                error=str(e),
                execution_time_ms=self.timeout_ms,
            )
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"Reflex execution error: {e}")
            return ReflexResult(
                error=f"Reflex execution error: {e}",
                execution_time_ms=execution_time_ms,
            )


def build_reflex_context(
    agent_id: str,
    world: World,
    recent_events_limit: int = 10,
) -> ReflexContext:
    """Build reflex context from world state.

    This function extracts a fast-to-compute subset of world state
    for reflex decision-making.

    Args:
        agent_id: ID of the agent
        world: World instance
        recent_events_limit: Max number of recent events to include

    Returns:
        ReflexContext ready for reflex execution
    """
    # Get balance
    balance = world.ledger.get_scrip(agent_id)

    # Get recent events from event log
    recent_events: list[dict[str, Any]] = []
    event_log = world.artifacts.get("genesis_event_log")
    if event_log and event_log.executable:
        try:
            # Read recent events
            result = world.executor.invoke(
                artifact_id="genesis_event_log",
                method="read",
                args={"limit": recent_events_limit},
                caller_id=agent_id,
            )
            if result.success and result.data:
                recent_events = result.data.get("events", [])
        except Exception as e:
            logger.debug(f"Could not fetch recent events: {e}")

    # Get owned artifacts
    owned_artifacts: list[str] = []
    for artifact in world.artifacts.list_all():
        if artifact.created_by == agent_id:
            owned_artifacts.append(artifact.id)

    # Get pending escrow deals (if escrow exists)
    pending_purchases: list[dict[str, Any]] = []
    escrow = world.artifacts.get("genesis_escrow")
    if escrow and escrow.executable:
        try:
            result = world.executor.invoke(
                artifact_id="genesis_escrow",
                method="my_deals",
                args={},
                caller_id=agent_id,
            )
            if result.success and result.data:
                deals = result.data.get("deals", [])
                # Filter for pending deals where agent is seller
                pending_purchases = [
                    d for d in deals
                    if d.get("status") == "pending" and d.get("seller_id") == agent_id
                ]
        except Exception as e:
            logger.debug(f"Could not fetch escrow deals: {e}")

    # Get resource quotas (simplified)
    llm_tokens_remaining = 0
    disk_remaining = 0
    try:
        rights_registry = world.artifacts.get("genesis_rights_registry")
        if rights_registry and rights_registry.executable:
            result = world.executor.invoke(
                artifact_id="genesis_rights_registry",
                method="check_quota",
                args={"principal_id": agent_id, "resource": "llm_tokens"},
                caller_id=agent_id,
            )
            if result.success and result.data:
                llm_tokens_remaining = result.data.get("remaining", 0)

            result = world.executor.invoke(
                artifact_id="genesis_rights_registry",
                method="check_quota",
                args={"principal_id": agent_id, "resource": "disk"},
                caller_id=agent_id,
            )
            if result.success and result.data:
                disk_remaining = result.data.get("remaining", 0)
    except Exception as e:
        logger.debug(f"Could not fetch quotas: {e}")

    return ReflexContext(
        agent_id=agent_id,
        tick=world.tick,
        balance=balance,
        llm_tokens_remaining=llm_tokens_remaining,
        disk_remaining=disk_remaining,
        recent_events=recent_events,
        pending_purchases=pending_purchases,
        owned_artifacts=owned_artifacts,
    )


def validate_reflex_code(code: str) -> tuple[bool, str | None]:
    """Validate reflex code without executing it.

    Checks that:
    1. Code is syntactically valid Python
    2. Code defines a 'reflex' function

    Args:
        code: Python code to validate

    Returns:
        (is_valid, error_message)
    """
    import ast

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Check for reflex function definition
    has_reflex_fn = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "reflex":
            has_reflex_fn = True
            # Check it has exactly one argument
            if len(node.args.args) != 1:
                return False, "reflex function must take exactly one argument (context)"
            break

    if not has_reflex_fn:
        return False, "Code must define a 'reflex(context)' function"

    return True, None
