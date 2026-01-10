"""SafeExecutor - Sandboxed execution of agent-created code

Uses RestrictedPython to safely execute Python code with:
- Whitelisted modules only (configurable in config.yaml)
- No file/network/system access
- Limited built-in functions
- Timeout protection (configurable)
"""

import math
import json
import random
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Tuple

from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Eval import default_guarded_getiter, default_guarded_getitem
from RestrictedPython.Guards import guarded_iter_unpack_sequence, safer_getattr

# Add src to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get


# Available modules that can be whitelisted in config
AVAILABLE_MODULES = {
    "math": math,
    "json": json,
    "random": random,
    "datetime": type("datetime_module", (), {
        "datetime": datetime,
        "timedelta": timedelta,
    })(),
}


def get_allowed_modules() -> Dict[str, Any]:
    """Get allowed modules based on config."""
    allowed_imports = get("executor.allowed_imports") or ["math", "json", "random", "datetime"]
    return {name: AVAILABLE_MODULES[name] for name in allowed_imports if name in AVAILABLE_MODULES}


# Default for backward compatibility
ALLOWED_MODULES = AVAILABLE_MODULES

# Safe subset of built-in functions
SAFE_BUILTINS = {
    # Type constructors
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "frozenset": frozenset,

    # Iteration and ranges
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "reversed": reversed,
    "sorted": sorted,

    # Math operations
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "round": round,
    "pow": pow,
    "divmod": divmod,

    # Sequence operations
    "len": len,
    "all": all,
    "any": any,

    # Type checking
    "isinstance": isinstance,
    "type": type,

    # String operations
    "chr": chr,
    "ord": ord,

    # Utilities
    "repr": repr,
    "hash": hash,
    "id": id,

    # Boolean constants
    "True": True,
    "False": False,
    "None": None,
}

# Blocked: open, exec, eval, compile, __import__, input, print, exit, quit, etc.


class ExecutionError(Exception):
    """Error during code execution"""
    pass


class TimeoutError(Exception):
    """Code execution timed out"""
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("Execution timed out")


def _make_safe_import(allowed_modules: Dict[str, Any]):
    """Create a restricted import function for the given allowed modules."""
    def _safe_import(name, *args, **kwargs):
        """Restricted import that only allows whitelisted modules"""
        if name in allowed_modules:
            return allowed_modules[name]
        raise ImportError(f"Import of '{name}' is not allowed. Allowed: {list(allowed_modules.keys())}")
    return _safe_import


def _write_guard(obj):
    """Guard for write operations - allow basic types only"""
    if isinstance(obj, (list, dict, set)):
        return obj
    raise TypeError(f"Cannot modify object of type {type(obj).__name__}")


class SafeExecutor:
    """
    Executes agent-created code in a restricted sandbox.

    Code must define a `run(*args)` function that will be called.

    Security features:
    - RestrictedPython compilation
    - Whitelisted imports only (configurable)
    - No file/network access
    - Limited built-ins
    - Execution timeout (configurable)
    """

    def __init__(self, timeout: int = None):
        default_timeout = get("executor.timeout_seconds") or 5
        self.timeout = timeout or default_timeout
        self.allowed_modules = get_allowed_modules()

    def validate_code(self, code: str) -> Tuple[bool, str]:
        """
        Validate that code can be safely compiled.

        Returns:
            (success, error_message)
        """
        if not code or not code.strip():
            return False, "Empty code"

        # Check for run() function definition
        if "def run(" not in code:
            return False, "Code must define a run() function"

        # Try to compile with RestrictedPython
        try:
            compile_restricted(code, '<agent_code>', 'exec')
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Compilation failed: {e}"

    def execute(self, code: str, args: list = None) -> Dict[str, Any]:
        """
        Execute code in sandbox and call run(*args).

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

        # Compile with RestrictedPython
        try:
            compiled = compile_restricted(code, '<agent_code>', 'exec')
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Compilation failed: {e}"}

        # Build restricted builtins (including __import__)
        safe_builtins = dict(SAFE_BUILTINS)
        safe_builtins["__import__"] = _make_safe_import(self.allowed_modules)

        # Build restricted globals
        restricted_globals = {
            "__builtins__": safe_builtins,
            "__name__": "__main__",
            "__metaclass__": type,
            "_write_": _write_guard,
            "_getattr_": safer_getattr,
            "_getitem_": default_guarded_getitem,
            "_getiter_": default_guarded_getiter,
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
        }

        # Add allowed modules to namespace (so they can be used without import)
        for name, module in self.allowed_modules.items():
            restricted_globals[name] = module

        restricted_locals = {}

        # Execute the code definition (creates the run function)
        try:
            # Set up timeout (Unix only)
            old_handler = None
            try:
                old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(self.timeout)
            except (ValueError, AttributeError):
                # signal.alarm not available (Windows) - skip timeout
                pass

            try:
                exec(compiled, restricted_globals, restricted_locals)
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
            return {"success": False, "error": f"Execution error: {type(e).__name__}: {e}"}

        # Check that run() was defined
        if "run" not in restricted_locals:
            return {"success": False, "error": "Code did not define a run() function"}

        run_func = restricted_locals["run"]
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
            return {"success": False, "error": f"Runtime error: {type(e).__name__}: {e}"}

        # Ensure result is JSON-serializable
        try:
            json.dumps(result)
        except (TypeError, ValueError):
            # Convert to string if not serializable
            result = str(result)

        return {"success": True, "result": result}


# Singleton instance
_executor = None


def get_executor(timeout: int = None) -> SafeExecutor:
    """Get or create the SafeExecutor singleton.

    Timeout defaults to config value if not specified.
    """
    global _executor
    if _executor is None or (timeout and timeout != _executor.timeout):
        _executor = SafeExecutor(timeout=timeout)
    return _executor
