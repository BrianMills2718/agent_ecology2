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
import time
from contextlib import contextmanager
from dataclasses import dataclass, replace as dataclass_replace
from datetime import datetime, timedelta
from types import FrameType, ModuleType
from typing import Any, Callable, Generator, TypedDict

import jsonschema

from ..config import get, get_validated_config
from .simulation_engine import measure_resources

# Import types for type hints (avoid circular import at runtime)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .ledger import Ledger
    from .artifacts import Artifact, ArtifactStore
    from .world import World

# Import contracts module for permission checking
from .contracts import (
    AccessContract,
    ExecutableContract,
    PermissionAction,
    PermissionResult,
)
from .genesis_contracts import get_contract_by_id, get_genesis_contract


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


def get_max_invoke_depth() -> int:
    """Get max recursion depth for nested invoke() calls from config."""
    return get_validated_config().executor.max_invoke_depth


def get_max_contract_depth() -> int:
    """Get max recursion depth for contract permission checks from config.

    This limits how deep permission check chains can go to prevent
    infinite recursion. Per Plan #100 and ADR-0018, default is 10.
    """
    return get_validated_config().executor.max_contract_depth


# Legacy constant for backward compatibility
DEFAULT_MAX_INVOKE_DEPTH = 5
DEFAULT_MAX_CONTRACT_DEPTH = 10


def _parse_json_args(args: list[Any]) -> list[Any]:
    """Parse JSON strings in args to Python objects.

    LLMs often generate JSON strings for dict arguments (e.g., '{"id": "foo"}').
    This auto-converts them to proper Python types before passing to artifacts.

    Plan #112: Fixes repeated 'str' object has no attribute 'get' errors.

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


class CodeValidationResult(TypedDict, total=False):
    """Result from code validation."""
    valid: bool
    error: str


@dataclass
class ValidationResult:
    """Result from interface validation (Plan #86).

    Attributes:
        valid: Whether the arguments matched the interface schema
        proceed: Whether to proceed with the invocation
        skipped: Whether validation was skipped entirely
        error_message: Description of validation failure (if any)
    """
    valid: bool
    proceed: bool
    skipped: bool
    error_message: str


# Logger for interface validation
_logger = logging.getLogger(__name__)


def validate_args_against_interface(
    interface: dict[str, Any] | None,
    method_name: str,
    args: dict[str, Any],
    validation_mode: str,
) -> ValidationResult:
    """Validate invocation arguments against artifact interface schema (Plan #86).

    Args:
        interface: The artifact's interface definition (MCP-compatible format)
        method_name: The method being invoked
        args: The arguments being passed
        validation_mode: One of 'none', 'warn', or 'strict'

    Returns:
        ValidationResult indicating whether to proceed
    """
    # Mode 'none' - skip all validation
    if validation_mode == "none":
        return ValidationResult(valid=True, proceed=True, skipped=True, error_message="")

    # No interface - skip validation
    if interface is None:
        return ValidationResult(valid=True, proceed=True, skipped=True, error_message="")

    # Get tools array from interface
    tools = interface.get("tools", [])
    if not tools:
        # No tools defined - skip validation
        return ValidationResult(valid=True, proceed=True, skipped=True, error_message="")

    # Find the method in tools
    method_schema = None
    for tool in tools:
        if tool.get("name") == method_name:
            method_schema = tool
            break

    if method_schema is None:
        # Method not found in interface
        error_msg = f"Method '{method_name}' not found in interface"
        if validation_mode == "warn":
            _logger.warning("Interface validation: %s", error_msg)
            return ValidationResult(valid=False, proceed=True, skipped=False, error_message=error_msg)
        else:  # strict
            return ValidationResult(valid=False, proceed=False, skipped=False, error_message=error_msg)

    # Get inputSchema from method
    input_schema = method_schema.get("inputSchema")
    if input_schema is None:
        # No inputSchema - skip validation (method accepts anything)
        return ValidationResult(valid=True, proceed=True, skipped=True, error_message="")

    # Validate args against inputSchema using jsonschema
    try:
        jsonschema.validate(instance=args, schema=input_schema)
        # Validation passed
        return ValidationResult(valid=True, proceed=True, skipped=False, error_message="")
    except jsonschema.ValidationError as e:
        # Validation failed - extract meaningful error message
        error_msg = str(e.message)

        if validation_mode == "warn":
            _logger.warning("Interface validation failed for '%s': %s", method_name, error_msg)
            return ValidationResult(valid=False, proceed=True, skipped=False, error_message=error_msg)
        else:  # strict
            return ValidationResult(valid=False, proceed=False, skipped=False, error_message=error_msg)
    except jsonschema.SchemaError as e:
        # Schema itself is invalid - treat as skip
        error_msg = f"Invalid interface schema: {e.message}"
        _logger.error("Interface schema error: %s", error_msg)
        return ValidationResult(valid=False, proceed=True, skipped=False, error_message=error_msg)


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


# Backward compatibility alias
def get_allowed_modules() -> dict[str, ModuleType | _DatetimeModule]:
    """DEPRECATED: Use get_preloaded_modules()"""
    return get_preloaded_modules()


# Default for backward compatibility
ALLOWED_MODULES: dict[str, ModuleType | _DatetimeModule] = AVAILABLE_MODULES


class ExecutionError(Exception):
    """Error during code execution"""
    pass


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

        Args:
            contract_id: The contract ID to look up

        Returns:
            Tuple of (contract, is_fallback, original_contract_id)
            - contract: The contract instance (never None)
            - is_fallback: True if this is a fallback due to missing contract
            - original_contract_id: The original ID if fallback occurred, else None
        """
        if contract_id in self._contract_cache:
            return self._contract_cache[contract_id], False, None

        # Check genesis contracts
        contract = get_contract_by_id(contract_id)
        if contract:
            self._contract_cache[contract_id] = contract
            return contract, False, None

        # Contract not found - use configurable default (ADR-0017)
        self._dangling_contract_count += 1

        # Log warning for observability
        logger = logging.getLogger(__name__)
        default_contract_id = get("contracts.default_on_missing") or "genesis_contract_freeware"
        logger.warning(
            f"Dangling contract: '{contract_id}' not found, "
            f"falling back to '{default_contract_id}'"
        )

        # Get the default contract
        contract = get_contract_by_id(default_contract_id)
        if not contract:
            contract = get_genesis_contract("freeware")

        # Cache the original ID pointing to fallback contract
        self._contract_cache[contract_id] = contract
        return contract, True, contract_id

    def _get_contract(
        self, contract_id: str
    ) -> AccessContract | ExecutableContract:
        """Get contract by ID, with caching.

        Checks genesis contracts first, then falls back to freeware
        if not found. Also supports ExecutableContracts registered
        via register_executable_contract().

        Args:
            contract_id: The contract ID to look up

        Returns:
            The contract instance (never None - falls back to freeware)
        """
        contract, _, _ = self._get_contract_with_fallback_info(contract_id)
        return contract

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
    ) -> PermissionResult:
        """Check permission using artifact's access contract.

        Supports both genesis contracts (static logic) and executable
        contracts (dynamic code). Executable contracts receive read-only
        ledger access for balance checks.

        Plan #100 Phase 2: Supports TTL-based caching for contracts with
        cache_policy. Caching is opt-in - contracts without cache_policy
        are never cached.

        Args:
            caller: The principal requesting access
            action: The action being attempted (read, write, invoke, etc.)
            artifact: The artifact being accessed
            contract_depth: Current depth of permission check chain (default 0).
                Per Plan #100, prevents infinite recursion in permission checks.

        Returns:
            PermissionResult with allowed, reason, and optional cost
        """
        # Check depth limit (Plan #100: prevent infinite recursion)
        if contract_depth >= self.max_contract_depth:
            return PermissionResult(
                allowed=False,
                reason=f"Contract permission check depth exceeded (depth={contract_depth}, limit={self.max_contract_depth})"
            )

        # Get contract ID from artifact (default to freeware)
        contract_id = getattr(artifact, "access_contract_id", "genesis_contract_freeware")
        contract, is_fallback, original_contract_id = self._get_contract_with_fallback_info(
            contract_id
        )

        # Convert action string to PermissionAction
        try:
            perm_action = PermissionAction(action)
        except ValueError:
            return PermissionResult(
                allowed=False,
                reason=f"Unknown action: {action}"
            )

        # Plan #100 Phase 2: Check permission cache for ExecutableContracts with cache_policy
        cache_key = None
        cache_policy = None
        if isinstance(contract, ExecutableContract) and contract.cache_policy is not None:
            cache_policy = contract.cache_policy
            # Cache key: (artifact_id, action, requester_id, contract_version)
            # Contract version is "v1" for now (versioning to be added later)
            contract_version = getattr(contract, "version", "v1")
            cache_key = (artifact.id, action, caller, contract_version)

            # Check cache
            cached_result = self._permission_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        # Build context for contract
        context: dict[str, object] = {
            "owner": artifact.owner_id,
            "artifact_type": artifact.type,
            "artifact_id": artifact.id,
        }

        # ExecutableContracts need ledger access for balance checks
        if isinstance(contract, ExecutableContract):
            result = contract.check_permission(
                caller=caller,
                action=perm_action,
                target=artifact.id,
                context=context,
                ledger=self._ledger,
            )

            # Store in cache if cache_policy is set
            if cache_key is not None and cache_policy is not None:
                ttl_seconds = cache_policy.get("ttl_seconds", 0)
                if ttl_seconds > 0:
                    self._permission_cache.put(cache_key, result, ttl_seconds)
        else:
            # Genesis/static contracts use standard interface
            result = contract.check_permission(
                caller=caller,
                action=perm_action,
                target=artifact.id,
                context=context,
            )

        # Plan #100 ADR-0017: Add dangling contract info to conditions for observability
        if is_fallback and original_contract_id is not None:
            # Merge with existing conditions if any
            new_conditions: dict[str, object] = dict(result.conditions or {})
            new_conditions["dangling_contract"] = True
            new_conditions["original_contract_id"] = original_contract_id
            result = dataclass_replace(result, conditions=new_conditions)

        return result

    def _check_permission_legacy(
        self,
        caller: str,
        action: str,
        artifact: "Artifact",
    ) -> tuple[bool, str]:
        """Legacy permission check using inline policy dict.

        DEPRECATED: Legacy mode is deprecated. All artifacts should use
        access_contract_id for permission checking. When an artifact lacks
        a contract, the executor falls back to freeware contract semantics:
        - READ, EXECUTE, INVOKE: Anyone can access
        - WRITE, DELETE, TRANSFER: Only owner can access

        This function now delegates to freeware contract instead of
        implementing custom logic. Owner bypass has been removed per CAP-003.

        Args:
            caller: The principal requesting access
            action: The action being attempted
            artifact: The artifact being accessed

        Returns:
            Tuple of (allowed, reason)
        """
        import warnings
        warnings.warn(
            "Legacy permission checking is deprecated. Set access_contract_id "
            "on artifacts to use contract-based permissions.",
            DeprecationWarning,
            stacklevel=3,
        )

        # CAP-003: No special owner bypass. Delegate to freeware contract
        # which properly handles owner access for write/delete/transfer actions.
        freeware = get_genesis_contract("freeware")

        # Convert action string to PermissionAction
        try:
            perm_action = PermissionAction(action)
        except ValueError:
            return (False, f"legacy: unknown action {action}")

        context: dict[str, object] = {
            "owner": artifact.owner_id,
            "artifact_type": artifact.type,
            "artifact_id": artifact.id,
        }

        result = freeware.check_permission(
            caller=caller,
            action=perm_action,
            target=artifact.id,
            context=context,
        )
        return (result.allowed, f"legacy (freeware): {result.reason}")

    def _check_permission(
        self,
        caller: str,
        action: str,
        artifact: "Artifact",
    ) -> tuple[bool, str]:
        """Check if caller has permission for action on artifact.

        Uses contracts when use_contracts=True AND the artifact has an
        access_contract_id attribute. Otherwise falls back to legacy policy.
        This provides backward compatibility for artifacts without contracts.

        Args:
            caller: The principal requesting access
            action: The action being attempted
            artifact: The artifact being accessed

        Returns:
            Tuple of (allowed, reason)
        """
        # Only use contract-based checking if:
        # 1. use_contracts is enabled
        # 2. The artifact has an explicit access_contract_id attribute
        has_contract = hasattr(artifact, "access_contract_id") and artifact.access_contract_id is not None

        if self.use_contracts and has_contract:
            result = self._check_permission_via_contract(caller, action, artifact)
            return (result.allowed, result.reason)

        # Legacy policy-based check (for backward compatibility)
        return self._check_permission_legacy(caller, action, artifact)

    def validate_code(self, code: str) -> tuple[bool, str]:
        """
        Validate that code can be compiled and has a run() function.

        Returns:
            (success, error_message)
        """
        if not code or not code.strip():
            return False, "Empty code"

        # Check for run() function definition
        if "def run(" not in code:
            return False, "Code must define a run() function"

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
                "error": f"Execution error: {type(e).__name__}: {e}"
            }

        # Check that run() was defined
        if "run" not in controlled_globals:
            return {"success": False, "error": "Code did not define a run() function"}

        run_func = controlled_globals["run"]
        if not callable(run_func):
            return {"success": False, "error": "run is not callable"}

        # Plan #112: Parse JSON strings in args to Python objects
        args = _parse_json_args(args)

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
                    "error": f"Runtime error: {type(e).__name__}: {e}",
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
                "error": f"Execution error: {type(e).__name__}: {e}"
            }

        # Check that run() was defined
        if "run" not in controlled_globals:
            return {"success": False, "error": "Code did not define a run() function"}

        run_func = controlled_globals["run"]
        if not callable(run_func):
            return {"success": False, "error": "run is not callable"}

        # Plan #112: Parse JSON strings in args to Python objects
        args = _parse_json_args(args)

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
                    "error": f"Runtime error: {type(e).__name__}: {e}",
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
            code: Python code defining a run() function
            args: Arguments to pass to run()
            caller_id: ID of the original caller (pays for nested invocations)
            artifact_id: ID of this artifact (for wallet access)
            ledger: Ledger instance for transfers
            artifact_store: ArtifactStore for looking up artifacts
            current_depth: Current recursion depth (for preventing infinite loops)
            max_depth: Maximum allowed recursion depth
            world: World instance for kernel interface injection (Plan #39)

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
        if caller_id and ledger and artifact_store:
            def invoke(target_artifact_id: str, *invoke_args: Any) -> InvokeResult:
                """Invoke another artifact from within this artifact's code.

                The caller (original agent) pays for the invocation.
                Recursion is limited to prevent infinite loops.

                Args:
                    target_artifact_id: ID of artifact to invoke
                    *invoke_args: Arguments to pass to the artifact's run()

                Returns:
                    InvokeResult with success, result, error, and price_paid
                """
                # Check recursion depth
                if current_depth >= max_depth:
                    return {
                        "success": False,
                        "result": None,
                        "error": f"Max invoke depth ({max_depth}) exceeded",
                        "price_paid": 0
                    }

                # Look up the target artifact
                target = artifact_store.get(target_artifact_id)
                if not target:
                    return {
                        "success": False,
                        "result": None,
                        "error": f"Artifact {target_artifact_id} not found",
                        "price_paid": 0
                    }

                if not target.executable:
                    return {
                        "success": False,
                        "result": None,
                        "error": f"Artifact {target_artifact_id} is not executable",
                        "price_paid": 0
                    }

                # Check invoke permission (caller, not this artifact)
                # _check_permission handles contract vs legacy decision internally
                allowed, reason = self._check_permission(caller_id, "invoke", target)
                if not allowed:
                    return {
                        "success": False,
                        "result": None,
                        "error": f"Caller {caller_id} not allowed to invoke {target_artifact_id}: {reason}",
                        "price_paid": 0
                    }

                # Determine price: contract cost (if any) + artifact price
                price = target.price
                owner_id = target.owner_id

                # If using contracts and target has a contract, check for additional cost
                contract_cost = 0
                has_contract = hasattr(target, "access_contract_id") and target.access_contract_id is not None
                if self.use_contracts and has_contract:
                    perm_result = self._check_permission_via_contract(
                        caller_id, "invoke", target
                    )
                    contract_cost = perm_result.cost

                total_cost = price + contract_cost
                if total_cost > 0 and not ledger.can_afford_scrip(caller_id, total_cost):
                    return {
                        "success": False,
                        "result": None,
                        "error": f"Caller has insufficient scrip for total cost {total_cost}",
                        "price_paid": 0
                    }

                # Recursively execute the target artifact
                nested_result = self.execute_with_invoke(
                    code=target.code,
                    args=list(invoke_args),
                    caller_id=caller_id,
                    artifact_id=target_artifact_id,
                    ledger=ledger,
                    artifact_store=artifact_store,
                    current_depth=current_depth + 1,
                    max_depth=max_depth,
                    world=world,
                )

                if nested_result.get("success"):
                    # Pay total cost to owner (only on success)
                    if total_cost > 0 and owner_id != caller_id:
                        ledger.deduct_scrip(caller_id, total_cost)
                        ledger.credit_scrip(owner_id, total_cost)

                    return {
                        "success": True,
                        "result": nested_result.get("result"),
                        "error": "",
                        "price_paid": total_cost
                    }
                else:
                    return {
                        "success": False,
                        "result": None,
                        "error": nested_result.get("error", "Unknown error"),
                        "price_paid": 0
                    }

            controlled_globals["invoke"] = invoke

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
                "error": f"Execution error: {type(e).__name__}: {e}"
            }

        # Check that run() was defined
        if "run" not in controlled_globals:
            return {"success": False, "error": "Code did not define a run() function"}

        run_func = controlled_globals["run"]
        if not callable(run_func):
            return {"success": False, "error": "run is not callable"}

        # Plan #112: Parse JSON strings in args to Python objects
        args = _parse_json_args(args)

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
                    "error": f"Runtime error: {type(e).__name__}: {e}",
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
