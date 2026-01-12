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


class TestContractIntegration:
    """Tests for Executor + Contracts integration."""

    def setup_method(self) -> None:
        """Create a fresh executor for each test."""
        self.executor = SafeExecutor(timeout=5, use_contracts=True)
        self.executor_legacy = SafeExecutor(timeout=5, use_contracts=False)

    def _make_artifact(
        self,
        artifact_id: str = "test_artifact",
        owner_id: str = "owner1",
        access_contract_id: str = "genesis_contract_freeware",
    ) -> "Artifact":
        """Create a test artifact with specified properties."""
        from src.world.artifacts import Artifact
        from datetime import datetime

        artifact = Artifact(
            id=artifact_id,
            type="test",
            content="test content",
            owner_id=owner_id,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        # Set the access_contract_id attribute
        artifact.access_contract_id = access_contract_id  # type: ignore[attr-defined]
        return artifact

    def test_contracts_enabled_by_default(self) -> None:
        """Contracts are used by default."""
        executor = SafeExecutor(timeout=5)
        assert executor.use_contracts is True

    def test_contracts_can_be_disabled(self) -> None:
        """Contracts can be disabled via constructor."""
        executor = SafeExecutor(timeout=5, use_contracts=False)
        assert executor.use_contracts is False

    def test_contract_cache_initialized(self) -> None:
        """Contract cache is initialized as empty dict."""
        executor = SafeExecutor(timeout=5)
        assert executor._contract_cache == {}

    def test_freeware_allows_read(self) -> None:
        """Freeware contract allows anyone to read."""
        artifact = self._make_artifact(access_contract_id="genesis_contract_freeware")
        allowed, _ = self.executor._check_permission("stranger", "read", artifact)
        assert allowed is True

    def test_freeware_allows_invoke(self) -> None:
        """Freeware contract allows anyone to invoke."""
        artifact = self._make_artifact(access_contract_id="genesis_contract_freeware")
        allowed, _ = self.executor._check_permission("stranger", "invoke", artifact)
        assert allowed is True

    def test_freeware_allows_execute(self) -> None:
        """Freeware contract allows anyone to execute."""
        artifact = self._make_artifact(access_contract_id="genesis_contract_freeware")
        allowed, _ = self.executor._check_permission("stranger", "execute", artifact)
        assert allowed is True

    def test_freeware_denies_write_non_owner(self) -> None:
        """Freeware contract denies write to non-owner."""
        artifact = self._make_artifact(
            access_contract_id="genesis_contract_freeware",
            owner_id="owner1",
        )
        allowed, reason = self.executor._check_permission("stranger", "write", artifact)
        assert allowed is False
        assert "owner" in reason.lower()

    def test_freeware_allows_write_owner(self) -> None:
        """Freeware contract allows owner to write."""
        artifact = self._make_artifact(
            access_contract_id="genesis_contract_freeware",
            owner_id="owner1",
        )
        allowed, _ = self.executor._check_permission("owner1", "write", artifact)
        assert allowed is True

    def test_private_denies_all_non_owner(self) -> None:
        """Private contract denies all access to non-owner."""
        artifact = self._make_artifact(
            access_contract_id="genesis_contract_private",
            owner_id="owner1",
        )

        for action in ["read", "write", "invoke", "execute", "delete", "transfer"]:
            allowed, _ = self.executor._check_permission("stranger", action, artifact)
            assert allowed is False, f"Private contract should deny {action} to non-owner"

    def test_private_allows_owner(self) -> None:
        """Private contract allows owner full access."""
        artifact = self._make_artifact(
            access_contract_id="genesis_contract_private",
            owner_id="owner1",
        )

        for action in ["read", "write", "invoke", "execute", "delete", "transfer"]:
            allowed, _ = self.executor._check_permission("owner1", action, artifact)
            assert allowed is True, f"Private contract should allow {action} to owner"

    def test_public_allows_everything(self) -> None:
        """Public contract allows all actions to anyone."""
        artifact = self._make_artifact(access_contract_id="genesis_contract_public")

        for action in ["read", "write", "invoke", "execute", "delete", "transfer"]:
            allowed, _ = self.executor._check_permission("anyone", action, artifact)
            assert allowed is True, f"Public contract should allow {action} to anyone"

    def test_self_owned_allows_self(self) -> None:
        """Self-owned contract allows artifact to access itself."""
        artifact = self._make_artifact(
            artifact_id="artifact1",
            access_contract_id="genesis_contract_self_owned",
            owner_id="owner1",
        )

        # Self access
        allowed, _ = self.executor._check_permission("artifact1", "read", artifact)
        assert allowed is True

    def test_self_owned_allows_owner(self) -> None:
        """Self-owned contract allows owner to access."""
        artifact = self._make_artifact(
            artifact_id="artifact1",
            access_contract_id="genesis_contract_self_owned",
            owner_id="owner1",
        )

        # Owner access
        allowed, _ = self.executor._check_permission("owner1", "read", artifact)
        assert allowed is True

    def test_self_owned_denies_stranger(self) -> None:
        """Self-owned contract denies access to strangers."""
        artifact = self._make_artifact(
            artifact_id="artifact1",
            access_contract_id="genesis_contract_self_owned",
            owner_id="owner1",
        )

        # Stranger denied
        allowed, _ = self.executor._check_permission("stranger", "read", artifact)
        assert allowed is False

    def test_legacy_mode_uses_freeware_contract(self) -> None:
        """Legacy policy mode now delegates to freeware contract (CAP-003).

        Before CAP-003: Owner had hardcoded bypass in _check_permission_legacy().
        After CAP-003: Legacy mode uses freeware contract semantics.

        Freeware contract:
        - READ, EXECUTE, INVOKE: Anyone can access (open access)
        - WRITE, DELETE, TRANSFER: Only owner can access

        This test verifies owner gets write access via freeware contract,
        not via special bypass.
        """
        import warnings
        from src.world.artifacts import Artifact
        from datetime import datetime

        artifact = Artifact(
            id="test",
            type="test",
            content="test",
            owner_id="owner1",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            policy={"allow_read": [], "allow_write": []},  # Empty lists - ignored now
        )

        # Legacy mode should emit deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Owner still has write access, but via freeware contract
            allowed, reason = self.executor_legacy._check_permission("owner1", "write", artifact)
            assert allowed is True
            assert "freeware" in reason.lower()  # Shows it's using freeware contract
            assert "owner access" in reason.lower()  # Freeware grants owner access

            # Verify deprecation warning was issued
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

    def test_legacy_mode_ignores_policy_uses_freeware(self) -> None:
        """Legacy policy mode ignores inline policy, uses freeware contract (CAP-003).

        Before CAP-003: Legacy mode respected allow_read, allow_write lists.
        After CAP-003: Legacy mode delegates to freeware contract which:
        - Allows anyone to READ (freeware: open access)
        - Only allows owner to WRITE (freeware: owner-only)

        The inline policy dict is ignored in favor of consistent contract behavior.
        """
        import warnings
        from src.world.artifacts import Artifact
        from datetime import datetime

        artifact = Artifact(
            id="test",
            type="test",
            content="test",
            owner_id="owner1",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            # These policy lists are now ignored - freeware contract takes over
            policy={"allow_read": [], "allow_write": ["alice"]},
        )

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            # Freeware: anyone can read (open access)
            allowed, _ = self.executor_legacy._check_permission("stranger", "read", artifact)
            assert allowed is True

            # Freeware: only owner can write (alice is NOT allowed despite policy)
            allowed, _ = self.executor_legacy._check_permission("alice", "write", artifact)
            assert allowed is False  # Changed: freeware doesn't respect allow_write list

            # Freeware: owner can write
            allowed, _ = self.executor_legacy._check_permission("owner1", "write", artifact)
            assert allowed is True

            # Freeware: non-owner bob cannot write
            allowed, _ = self.executor_legacy._check_permission("bob", "write", artifact)
            assert allowed is False

    def test_missing_contract_falls_back_to_freeware(self) -> None:
        """Unknown contract_id falls back to freeware."""
        artifact = self._make_artifact(access_contract_id="nonexistent_contract")

        # Should allow read (freeware default)
        allowed, _ = self.executor._check_permission("anyone", "read", artifact)
        assert allowed is True

        # Should deny write to non-owner (freeware default)
        allowed, _ = self.executor._check_permission("anyone", "write", artifact)
        assert allowed is False

    def test_unknown_action_denied(self) -> None:
        """Unknown action type is denied."""
        artifact = self._make_artifact(access_contract_id="genesis_contract_freeware")

        allowed, reason = self.executor._check_permission("anyone", "unknown_action", artifact)
        assert allowed is False
        assert "unknown" in reason.lower()

    def test_contract_caching(self) -> None:
        """Contracts are cached after first lookup."""
        artifact = self._make_artifact(access_contract_id="genesis_contract_freeware")

        # First call - should populate cache
        assert "genesis_contract_freeware" not in self.executor._contract_cache
        self.executor._check_permission("anyone", "read", artifact)
        assert "genesis_contract_freeware" in self.executor._contract_cache

        # Verify same contract is returned from cache
        contract1 = self.executor._get_contract("genesis_contract_freeware")
        contract2 = self.executor._get_contract("genesis_contract_freeware")
        assert contract1 is contract2

    def test_permission_result_includes_reason(self) -> None:
        """Permission denial includes contract's reason."""
        artifact = self._make_artifact(
            access_contract_id="genesis_contract_private",
            owner_id="owner1",
        )

        allowed, reason = self.executor._check_permission("stranger", "read", artifact)
        assert allowed is False
        assert len(reason) > 0  # Reason should not be empty
        assert "denied" in reason.lower() or "private" in reason.lower()

    def test_artifact_without_access_contract_id_defaults_to_freeware(self) -> None:
        """Artifacts without access_contract_id attribute use freeware."""
        from src.world.artifacts import Artifact
        from datetime import datetime

        # Create artifact WITHOUT setting access_contract_id
        artifact = Artifact(
            id="test",
            type="test",
            content="test",
            owner_id="owner1",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        # Should use freeware default (allows read)
        allowed, _ = self.executor._check_permission("anyone", "read", artifact)
        assert allowed is True


# Import Artifact type for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.world.artifacts import Artifact
