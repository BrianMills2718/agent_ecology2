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
import math
import random
import signal
from datetime import datetime, timedelta
from types import FrameType, ModuleType
from typing import Any, TypedDict

from config import get

# Import Ledger type for type hints (avoid circular import at runtime)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .ledger import Ledger


class PaymentResult(TypedDict):
    """Result from a pay() call within artifact execution."""
    success: bool
    amount: int
    target: str
    error: str


class ExecutionResult(TypedDict, total=False):
    """Result from code execution."""
    success: bool
    result: Any
    error: str


class ValidationResult(TypedDict, total=False):
    """Result from code validation."""
    valid: bool
    error: str


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


def _timeout_handler(signum: int, frame: FrameType | None) -> None:
    raise TimeoutError("Execution timed out")


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

    NOTE: This is NOT a security sandbox. Security boundary is the
    container (Docker non-root user), not code-level restrictions.
    See docs/SECURITY.md for rationale.
    """

    timeout: int
    preloaded_modules: dict[str, ModuleType | _DatetimeModule]

    def __init__(self, timeout: int | None = None) -> None:
        default_timeout: int = get("executor.timeout_seconds") or 5
        self.timeout = timeout or default_timeout
        self.preloaded_modules = get_preloaded_modules()

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
        except Exception as e:
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
        except Exception as e:
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
            # Set up timeout (Unix only)
            old_handler: Any = None
            try:
                old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(self.timeout)
            except (ValueError, AttributeError):
                # signal.alarm not available (Windows) - skip timeout
                pass

            try:
                exec(compiled, controlled_globals)
            finally:
                # Disable alarm
                try:
                    signal.alarm(0)
                    if old_handler:
                        signal.signal(signal.SIGALRM, old_handler)
                except (ValueError, AttributeError):
                    pass

        except TimeoutError:
            return {"success": False, "error": "Code definition timed out"}
        except Exception as e:
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

        # Call run() with args
        try:
            # Set up timeout for run() call
            old_handler = None
            try:
                old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(self.timeout)
            except (ValueError, AttributeError):
                pass

            try:
                result = run_func(*args)
            finally:
                try:
                    signal.alarm(0)
                    if old_handler:
                        signal.signal(signal.SIGALRM, old_handler)
                except (ValueError, AttributeError):
                    pass

        except TimeoutError:
            return {"success": False, "error": "Execution timed out"}
        except TypeError as e:
            return {"success": False, "error": f"Argument error: {e}"}
        except Exception as e:
            return {
                "success": False,
                "error": f"Runtime error: {type(e).__name__}: {e}"
            }

        # Ensure result is JSON-serializable
        try:
            json.dumps(result)
        except (TypeError, ValueError):
            # Convert to string if not serializable
            result = str(result)

        return {"success": True, "result": result}

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
        except Exception as e:
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
            old_handler: Any = None
            try:
                old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(self.timeout)
            except (ValueError, AttributeError):
                pass

            try:
                exec(compiled, controlled_globals)
            finally:
                try:
                    signal.alarm(0)
                    if old_handler:
                        signal.signal(signal.SIGALRM, old_handler)
                except (ValueError, AttributeError):
                    pass

        except TimeoutError:
            return {"success": False, "error": "Code definition timed out"}
        except Exception as e:
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

        # Call run() with args
        try:
            old_handler = None
            try:
                old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(self.timeout)
            except (ValueError, AttributeError):
                pass

            try:
                result = run_func(*args)
            finally:
                try:
                    signal.alarm(0)
                    if old_handler:
                        signal.signal(signal.SIGALRM, old_handler)
                except (ValueError, AttributeError):
                    pass

        except TimeoutError:
            return {"success": False, "error": "Execution timed out"}
        except TypeError as e:
            return {"success": False, "error": f"Argument error: {e}"}
        except Exception as e:
            return {
                "success": False,
                "error": f"Runtime error: {type(e).__name__}: {e}"
            }

        # Ensure result is JSON-serializable
        try:
            json.dumps(result)
        except (TypeError, ValueError):
            result = str(result)

        return {"success": True, "result": result}


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
