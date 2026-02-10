"""SafeExecutor - Execution of agent-created code

Uses standard Python exec() with:
- Pre-loaded modules available without import (configurable in config.yaml)
- Controlled globals namespace
- Timeout protection (configurable via signal)

NOTE: This is NOT a security sandbox. Agents CAN import any stdlib module.
The preloaded_imports config just makes common modules available without
explicit import statements. Security boundary is the container (Docker
non-root user), not code-level restrictions. See docs/SECURITY.md.
"""

from __future__ import annotations

import builtins
import json
import logging
import math
import random
import signal
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import FrameType, ModuleType
from typing import Any, Callable, Generator, TypedDict

from ..config import get, get_validated_config

# Pre-import litellm at module level to ensure full initialization.
# Without this, first import inside an async executor context leaves
# litellm partially initialized (circular import in submodules).
try:
    import litellm  # noqa: F401
except ImportError:
    pass  # litellm optional if no agents use can_call_llm
from .simulation_engine import measure_resources

# Import types for type hints (avoid circular import at runtime)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .ledger import Ledger
    from .artifacts import Artifact, ArtifactStore
    from .world import World
    from .contracts import PermissionCache

# Import contracts module for permission checking
from .contracts import (
    AccessContract,
    ExecutableContract,
    PermissionAction,
    PermissionResult,
)
# Import from permission_checker module (Plan #181: Split Large Files)
from . import permission_checker as _permission_checker

# Import from interface_validation module (Plan #181: Split Large Files)
from .interface_validation import (
    ValidationResult,
    convert_positional_to_named_args,
    convert_named_to_positional_args,
    validate_args_against_interface,
)

# Import from invoke_handler module (Plan #181: Split Large Files)
from .invoke_handler import create_invoke_function

# Explicit re-exports for mypy --strict (used by action_executor.py)
__all__ = [
    "get_executor",
    "validate_args_against_interface",
    "convert_positional_to_named_args",
    "convert_named_to_positional_args",
    "parse_json_args",
    "ValidationResult",
    "SafeExecutor",
]

logger = logging.getLogger(__name__)


class PaymentResult(TypedDict):
    """Result from a pay() call within artifact execution."""
    success: bool
    amount: int
    target: str
    error: str


class InvokeResult(TypedDict):
    """Result from an invoke() call within artifact execution."""
    success: bool
    result: Any
    error: str
    price_paid: int


class LLMSyscallResult(TypedDict):
    """Result from _syscall_llm kernel primitive (Plan #255)."""
    success: bool
    content: str
    usage: dict[str, Any]
    cost: float
    error: str


def create_syscall_llm(
    world: "World",
    caller_id: str,
) -> Callable[[str, list[dict[str, Any]]], LLMSyscallResult]:
    """Create _syscall_llm function for artifact sandbox (Plan #255).

    This is the kernel primitive for LLM access. It:
    1. Checks caller's llm_budget (ADR-0002: no compute debt)
    2. Calls LLM via llm_client.call_llm
    3. Deducts actual cost from caller's budget (ADR-0011/0023)
    4. Returns response

    The Universal Bridge Pattern: This is the template for all external
    API access (search, GitHub, etc.). The kernel provides the syscall,
    a gateway artifact wraps it.

    Args:
        world: World instance for ledger access
        caller_id: Principal ID who pays for the call

    Returns:
        _syscall_llm function that can be injected into artifact sandbox
    """
    def _syscall_llm(
        model: str,
        messages: list[dict[str, Any]],
    ) -> LLMSyscallResult:
        """Kernel syscall for LLM access (Plan #255).

        Deducts llm_budget from caller automatically. Only available to
        artifacts with can_call_llm capability.

        Args:
            model: LLM model name (e.g., "gpt-4", "gemini/gemini-2.0-flash")
            messages: Chat messages in OpenAI format

        Returns:
            LLMSyscallResult with content, usage, and cost
        """
        # Estimate cost (rough: $0.001 per message as minimum)
        # Real cost will be calculated after the call
        estimated_cost = max(0.001, len(messages) * 0.0005)

        # Check budget (ADR-0002: no compute debt — validate before execution)
        if not world.ledger.can_afford_llm_call(caller_id, estimated_cost):
            current_budget = world.ledger.get_llm_budget(caller_id)
            return LLMSyscallResult(
                success=False,
                content="",
                usage={},
                cost=0.0,
                error=f"Budget exhausted: {caller_id} has ${current_budget:.4f}, need ~${estimated_cost:.4f}",
            )

        try:
            from .llm_client import call_llm

            # Call litellm directly — litellm.completion() is synchronous
            # and works fine in async contexts despite event loop detection
            llm_result = call_llm(model=model, messages=messages, timeout=60)

            actual_cost = llm_result.cost

            # Deduct from caller's budget (ADR-0011/0023: charges to principals)
            world.ledger.deduct_llm_cost(caller_id, actual_cost)

            return LLMSyscallResult(
                success=True,
                content=llm_result.content,
                usage=llm_result.usage,
                cost=actual_cost,
                error="",
            )

        except Exception as e:
            return LLMSyscallResult(
                success=False,
                content="",
                usage={},
                cost=0.0,
                error=f"LLM call failed: {e}",
            )

    return _syscall_llm


def get_max_invoke_depth() -> int:
    """Get max recursion depth for nested invoke() calls from config."""
    return get_validated_config().executor.max_invoke_depth


def get_max_contract_depth() -> int:
    """Get max recursion depth for contract permission checks from config.

    This limits how deep permission check chains can go to prevent
    infinite recursion. Per Plan #100 and ADR-0018, default is 10.

    Plan #181: Delegates to permission_checker module.
    """
    return _permission_checker.get_max_contract_depth()


def _format_runtime_error(e: Exception, prefix: str = "Runtime error") -> str:
    """Format a runtime error with helpful hints for common issues.

    Plan #160: Help agents recover from common errors by suggesting fixes.

    Args:
        e: The exception that occurred
        prefix: Error prefix like "Runtime error" or "Execution error"
    """
    error_type = type(e).__name__
    error_msg = str(e)
    base = f"{prefix}: {error_type}: {error_msg}"

    # Add hints based on error type
    if isinstance(e, ModuleNotFoundError):
        # Extract module name from error message
        module = error_msg.replace("No module named ", "").strip("'\"")
        return (
            f"{base}. "
            f"Hint: Use kernel_actions.install_library('{module}') to install it, "
            f"or use a simpler approach without this library."
        )
    elif isinstance(e, AttributeError) and "has no attribute" in error_msg:
        return (
            f"{base}. "
            f"Hint: Check the object's available methods. "
            f"Use dir(obj) or read the artifact's interface."
        )
    elif isinstance(e, KeyError):
        return (
            f"{base}. "
            f"Hint: The key doesn't exist. Check dict.keys() or use dict.get(key, default)."
        )
    elif isinstance(e, TypeError) and "argument" in error_msg.lower():
        if "missing" in error_msg.lower() and "required" in error_msg.lower():
            return (
                f"{base}. "
                f"Hint: Your run() function expects more arguments than were passed. "
                f"Check your code's function signature matches the interface schema."
            )
        return (
            f"{base}. "
            f"Hint: Check the function signature - you may have wrong number/type of arguments."
        )
    elif isinstance(e, IndexError):
        return (
            f"{base}. "
            f"Hint: Your code tried to access an index that doesn't exist. "
            f"Check array/tuple lengths before accessing elements, or use try/except."
        )
    elif "connection" in error_msg.lower() or "adapter" in error_msg.lower():
        return (
            f"{base}. "
            f"Hint: For HTTP requests, use requests.get(url) where url is a plain string, "
            f"not url='...' keyword syntax."
        )

    return base


def parse_json_args(args: list[Any]) -> list[Any]:
    """Parse JSON strings in args to Python objects.

    LLMs often generate JSON strings for dict arguments (e.g., '{"id": "foo"}').
    This auto-converts them to proper Python types before passing to artifacts.

    Plan #112: Fixes repeated 'str' object has no attribute 'get' errors.
    Plan #160: Now exported for use before interface validation.

    Args:
        args: List of arguments, some may be JSON strings

    Returns:
        List with JSON strings parsed to dicts/lists where valid.
        Plain strings and non-JSON values pass through unchanged.
    """
    parsed: list[Any] = []
    for arg in args:
        if isinstance(arg, str):
            try:
                result = json.loads(arg)
                # Only convert if result is dict or list
                # (avoid converting "123" to 123 or "true" to True)
                if isinstance(result, (dict, list)):
                    parsed.append(result)
                else:
                    parsed.append(arg)
            except (json.JSONDecodeError, ValueError):
                parsed.append(arg)
        else:
            parsed.append(arg)
    return parsed


class ExecutionResult(TypedDict, total=False):
    """Result from code execution.

    Includes resource consumption tracking for the two-layer model:
    - resources_consumed: Physical resources used (compute based on execution time)
    - execution_time_ms: Wall-clock time for execution
    """
    success: bool
    result: Any
    error: str
    resources_consumed: dict[str, float]
    execution_time_ms: float


# Note: ValidationResult, convert_positional_to_named_args,
# convert_named_to_positional_args, and validate_args_against_interface
# are now imported from interface_validation module (Plan #181)


# Create a simple datetime module-like object
class _DatetimeModule:
    """A simple namespace for datetime classes."""
    datetime: type[datetime] = datetime
    timedelta: type[timedelta] = timedelta


# Available modules that can be pre-loaded into execution namespace
AVAILABLE_MODULES: dict[str, ModuleType | _DatetimeModule] = {
    "math": math,
    "json": json,
    "random": random,
    "datetime": _DatetimeModule(),
}


def get_preloaded_modules() -> dict[str, ModuleType | _DatetimeModule]:
    """Get modules to pre-load into execution namespace.

    NOTE: This is NOT a security whitelist. Agents can still import
    any stdlib module via import statements. These modules are just
    made available without explicit import for convenience.
    """
    # Support both new name and legacy name for backward compatibility
    preloaded: list[str] = (
        get("executor.preloaded_imports") or
        get("executor.allowed_imports") or  # Legacy fallback
        ["math", "json", "random", "datetime"]
    )
    return {
        name: AVAILABLE_MODULES[name]
        for name in preloaded
        if name in AVAILABLE_MODULES
    }


class TimeoutError(Exception):
    """Code execution timed out"""
    pass


class DependencyWrapper:
    """Wrapper for a declared dependency that enables invoke() calls.

    Plan #63: Artifact Dependencies - provides a callable wrapper for
    dependencies so artifacts can call `context.dependencies["foo"].invoke()`.
    """

    def __init__(
        self,
        artifact_id: str,
        invoke_func: "Callable[[str, Any], InvokeResult]",
    ):
        self.artifact_id = artifact_id
        self._invoke_func = invoke_func

    def invoke(self, *args: Any) -> InvokeResult:
        """Invoke this dependency with the given arguments."""
        return self._invoke_func(self.artifact_id, *args)


class ExecutionContext:
    """Context object passed to artifact code at execution time.

    Plan #63: Artifact Dependencies - provides access to resolved dependencies.

    Attributes:
        dependencies: Dict mapping dependency artifact IDs to DependencyWrapper objects
    """

    def __init__(self, dependencies: dict[str, DependencyWrapper] | None = None):
        self.dependencies: dict[str, DependencyWrapper] = dependencies or {}


def _timeout_handler(signum: int, frame: FrameType | None) -> None:
    raise TimeoutError("Execution timed out")


@contextmanager
def _timeout_context(timeout: int) -> Generator[None, None, None]:
    """Context manager for Unix signal-based timeout.

    On Windows/platforms without signal.alarm, silently does nothing.
    Properly restores the previous signal handler on exit.

    Args:
        timeout: Timeout in seconds

    Yields:
        None - just provides timeout protection for the block

    Raises:
        TimeoutError: If the block takes longer than timeout seconds
    """
    old_handler: Any = None
    try:
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
    except (ValueError, AttributeError):
        # signal.alarm not available (Windows) - skip timeout
        pass

    try:
        yield
    finally:
        try:
            signal.alarm(0)
            if old_handler:
                signal.signal(signal.SIGALRM, old_handler)
        except (ValueError, AttributeError):
            pass


def _make_controlled_import(
    allowed_modules: dict[str, ModuleType | _DatetimeModule]
) -> Any:
    """Create an import function that allows whitelisted modules."""
    def _controlled_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0
    ) -> ModuleType | _DatetimeModule:
        """Import that allows whitelisted modules."""
        if name in allowed_modules:
            return allowed_modules[name]
        # Allow standard library imports for full functionality
        return builtins.__import__(name, globals, locals, fromlist, level)
    return _controlled_import


class SafeExecutor:
    """
    Executes agent-created code with timeout protection.

    Code must define a `run(*args)` function that will be called.

    Features:
    - Standard Python exec() with controlled namespace
    - Common modules pre-loaded (configurable via preloaded_imports)
    - Execution timeout (configurable)
    - Full Python capability - agents CAN import any stdlib module
    - Contract-based permission checking (when use_contracts=True)

    NOTE: This is NOT a security sandbox. Security boundary is the
    container (Docker non-root user), not code-level restrictions.
    See docs/SECURITY.md for rationale.
    """

    timeout: int
    preloaded_modules: dict[str, ModuleType | _DatetimeModule]
    use_contracts: bool
    max_contract_depth: int
    _contract_cache: dict[str, AccessContract | ExecutableContract]
    _ledger: "Ledger | None"
    _artifact_store: "ArtifactStore | None"
    _permission_cache: "PermissionCache"
    _dangling_contract_count: int

    def __init__(
        self,
        timeout: int | None = None,
        use_contracts: bool = True,
        ledger: "Ledger | None" = None,
        max_contract_depth: int | None = None,
    ) -> None:
        default_timeout: int = get("executor.timeout_seconds") or 5
        self.timeout = timeout or default_timeout
        self.preloaded_modules = get_preloaded_modules()
        self.use_contracts = use_contracts
        self.max_contract_depth = max_contract_depth if max_contract_depth is not None else get_max_contract_depth()
        self._contract_cache = {}
        self._ledger = ledger
        self._artifact_store = None
        # Permission cache for TTL-based caching (Plan #100 Phase 2)
        from src.world.contracts import PermissionCache
        self._permission_cache = PermissionCache()
        # Dangling contract counter for observability (Plan #100 Phase 2, ADR-0017)
        self._dangling_contract_count = 0

    def set_ledger(self, ledger: "Ledger") -> None:
        """Set the ledger for executable contract permission checks.

        Executable contracts may need read-only ledger access to check
        balances for pay-per-use or balance-gated access patterns.

        Args:
            ledger: The ledger instance to use
        """
        self._ledger = ledger

    def set_artifact_store(self, artifact_store: "ArtifactStore") -> None:
        """Set the artifact store for applying contract state_updates.

        Plan #311: Contracts can return state_updates in PermissionResult.
        The kernel applies these to artifact.state after permission checks.
        Requires access to the ArtifactStore to look up the target artifact.

        Args:
            artifact_store: The ArtifactStore instance to use
        """
        self._artifact_store = artifact_store

    def clear_permission_cache(self) -> None:
        """Clear all cached permission results.

        Useful when contracts are updated or for testing.
        Plan #100 Phase 2: TTL-based permission caching.
        """
        self._permission_cache.clear()

    def get_dangling_contract_count(self) -> int:
        """Get count of dangling contract fallbacks that have occurred.

        Plan #100 Phase 2, ADR-0017: Observable degradation for dangling contracts.
        """
        return self._dangling_contract_count

    def _get_contract_with_fallback_info(
        self, contract_id: str
    ) -> tuple[AccessContract | ExecutableContract, bool, str | None]:
        """Get contract by ID, with info about whether fallback was used.

        Checks genesis contracts first, then falls back to configurable
        default if not found. Also supports ExecutableContracts registered
        via register_executable_contract().

        Plan #100 Phase 2, ADR-0017: Dangling contracts fail open to default.
        Plan #181: Delegates to permission_checker module.

        Args:
            contract_id: The contract ID to look up

        Returns:
            Tuple of (contract, is_fallback, original_contract_id)
            - contract: The contract instance (never None)
            - is_fallback: True if this is a fallback due to missing contract
            - original_contract_id: The original ID if fallback occurred, else None
        """
        # Use a mutable tracker so the module can increment the count
        dangling_tracker = [self._dangling_contract_count]
        result = _permission_checker.get_contract_with_fallback_info(
            contract_id, self._contract_cache, dangling_tracker
        )
        # Update instance state from tracker
        self._dangling_contract_count = dangling_tracker[0]
        return result

    def register_executable_contract(self, contract: ExecutableContract) -> None:
        """Register an executable contract for use in permission checks.

        Executable contracts have dynamic code that runs in a sandbox to
        determine permissions. They can access ledger balances (read-only)
        for pay-per-use or balance-gated access patterns.

        Args:
            contract: The ExecutableContract to register
        """
        self._contract_cache[contract.contract_id] = contract

    def _check_permission_via_contract(
        self,
        caller: str,
        action: str,
        artifact: "Artifact",
        contract_depth: int = 0,
        method: str | None = None,
        args: list[Any] | None = None,
    ) -> PermissionResult:
        """Check permission using artifact's access contract.

        Supports both genesis contracts (static logic) and executable
        contracts (dynamic code). Executable contracts receive read-only
        ledger access for balance checks.

        Plan #100 Phase 2: Supports TTL-based caching for contracts with
        cache_policy. Caching is opt-in - contracts without cache_policy
        are never cached.
        Plan #181: Delegates to permission_checker module.

        Args:
            caller: The principal requesting access
            action: The action being attempted (read, write, invoke, etc.)
            artifact: The artifact being accessed
            contract_depth: Current depth of permission check chain (default 0).
                Per Plan #100, prevents infinite recursion in permission checks.

        Returns:
            PermissionResult with allowed, reason, and optional cost
        """
        # Use a mutable tracker so the module can increment the count
        dangling_tracker = [self._dangling_contract_count]
        result = _permission_checker.check_permission_via_contract(
            caller=caller,
            action=action,
            artifact=artifact,
            contract_cache=self._contract_cache,
            permission_cache=self._permission_cache,
            dangling_count_tracker=dangling_tracker,
            ledger=self._ledger,
            max_contract_depth=self.max_contract_depth,
            contract_depth=contract_depth,
            method=method,
            args=args,
            artifact_store=self._artifact_store,
        )
        # Update instance state from tracker
        self._dangling_contract_count = dangling_tracker[0]
        return result

    def _check_permission(
        self,
        caller: str,
        action: str,
        artifact: "Artifact",
        method: str | None = None,
        args: list[Any] | None = None,
    ) -> "PermissionResult":
        """Check if caller has permission for action on artifact.

        Permission checking follows ADR-0019:
        1. If access_contract_id is set: use that contract
        2. If access_contract_id is NULL: use configurable default (creator_only or freeware)
        3. If access_contract_id points to deleted contract: use default_on_missing

        Plan #181: Delegates to permission_checker module.

        Returns:
            PermissionResult with allowed, reason, cost, recipient, etc.
        """
        # Use a mutable tracker so the module can increment the count
        dangling_tracker = [self._dangling_contract_count]
        result = _permission_checker.check_permission(
            caller=caller,
            action=action,
            artifact=artifact,
            contract_cache=self._contract_cache,
            permission_cache=self._permission_cache,
            dangling_count_tracker=dangling_tracker,
            ledger=self._ledger,
            max_contract_depth=self.max_contract_depth,
            use_contracts=self.use_contracts,
            method=method,
            args=args,
            artifact_store=self._artifact_store,
        )
        # Update instance state from tracker
        self._dangling_contract_count = dangling_tracker[0]
        return result

    def validate_code(self, code: str) -> tuple[bool, str]:
        """
        Validate that code can be compiled and has a recognized entry point.

        Plan #234: Accept handle_request(caller, operation, args) as alternative
        to run() for ADR-0024 artifact-handled access control.
        Plan #317: Accept check_permission() for contract artifacts.

        Returns:
            (success, error_message)
        """
        if not code or not code.strip():
            return False, "Empty code"

        # Check for recognized entry point function definition
        has_run = "def run(" in code
        has_handle_request = "def handle_request(" in code
        has_check_permission = "def check_permission(" in code
        if not has_run and not has_handle_request and not has_check_permission:
            return False, "Code must define a run(), handle_request(), or check_permission() function"

        # Try to compile with standard Python
        try:
            compile(code, '<agent_code>', 'exec')
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:  # exception-ok: user code can raise anything
            return False, f"Compilation failed: {e}"

    def execute(self, code: str, args: list[Any] | None = None) -> ExecutionResult:
        """
        Execute code and call run(*args).

        Args:
            code: Python code defining a run() function
            args: Arguments to pass to run()

        Returns:
            Dict with:
            - success: bool
            - result: return value from run() (if success)
            - error: error message (if failed)
        """
        args = args or []

        # Validate first
        valid, error = self.validate_code(code)
        if not valid:
            return {"success": False, "error": error}

        # Compile with standard Python
        try:
            compiled = compile(code, '<agent_code>', 'exec')
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}"}
        except Exception as e:  # exception-ok: user code can raise anything
            return {"success": False, "error": f"Compilation failed: {e}"}

        # Build controlled globals with full builtins and allowed modules
        controlled_builtins = dict(vars(builtins))
        controlled_builtins["__import__"] = _make_controlled_import(
            self.preloaded_modules
        )

        controlled_globals: dict[str, Any] = {
            "__builtins__": controlled_builtins,
            "__name__": "__main__",
        }

        # Add allowed modules to namespace (so they can be used without import)
        for name, module in self.preloaded_modules.items():
            controlled_globals[name] = module

        # Plan #140: Create Action class for agent-expected API
        # In this simple execute() context, most methods return errors
        class Action:
            """Agent-friendly wrapper (limited context version)."""

            def invoke_artifact(
                self,
                artifact_id: str,
                method: str = "run",
                args: list[Any] | None = None
            ) -> dict[str, Any]:
                return {
                    "success": False,
                    "error": "invoke not available in this context",
                    "result": None,
                    "price_paid": 0
                }

            def pay(self, target: str, amount: int) -> dict[str, Any]:
                return {"success": False, "error": "pay not available"}

            def get_balance(self) -> int:
                return 0

            def get_kernel_state(self) -> Any:
                return None

            def read_artifact(self, artifact_id: str) -> dict[str, Any]:
                return {"success": False, "error": "read_artifact not available in this context"}

        # Inject actions module
        actions_module = ModuleType("actions")
        actions_module.Action = Action  # type: ignore[attr-defined]
        sys.modules["actions"] = actions_module
        controlled_globals["Action"] = Action

        # Execute the code definition (creates the run function)
        # Use single namespace so imports work correctly
        try:
            with _timeout_context(self.timeout):
                exec(compiled, controlled_globals)
        except TimeoutError:
            return {"success": False, "error": "Code definition timed out"}
        except Exception as e:  # exception-ok: user code can raise anything
            return {
                "success": False,
                "error": _format_runtime_error(e, "Execution error")
            }

        # Check that run() was defined
        if "run" not in controlled_globals:
            return {"success": False, "error": "Code did not define a run() function"}

        run_func = controlled_globals["run"]
        if not callable(run_func):
            return {"success": False, "error": "run is not callable"}

        # Plan #112: Parse JSON strings in args to Python objects
        args = parse_json_args(args)

        # Call run() with args, measuring resource usage via ResourceMeasurer
        start_time = time.perf_counter()
        execution_time_ms: float = 0.0
        result: Any = None
        error_result: ExecutionResult | None = None

        # Use ResourceMeasurer for accurate CPU time measurement
        with measure_resources() as measurer:
            try:
                with _timeout_context(self.timeout):
                    result = run_func(*args)
                    execution_time_ms = (time.perf_counter() - start_time) * 1000
            except TimeoutError:
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                error_result = {
                    "success": False,
                    "error": "Execution timed out",
                    "execution_time_ms": execution_time_ms,
                }
            except TypeError as e:
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                error_result = {
                    "success": False,
                    "error": f"Argument error: {e}",
                    "execution_time_ms": execution_time_ms,
                }
            except Exception as e:  # exception-ok: user code can raise anything
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                error_result = {
                    "success": False,
                    "error": _format_runtime_error(e),
                    "execution_time_ms": execution_time_ms,
                }

        # Get resource usage after exiting context manager
        usage = measurer.get_usage()
        resources_consumed = {"cpu_seconds": usage.cpu_seconds}

        # Return error if one occurred
        if error_result is not None:
            error_result["resources_consumed"] = resources_consumed
            return error_result

        # Ensure result is JSON-serializable
        try:
            json.dumps(result)
        except (TypeError, ValueError):
            # Convert to string if not serializable
            result = str(result)

        return {
            "success": True,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "resources_consumed": resources_consumed,
        }

    def execute_with_wallet(
        self,
        code: str,
        args: list[Any] | None = None,
        artifact_id: str | None = None,
        ledger: "Ledger | None" = None,
    ) -> ExecutionResult:
        """
        Execute code with pay() capability for artifact wallets.

        When artifact_id and ledger are provided, injects a pay(target, amount)
        function that allows the artifact to spend from its own wallet.

        Args:
            code: Python code defining a run() function
            args: Arguments to pass to run()
            artifact_id: ID of the artifact (for wallet access)
            ledger: Ledger instance for transfers

        Returns:
            Same as execute() - dict with success, result/error
        """
        args = args or []

        # Validate first
        valid, error = self.validate_code(code)
        if not valid:
            return {"success": False, "error": error}

        # Compile with standard Python
        try:
            compiled = compile(code, '<agent_code>', 'exec')
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}"}
        except Exception as e:  # exception-ok: user code can raise anything
            return {"success": False, "error": f"Compilation failed: {e}"}

        # Build controlled globals with full builtins and allowed modules
        controlled_builtins = dict(vars(builtins))
        controlled_builtins["__import__"] = _make_controlled_import(
            self.preloaded_modules
        )

        controlled_globals: dict[str, Any] = {
            "__builtins__": controlled_builtins,
            "__name__": "__main__",
        }

        # Add allowed modules to namespace
        for name, module in self.preloaded_modules.items():
            controlled_globals[name] = module

        # Track payments made during execution
        payments_made: list[PaymentResult] = []

        # Create pay() function if wallet context provided
        if artifact_id and ledger:
            def pay(target: str, amount: int) -> PaymentResult:
                """Transfer scrip from this artifact's wallet to target.

                Can ONLY spend from this artifact's own balance.
                Returns dict with success status.
                """
                if amount <= 0:
                    result: PaymentResult = {
                        "success": False,
                        "amount": amount,
                        "target": target,
                        "error": "Amount must be positive"
                    }
                    payments_made.append(result)
                    return result

                # Transfer from artifact's wallet
                success = ledger.transfer_scrip(artifact_id, target, amount)
                if success:
                    result = {
                        "success": True,
                        "amount": amount,
                        "target": target,
                        "error": ""
                    }
                else:
                    result = {
                        "success": False,
                        "amount": amount,
                        "target": target,
                        "error": "Insufficient funds in artifact wallet"
                    }
                payments_made.append(result)
                return result

            def get_balance() -> int:
                """Get this artifact's current scrip balance."""
                return ledger.get_scrip(artifact_id)

            # Inject wallet functions into namespace
            controlled_globals["pay"] = pay
            controlled_globals["get_balance"] = get_balance

        # Execute the code definition
        try:
            with _timeout_context(self.timeout):
                exec(compiled, controlled_globals)
        except TimeoutError:
            return {"success": False, "error": "Code definition timed out"}
        except Exception as e:  # exception-ok: user code can raise anything
            return {
                "success": False,
                "error": _format_runtime_error(e, "Execution error")
            }

        # Check that run() was defined
        if "run" not in controlled_globals:
            return {"success": False, "error": "Code did not define a run() function"}

        run_func = controlled_globals["run"]
        if not callable(run_func):
            return {"success": False, "error": "run is not callable"}

        # Plan #112: Parse JSON strings in args to Python objects
        args = parse_json_args(args)

        # Call run() with args, measuring resource usage via ResourceMeasurer
        start_time = time.perf_counter()
        execution_time_ms: float = 0.0
        result: Any = None
        error_result: ExecutionResult | None = None

        # Use ResourceMeasurer for accurate CPU time measurement
        with measure_resources() as measurer:
            try:
                with _timeout_context(self.timeout):
                    result = run_func(*args)
                    execution_time_ms = (time.perf_counter() - start_time) * 1000
            except TimeoutError:
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                error_result = {
                    "success": False,
                    "error": "Execution timed out",
                    "execution_time_ms": execution_time_ms,
                }
            except TypeError as e:
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                error_result = {
                    "success": False,
                    "error": f"Argument error: {e}",
                    "execution_time_ms": execution_time_ms,
                }
            except Exception as e:  # exception-ok: user code can raise anything
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                error_result = {
                    "success": False,
                    "error": _format_runtime_error(e),
                    "execution_time_ms": execution_time_ms,
                }

        # Get resource usage after exiting context manager
        usage = measurer.get_usage()
        resources_consumed = {"cpu_seconds": usage.cpu_seconds}

        # Return error if one occurred
        if error_result is not None:
            error_result["resources_consumed"] = resources_consumed
            return error_result

        # Ensure result is JSON-serializable
        try:
            json.dumps(result)
        except (TypeError, ValueError):
            result = str(result)

        return {
            "success": True,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "resources_consumed": resources_consumed,
        }

    def execute_with_invoke(
        self,
        code: str,
        args: list[Any] | None = None,
        caller_id: str | None = None,
        artifact_id: str | None = None,
        ledger: "Ledger | None" = None,
        artifact_store: "ArtifactStore | None" = None,
        current_depth: int = 0,
        max_depth: int | None = None,
        world: "World | None" = None,
        entry_point: str = "run",
        method_name: str | None = None,
    ) -> ExecutionResult:
        """
        Execute code with invoke() capability for artifact composition.

        Injects invoke(artifact_id, *args) function that allows artifacts to
        call other artifacts. Also includes pay() and get_balance() from
        execute_with_wallet.

        When `world` is provided, also injects kernel interfaces for equal access:
        - kernel_state: Read-only access to ledger, resources, artifacts
        - kernel_actions: Write access (transfers, artifact writes)
        - caller_id: The ID of the invoking principal

        Args:
            code: Python code defining a run() or handle_request() function
            args: Arguments to pass to run() or handle_request()
            caller_id: ID of the original caller (pays for nested invocations)
            artifact_id: ID of this artifact (for wallet access)
            ledger: Ledger instance for transfers
            artifact_store: ArtifactStore for looking up artifacts
            current_depth: Current recursion depth (for preventing infinite loops)
            max_depth: Maximum allowed recursion depth
            world: World instance for kernel interface injection (Plan #39)
            entry_point: "run" for legacy run(*args), "handle_request" for
                ADR-0024 handle_request(caller, operation, args) (Plan #234)
            method_name: Operation name passed to handle_request (Plan #234)

        Returns:
            Same as execute() - dict with success, result/error
        """
        args = args or []
        if max_depth is None:
            max_depth = get_max_invoke_depth()

        # Validate first
        valid, error = self.validate_code(code)
        if not valid:
            return {"success": False, "error": error}

        # Compile with standard Python
        try:
            compiled = compile(code, '<agent_code>', 'exec')
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}"}
        except Exception as e:  # exception-ok: user code can raise anything
            return {"success": False, "error": f"Compilation failed: {e}"}

        # Build controlled globals with full builtins and allowed modules
        controlled_builtins = dict(vars(builtins))
        controlled_builtins["__import__"] = _make_controlled_import(
            self.preloaded_modules
        )

        controlled_globals: dict[str, Any] = {
            "__builtins__": controlled_builtins,
            "__name__": "__main__",
        }

        # Add allowed modules to namespace
        for name, module in self.preloaded_modules.items():
            controlled_globals[name] = module

        # Inject kernel interfaces if world is provided (Plan #39 - Genesis Unprivilege)
        # This gives all artifacts equal access to kernel state/actions
        if world is not None:
            from .kernel_interface import KernelState, KernelActions
            controlled_globals["kernel_state"] = KernelState(world)
            controlled_globals["kernel_actions"] = KernelActions(world)

        # Inject caller_id so artifacts know who invoked them
        if caller_id is not None:
            controlled_globals["caller_id"] = caller_id

        # Plan #255: Inject _syscall_llm for artifacts with can_call_llm capability
        # This is the Universal Bridge Pattern - kernel provides syscall, artifact wraps it
        if world is not None and artifact_id and artifact_store:
            artifact = artifact_store.get(artifact_id)
            if artifact and "can_call_llm" in artifact.capabilities:
                # Caller pays - use caller_id (the one who invoked this artifact)
                paying_principal = caller_id if caller_id else artifact_id
                controlled_globals["_syscall_llm"] = create_syscall_llm(world, paying_principal)

        # Track payments made during execution
        payments_made: list[PaymentResult] = []

        # Create pay() and get_balance() if wallet context provided
        if artifact_id and ledger:
            def pay(target: str, amount: int) -> PaymentResult:
                """Transfer scrip from this artifact's wallet to target."""
                if amount <= 0:
                    result: PaymentResult = {
                        "success": False,
                        "amount": amount,
                        "target": target,
                        "error": "Amount must be positive"
                    }
                    payments_made.append(result)
                    return result

                success = ledger.transfer_scrip(artifact_id, target, amount)
                if success:
                    result = {
                        "success": True,
                        "amount": amount,
                        "target": target,
                        "error": ""
                    }
                else:
                    result = {
                        "success": False,
                        "amount": amount,
                        "target": target,
                        "error": "Insufficient funds in artifact wallet"
                    }
                payments_made.append(result)
                return result

            def get_balance() -> int:
                """Get this artifact's current scrip balance."""
                return ledger.get_scrip(artifact_id)

            controlled_globals["pay"] = pay
            controlled_globals["get_balance"] = get_balance

        # Create invoke() function if full context provided
        # Plan #181: Use factory from invoke_handler module
        if caller_id and ledger and artifact_store:
            invoke = create_invoke_function(
                caller_id=caller_id,
                artifact_id=artifact_id,
                ledger=ledger,
                artifact_store=artifact_store,
                current_depth=current_depth,
                max_depth=max_depth,
                world=world,
                check_permission_func=self._check_permission,
                check_permission_via_contract_func=self._check_permission_via_contract,
                execute_with_invoke_func=self.execute_with_invoke,
                use_contracts=self.use_contracts,
            )
            controlled_globals["invoke"] = invoke

        # Plan #140: Create Action class that wraps injected functions
        # This matches the API pattern agents naturally expect: from actions import Action
        class Action:
            """Agent-friendly wrapper for sandbox functions.

            Agents naturally write code like:
                from actions import Action
                action = Action()
                result = action.invoke_artifact("target", args=[1, 2])

            This class provides that API by wrapping the bare functions.
            """

            def invoke_artifact(
                self,
                artifact_id: str,
                method: str = "run",
                args: list[Any] | None = None
            ) -> dict[str, Any]:
                """Invoke another artifact.

                Args:
                    artifact_id: ID of artifact to invoke
                    method: Method name (currently only "run" is supported)
                    args: Arguments to pass to run()

                Returns:
                    Dict with success, result, error, price_paid
                """
                if "invoke" not in controlled_globals:
                    return {
                        "success": False,
                        "error": "invoke not available in this context",
                        "result": None,
                        "price_paid": 0
                    }
                result: dict[str, Any] = controlled_globals["invoke"](artifact_id, *(args or []))
                return result

            def pay(self, target: str, amount: int) -> dict[str, Any]:
                """Transfer scrip to another principal.

                Args:
                    target: ID of recipient
                    amount: Amount to transfer

                Returns:
                    Dict with success and details
                """
                if "pay" not in controlled_globals:
                    return {"success": False, "error": "pay not available"}
                result: dict[str, Any] = controlled_globals["pay"](target, amount)
                return result

            def get_balance(self) -> int:
                """Get this artifact's current scrip balance."""
                if "get_balance" not in controlled_globals:
                    return 0
                balance: int = controlled_globals["get_balance"]()
                return balance

            def get_kernel_state(self) -> Any:
                """Get access to kernel_state for read operations."""
                return controlled_globals.get("kernel_state")

            def read_artifact(self, artifact_id: str) -> dict[str, Any]:
                """Read another artifact's content.

                Args:
                    artifact_id: ID of artifact to read

                Returns:
                    Dict with success, content, and artifact metadata
                """
                if artifact_store is None:
                    return {"success": False, "error": "read_artifact not available in this context"}

                target = artifact_store.get(artifact_id)
                if target is None:
                    return {"success": False, "error": f"Artifact {artifact_id} not found"}

                if target.deleted:
                    return {"success": False, "error": f"Artifact {artifact_id} has been deleted"}

                return {
                    "success": True,
                    "artifact_id": artifact_id,
                    "content": target.content,
                    "type": target.type,
                    "created_by": target.created_by,
                    "executable": target.executable,
                }

        # Inject actions module so "from actions import Action" works
        actions_module = ModuleType("actions")
        actions_module.Action = Action  # type: ignore[attr-defined]
        sys.modules["actions"] = actions_module
        controlled_globals["Action"] = Action  # Also available directly

        # Build execution context with resolved dependencies (Plan #63)
        if artifact_id and artifact_store:
            artifact = artifact_store.get(artifact_id)
            if artifact and artifact.depends_on:
                # Create dependency wrappers for each declared dependency
                dep_wrappers: dict[str, DependencyWrapper] = {}
                for dep_id in artifact.depends_on:
                    dep_artifact = artifact_store.get(dep_id)
                    if dep_artifact is None or dep_artifact.deleted:
                        # Dependency missing or deleted - fail early
                        return {
                            "success": False,
                            "error": f"Dependency '{dep_id}' not found or deleted",
                        }
                    # Create wrapper using the invoke function
                    if "invoke" in controlled_globals:
                        dep_wrappers[dep_id] = DependencyWrapper(
                            artifact_id=dep_id,
                            invoke_func=controlled_globals["invoke"],
                        )
                context = ExecutionContext(dependencies=dep_wrappers)
                controlled_globals["context"] = context
            else:
                # No dependencies - provide empty context
                controlled_globals["context"] = ExecutionContext()
        else:
            # No artifact store - provide empty context
            controlled_globals["context"] = ExecutionContext()

        # Execute the code definition
        try:
            with _timeout_context(self.timeout):
                exec(compiled, controlled_globals)
        except TimeoutError:
            return {"success": False, "error": "Code definition timed out"}
        except Exception as e:  # exception-ok: user code can raise anything
            return {
                "success": False,
                "error": _format_runtime_error(e, "Execution error")
            }

        # Plan #234: Resolve entry point function
        if entry_point == "handle_request":
            if "handle_request" not in controlled_globals:
                return {"success": False, "error": "Code did not define a handle_request() function"}
            entry_func = controlled_globals["handle_request"]
            if not callable(entry_func):
                return {"success": False, "error": "handle_request is not callable"}
        else:
            if "run" not in controlled_globals:
                return {"success": False, "error": "Code did not define a run() function"}
            entry_func = controlled_globals["run"]
            if not callable(entry_func):
                return {"success": False, "error": "run is not callable"}

        # Plan #112: Parse JSON strings in args to Python objects
        args = parse_json_args(args)

        # Call entry point, measuring resource usage via ResourceMeasurer
        start_time = time.perf_counter()
        execution_time_ms: float = 0.0
        result: Any = None
        error_result: ExecutionResult | None = None

        # Use ResourceMeasurer for accurate CPU time measurement
        with measure_resources() as measurer:
            try:
                with _timeout_context(self.timeout):
                    # Plan #234: handle_request receives (caller, operation, args)
                    if entry_point == "handle_request":
                        result = entry_func(
                            caller_id, method_name or "invoke", args
                        )
                    else:
                        result = entry_func(*args)
                    execution_time_ms = (time.perf_counter() - start_time) * 1000
            except TimeoutError:
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                error_result = {
                    "success": False,
                    "error": "Execution timed out",
                    "execution_time_ms": execution_time_ms,
                }
            except TypeError as e:
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                error_result = {
                    "success": False,
                    "error": f"Argument error: {e}",
                    "execution_time_ms": execution_time_ms,
                }
            except Exception as e:  # exception-ok: user code can raise anything
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                error_result = {
                    "success": False,
                    "error": _format_runtime_error(e),
                    "execution_time_ms": execution_time_ms,
                }

        # Get resource usage after exiting context manager
        usage = measurer.get_usage()
        resources_consumed = {"cpu_seconds": usage.cpu_seconds}

        # Return error if one occurred
        if error_result is not None:
            error_result["resources_consumed"] = resources_consumed
            return error_result

        # Ensure result is JSON-serializable
        try:
            json.dumps(result)
        except (TypeError, ValueError):
            result = str(result)

        return {
            "success": True,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "resources_consumed": resources_consumed,
        }


# Singleton instance
_executor: SafeExecutor | None = None


def get_executor(timeout: int | None = None) -> SafeExecutor:
    """Get or create the SafeExecutor singleton.

    Timeout defaults to config value if not specified.
    """
    global _executor
    if _executor is None or (timeout and timeout != _executor.timeout):
        _executor = SafeExecutor(timeout=timeout)
    return _executor
