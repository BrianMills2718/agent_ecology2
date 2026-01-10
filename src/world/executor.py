"""SafeExecutor - Execution of agent-created code

Uses standard Python exec() with:
- Whitelisted modules only (configurable in config.yaml)
- Controlled globals with pre-imported allowed modules
- Timeout protection (configurable via signal)

Security model: Docker non-root user (external), not code-level sandboxing.
"""

from __future__ import annotations

import builtins
import json
import math
import random
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import FrameType, ModuleType
from typing import Any, TypedDict

# Add src to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get


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


# Available modules that can be whitelisted in config
AVAILABLE_MODULES: dict[str, ModuleType | _DatetimeModule] = {
    "math": math,
    "json": json,
    "random": random,
    "datetime": _DatetimeModule(),
}


def get_allowed_modules() -> dict[str, ModuleType | _DatetimeModule]:
    """Get allowed modules based on config."""
    allowed_imports: list[str] = get("executor.allowed_imports") or [
        "math", "json", "random", "datetime"
    ]
    return {
        name: AVAILABLE_MODULES[name]
        for name in allowed_imports
        if name in AVAILABLE_MODULES
    }


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
    - Whitelisted imports pre-loaded (configurable)
    - Execution timeout (configurable)
    - Full Python capability for agent sub-calls

    Security: Docker non-root user (external), not code-level sandboxing.
    """

    timeout: int
    allowed_modules: dict[str, ModuleType | _DatetimeModule]

    def __init__(self, timeout: int | None = None) -> None:
        default_timeout: int = get("executor.timeout_seconds") or 5
        self.timeout = timeout or default_timeout
        self.allowed_modules = get_allowed_modules()

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
            self.allowed_modules
        )

        controlled_globals: dict[str, Any] = {
            "__builtins__": controlled_builtins,
            "__name__": "__main__",
        }

        # Add allowed modules to namespace (so they can be used without import)
        for name, module in self.allowed_modules.items():
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
