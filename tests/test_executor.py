"""Unit tests for the SandboxExecutor (SafeExecutor) class.

These tests verify that the sandbox properly blocks dangerous operations
while allowing legitimate code execution.
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from world.executor import SafeExecutor


class TestSandboxSafety:
    """Tests that verify the sandbox blocks dangerous operations."""

    def setup_method(self) -> None:
        """Create a fresh executor for each test."""
        self.executor = SafeExecutor(timeout=5)

    def test_block_file_read(self) -> None:
        """Verify that open() cannot be used to read files."""
        code = '''
def run():
    with open("/etc/passwd", "r") as f:
        return f.read()
'''
        result = self.executor.execute(code)
        assert result["success"] is False
        # Should fail during compilation or execution because open is not available
        assert "error" in result

    def test_block_file_write(self) -> None:
        """Verify that open() cannot be used to write files."""
        code = '''
def run():
    with open("/tmp/malicious.txt", "w") as f:
        f.write("pwned")
    return "wrote file"
'''
        result = self.executor.execute(code)
        assert result["success"] is False
        assert "error" in result

    def test_block_import_os(self) -> None:
        """Verify that the os module cannot be imported."""
        code = '''
def run():
    import os
    return os.getcwd()
'''
        result = self.executor.execute(code)
        assert result["success"] is False
        assert "error" in result
        # Check that the error mentions import restriction
        assert "Import" in result["error"] or "import" in result["error"].lower()

    def test_block_import_subprocess(self) -> None:
        """Verify that subprocess cannot be imported."""
        code = '''
def run():
    import subprocess
    return subprocess.run(["ls"], capture_output=True).stdout
'''
        result = self.executor.execute(code)
        assert result["success"] is False
        assert "error" in result
        assert "Import" in result["error"] or "import" in result["error"].lower()

    def test_block_exec(self) -> None:
        """Verify that exec() is not available."""
        code = '''
def run():
    exec("x = 1 + 1")
    return x
'''
        result = self.executor.execute(code)
        assert result["success"] is False
        assert "error" in result

    def test_block_eval(self) -> None:
        """Verify that eval() is not available."""
        code = '''
def run():
    return eval("1 + 1")
'''
        result = self.executor.execute(code)
        assert result["success"] is False
        assert "error" in result

    def test_block_getattr_exploit(self) -> None:
        """Verify that getattr cannot be used to escape the sandbox."""
        # Attempt to access __builtins__ through a chain of getattr calls
        code = '''
def run():
    # Try to get __class__.__mro__ to access object and then builtins
    x = ().__class__.__mro__[1].__subclasses__()
    return str(x)
'''
        result = self.executor.execute(code)
        # This should either fail during compilation or execution
        # RestrictedPython should block direct attribute access to dunder methods
        assert result["success"] is False
        assert "error" in result

    def test_block_builtins_access(self) -> None:
        """Verify that __builtins__ cannot be accessed directly."""
        code = '''
def run():
    return __builtins__["open"]("/etc/passwd").read()
'''
        result = self.executor.execute(code)
        assert result["success"] is False
        assert "error" in result

    def test_block_import_sys(self) -> None:
        """Verify that sys module cannot be imported."""
        code = '''
def run():
    import sys
    return sys.path
'''
        result = self.executor.execute(code)
        assert result["success"] is False
        assert "error" in result

    def test_block_compile(self) -> None:
        """Verify that compile() is not available."""
        code = '''
def run():
    c = compile("print('pwned')", "<string>", "exec")
    return "compiled"
'''
        result = self.executor.execute(code)
        assert result["success"] is False
        assert "error" in result


class TestSandboxFunctionality:
    """Tests that verify allowed operations work correctly."""

    def setup_method(self) -> None:
        """Create a fresh executor for each test."""
        self.executor = SafeExecutor(timeout=5)

    def test_allowed_import_math(self) -> None:
        """Verify that the math module can be imported and used."""
        code = '''
def run():
    import math
    return math.sqrt(16)
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == 4.0

    def test_allowed_import_json(self) -> None:
        """Verify that the json module can be imported and used."""
        code = '''
def run():
    import json
    data = {"key": "value", "number": 42}
    return json.dumps(data)
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        parsed = __import__("json").loads(result["result"])
        assert parsed["key"] == "value"
        assert parsed["number"] == 42

    def test_allowed_import_random(self) -> None:
        """Verify that the random module can be imported and used."""
        code = '''
def run():
    import random
    random.seed(42)  # Set seed for reproducibility
    return random.randint(1, 100)
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert isinstance(result["result"], int)
        assert 1 <= result["result"] <= 100

    def test_simple_function(self) -> None:
        """Verify that basic function execution works."""
        code = '''
def run():
    x = 5
    y = 10
    return x + y
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == 15

    def test_function_with_args(self) -> None:
        """Verify that functions with arguments work correctly."""
        code = '''
def run(a, b, c):
    return a + b * c
'''
        result = self.executor.execute(code, args=[2, 3, 4])
        assert result["success"] is True
        assert result["result"] == 14  # 2 + 3 * 4 = 14

    def test_timeout(self) -> None:
        """Verify that long-running code times out."""
        code = '''
def run():
    x = []
    while True:
        x.append(1)
    return len(x)
'''
        # Use a short timeout for this test
        executor = SafeExecutor(timeout=1)
        result = executor.execute(code)
        assert result["success"] is False
        assert "timeout" in result["error"].lower() or "timed out" in result["error"].lower()

    def test_return_value(self) -> None:
        """Verify that return values are captured correctly."""
        code = '''
def run():
    return {"status": "ok", "count": 42, "items": [1, 2, 3]}
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"]["status"] == "ok"
        assert result["result"]["count"] == 42
        assert result["result"]["items"] == [1, 2, 3]

    def test_builtin_functions(self) -> None:
        """Verify that allowed builtin functions work."""
        code = '''
def run():
    nums = [3, 1, 4, 1, 5, 9, 2, 6]
    return {
        "sum": sum(nums),
        "max": max(nums),
        "min": min(nums),
        "len": len(nums),
        "sorted": sorted(nums),
    }
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"]["sum"] == 31
        assert result["result"]["max"] == 9
        assert result["result"]["min"] == 1
        assert result["result"]["len"] == 8
        assert result["result"]["sorted"] == [1, 1, 2, 3, 4, 5, 6, 9]

    def test_list_operations(self) -> None:
        """Verify that list operations work correctly."""
        code = '''
def run():
    items = []
    items.append(1)
    items.append(2)
    items.extend([3, 4])
    return items
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == [1, 2, 3, 4]

    def test_dict_operations(self) -> None:
        """Verify that dict operations work correctly."""
        code = '''
def run():
    d = {}
    d["a"] = 1
    d["b"] = 2
    d.update({"c": 3})
    return d
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == {"a": 1, "b": 2, "c": 3}

    def test_string_operations(self) -> None:
        """Verify that string operations work correctly."""
        code = '''
def run():
    s = "hello world"
    return {
        "upper": s.upper(),
        "split": s.split(),
        "replace": s.replace("world", "python"),
    }
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"]["upper"] == "HELLO WORLD"
        assert result["result"]["split"] == ["hello", "world"]
        assert result["result"]["replace"] == "hello python"


class TestValidation:
    """Tests for code validation functionality."""

    def setup_method(self) -> None:
        """Create a fresh executor for each test."""
        self.executor = SafeExecutor(timeout=5)

    def test_empty_code(self) -> None:
        """Verify that empty code is rejected."""
        valid, error = self.executor.validate_code("")
        assert valid is False
        assert "Empty" in error

    def test_missing_run_function(self) -> None:
        """Verify that code without run() is rejected."""
        code = '''
def foo():
    return 42
'''
        valid, error = self.executor.validate_code(code)
        assert valid is False
        assert "run()" in error

    def test_syntax_error(self) -> None:
        """Verify that syntax errors are caught."""
        code = '''
def run(
    return 42
'''
        valid, error = self.executor.validate_code(code)
        assert valid is False
        assert "Syntax" in error or "syntax" in error

    def test_valid_code(self) -> None:
        """Verify that valid code passes validation."""
        code = '''
def run():
    return 42
'''
        valid, error = self.executor.validate_code(code)
        assert valid is True
        assert error == ""


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def setup_method(self) -> None:
        """Create a fresh executor for each test."""
        self.executor = SafeExecutor(timeout=5)

    def test_run_not_callable(self) -> None:
        """Verify error when run is not a function."""
        code = '''
run = 42

def dummy():
    pass
'''
        # This should pass validation (has "def run(" substring check fails)
        # but let's test execution anyway
        result = self.executor.execute(code)
        # Should fail because run must be a function
        assert result["success"] is False

    def test_wrong_number_of_args(self) -> None:
        """Verify error when wrong number of arguments passed."""
        code = '''
def run(a, b):
    return a + b
'''
        result = self.executor.execute(code, args=[1])  # Missing second arg
        assert result["success"] is False
        assert "error" in result

    def test_exception_in_run(self) -> None:
        """Verify that exceptions in run() are caught."""
        code = '''
def run():
    x = 1 / 0
    return x
'''
        result = self.executor.execute(code)
        assert result["success"] is False
        assert "ZeroDivision" in result["error"] or "division" in result["error"].lower()

    def test_none_return_value(self) -> None:
        """Verify that None return values work."""
        code = '''
def run():
    x = 1 + 1
    # No return statement
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] is None

    def test_complex_return_value(self) -> None:
        """Verify that complex but serializable return values work."""
        code = '''
def run():
    return {
        "nested": {"a": 1, "b": [1, 2, 3]},
        "list_of_dicts": [{"x": 1}, {"y": 2}],
        "tuple_as_list": [1, 2, 3],
    }
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"]["nested"]["a"] == 1
        assert result["result"]["nested"]["b"] == [1, 2, 3]

    def test_modules_available_without_import(self) -> None:
        """Verify that allowed modules are available without explicit import."""
        code = '''
def run():
    # math, json, random should be available in the namespace
    return math.pi > 3
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] is True
