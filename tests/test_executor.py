"""Unit tests for the SafeExecutor class.

These tests verify that the executor properly executes code with timeout
protection while allowing full Python functionality.

Note: The executor is now unrestricted (no RestrictedPython) and relies on
Docker container isolation for security instead of Python-level sandboxing.
"""

from pathlib import Path

import pytest

from src.world.executor import SafeExecutor


class TestUnrestrictedExecution:
    """Tests that verify the unrestricted executor allows Python operations.

    These tests confirm that operations previously blocked by RestrictedPython
    now work correctly, as security is provided by Docker container isolation.
    """

    def setup_method(self) -> None:
        """Create a fresh executor for each test."""
        self.executor = SafeExecutor(timeout=5)

    def test_allow_import_os(self) -> None:
        """Verify that the os module can be imported."""
        code = '''
def run():
    import os
    return os.getcwd()
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert isinstance(result["result"], str)

    def test_allow_import_sys(self) -> None:
        """Verify that sys module can be imported."""
        code = '''
def run():
    import sys
    return len(sys.path) > 0
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] is True

    def test_allow_eval(self) -> None:
        """Verify that eval() works."""
        code = '''
def run():
    return eval("1 + 1")
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == 2

    def test_allow_exec(self) -> None:
        """Verify that exec() works."""
        code = '''
def run():
    local_vars = {}
    exec("x = 1 + 1", {}, local_vars)
    return local_vars.get("x")
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == 2

    def test_allow_compile(self) -> None:
        """Verify that compile() works."""
        code = '''
def run():
    c = compile("result = 2 + 2", "<string>", "exec")
    local_vars = {}
    exec(c, {}, local_vars)
    return local_vars.get("result")
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == 4

    def test_allow_getattr_dunder(self) -> None:
        """Verify that dunder attribute access works."""
        code = '''
def run():
    x = ().__class__.__mro__
    return len(x) > 0
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] is True


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


class TestNetworkAccess:
    """Tests verifying network access is allowed."""

    def setup_method(self) -> None:
        """Create a fresh executor for each test."""
        self.executor = SafeExecutor(timeout=10)

    def test_import_socket(self) -> None:
        """Verify socket module can be imported."""
        code = '''
def run():
    import socket
    return socket.AF_INET == 2
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] is True

    def test_import_urllib(self) -> None:
        """Verify urllib module can be imported."""
        code = '''
def run():
    import urllib.request
    return hasattr(urllib.request, 'urlopen')
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] is True

    def test_import_http_client(self) -> None:
        """Verify http.client module can be imported."""
        code = '''
def run():
    import http.client
    return hasattr(http.client, 'HTTPConnection')
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] is True


class TestBuiltinsAvailable:
    """Tests verifying all builtins are available."""

    def setup_method(self) -> None:
        """Create a fresh executor for each test."""
        self.executor = SafeExecutor(timeout=5)

    def test_builtin_open(self) -> None:
        """Verify open() is available (file access allowed)."""
        code = '''
def run():
    return callable(open)
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] is True

    def test_builtin_eval(self) -> None:
        """Verify eval() is available."""
        code = '''
def run():
    return eval("1 + 1")
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == 2

    def test_builtin_exec(self) -> None:
        """Verify exec() is available."""
        code = '''
def run():
    ns = {}
    exec("x = 42", ns)
    return ns.get("x")
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == 42

    def test_builtin_compile(self) -> None:
        """Verify compile() is available."""
        code = '''
def run():
    c = compile("1 + 1", "<string>", "eval")
    return eval(c)
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == 2

    def test_builtin_getattr(self) -> None:
        """Verify getattr() is available."""
        code = '''
def run():
    class Obj:
        value = 42
    return getattr(Obj, "value")
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == 42

    def test_builtin_setattr(self) -> None:
        """Verify setattr() is available."""
        code = '''
def run():
    class Obj:
        pass
    setattr(Obj, "value", 42)
    return Obj.value
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == 42

    def test_common_builtins(self) -> None:
        """Verify common builtin functions work."""
        code = '''
def run():
    nums = [3, 1, 4, 1, 5, 9, 2, 6]
    return {
        "sum": sum(nums),
        "max": max(nums),
        "min": min(nums),
        "len": len(nums),
        "sorted": sorted(nums),
        "abs": abs(-5),
        "round": round(3.7),
    }
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"]["sum"] == 31
        assert result["result"]["max"] == 9
        assert result["result"]["min"] == 1
        assert result["result"]["len"] == 8
        assert result["result"]["sorted"] == [1, 1, 2, 3, 4, 5, 6, 9]
        assert result["result"]["abs"] == 5
        assert result["result"]["round"] == 4


class TestStandardLibraryImports:
    """Tests verifying standard library imports work."""

    def setup_method(self) -> None:
        """Create a fresh executor for each test."""
        self.executor = SafeExecutor(timeout=5)

    def test_import_re(self) -> None:
        """Verify re module can be imported and used."""
        code = '''
def run():
    import re
    match = re.search(r"world", "hello world")
    return match.group() if match else None
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == "world"

    def test_import_datetime(self) -> None:
        """Verify datetime module can be imported and used."""
        code = '''
def run():
    from datetime import datetime
    now = datetime.now()
    return now.year >= 2024
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] is True

    def test_import_collections(self) -> None:
        """Verify collections module can be imported and used."""
        code = '''
def run():
    from collections import Counter
    c = Counter([1, 1, 2, 3, 3, 3])
    return dict(c)
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == {1: 2, 2: 1, 3: 3}

    def test_import_itertools(self) -> None:
        """Verify itertools module can be imported and used."""
        code = '''
def run():
    import itertools
    perms = list(itertools.permutations([1, 2], 2))
    # Convert tuples to lists for JSON serialization
    return [list(p) for p in perms]
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] == [[1, 2], [2, 1]]

    def test_import_subprocess(self) -> None:
        """Verify subprocess module can be imported."""
        code = '''
def run():
    import subprocess
    return hasattr(subprocess, 'run')
'''
        result = self.executor.execute(code)
        assert result["success"] is True
        assert result["result"] is True
