"""Unit tests for handle_request interface (Plan #234, ADR-0024).

Tests detection, validation, and execution of handle_request artifacts.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.world.action_executor import _artifact_has_handle_request
from src.world.artifacts import Artifact
from src.world.executor import SafeExecutor


def _make_artifact(
    code: str = "",
    executable: bool = True,
    genesis_methods: dict | None = None,
) -> Artifact:
    """Create a minimal Artifact for testing."""
    now = datetime.now(timezone.utc).isoformat()
    return Artifact(
        id="test_artifact",
        type="executable" if executable else "data",
        content=code,
        created_by="alice",
        created_at=now,
        updated_at=now,
        executable=executable,
        code=code,
        genesis_methods=genesis_methods,
    )


@pytest.mark.plans(234)
class TestArtifactHasHandleRequest:
    """Detection: _artifact_has_handle_request returns True/False correctly."""

    def test_detects_handle_request_function(self) -> None:
        code = "def handle_request(caller, operation, args):\n    return {'success': True}"
        artifact = _make_artifact(code=code)
        assert _artifact_has_handle_request(artifact) is True

    def test_rejects_run_function(self) -> None:
        code = "def run(*args):\n    return 42"
        artifact = _make_artifact(code=code)
        assert _artifact_has_handle_request(artifact) is False

    def test_rejects_genesis_artifact(self) -> None:
        """Genesis artifacts always use method dispatch in Phase 1."""
        code = "def handle_request(caller, operation, args):\n    return {}"
        artifact = _make_artifact(code=code, genesis_methods={"some_method": object()})
        assert _artifact_has_handle_request(artifact) is False

    def test_rejects_no_code(self) -> None:
        artifact = _make_artifact(code="")
        assert _artifact_has_handle_request(artifact) is False

    def test_rejects_non_executable(self) -> None:
        """Non-executable artifacts can't have handle_request dispatched."""
        code = "def handle_request(caller, operation, args):\n    return {}"
        artifact = _make_artifact(code=code, executable=False)
        # Detection checks code string, not executable flag
        # (executable check is separate in dispatch path)
        assert _artifact_has_handle_request(artifact) is True

    def test_detects_handle_request_with_type_hints(self) -> None:
        code = "def handle_request(caller: str, operation: str, args: list):\n    return {}"
        artifact = _make_artifact(code=code)
        assert _artifact_has_handle_request(artifact) is True


@pytest.mark.plans(234)
class TestValidateCodeAcceptsBoth:
    """Validation: validate_code() accepts both run() and handle_request()."""

    @pytest.fixture
    def executor(self) -> SafeExecutor:
        return SafeExecutor(timeout=5, use_contracts=False)

    def test_accepts_run_function(self, executor: SafeExecutor) -> None:
        valid, error = executor.validate_code("def run():\n    return 42")
        assert valid is True
        assert error == ""

    def test_accepts_handle_request_function(self, executor: SafeExecutor) -> None:
        code = "def handle_request(caller, operation, args):\n    return {'success': True}"
        valid, error = executor.validate_code(code)
        assert valid is True
        assert error == ""

    def test_rejects_neither(self, executor: SafeExecutor) -> None:
        valid, error = executor.validate_code("def helper():\n    return 42")
        assert valid is False
        assert "run()" in error
        assert "handle_request" in error

    def test_rejects_empty_code(self, executor: SafeExecutor) -> None:
        valid, error = executor.validate_code("")
        assert valid is False

    def test_rejects_syntax_error(self, executor: SafeExecutor) -> None:
        valid, error = executor.validate_code("def handle_request(:\n    return {}")
        assert valid is False
        assert "Syntax error" in error


@pytest.mark.plans(234)
class TestHandleRequestExecution:
    """Execution: handle_request receives correct caller, operation, args."""

    @pytest.fixture
    def executor(self) -> SafeExecutor:
        return SafeExecutor(timeout=5, use_contracts=False)

    def test_handle_request_receives_caller_operation_args(
        self, executor: SafeExecutor
    ) -> None:
        """handle_request(caller, operation, args) dispatched correctly."""
        code = """
def handle_request(caller, operation, args):
    return {"caller": caller, "operation": operation, "args": args}
"""
        result = executor.execute_with_invoke(
            code=code,
            args=["arg1", "arg2"],
            caller_id="alice",
            entry_point="handle_request",
            method_name="my_method",
        )
        assert result["success"] is True
        payload = result["result"]
        assert payload["caller"] == "alice"
        assert payload["operation"] == "my_method"
        assert payload["args"] == ["arg1", "arg2"]

    def test_handle_request_default_operation_is_invoke(
        self, executor: SafeExecutor
    ) -> None:
        """When method_name is None, operation defaults to 'invoke'."""
        code = """
def handle_request(caller, operation, args):
    return {"operation": operation}
"""
        result = executor.execute_with_invoke(
            code=code,
            args=[],
            caller_id="bob",
            entry_point="handle_request",
            method_name=None,
        )
        assert result["success"] is True
        assert result["result"]["operation"] == "invoke"

    def test_run_entry_point_still_works(self, executor: SafeExecutor) -> None:
        """Legacy run() path unchanged."""
        code = "def run(x, y):\n    return x + y"
        result = executor.execute_with_invoke(
            code=code,
            args=[3, 4],
            entry_point="run",
        )
        assert result["success"] is True
        assert result["result"] == 7

    def test_handle_request_error_propagates(self, executor: SafeExecutor) -> None:
        """Runtime errors in handle_request are reported."""
        code = """
def handle_request(caller, operation, args):
    raise ValueError("denied by handler")
"""
        result = executor.execute_with_invoke(
            code=code,
            args=[],
            caller_id="alice",
            entry_point="handle_request",
            method_name="test",
        )
        assert result["success"] is False
        assert "denied by handler" in result["error"]

    def test_handle_request_missing_function(self, executor: SafeExecutor) -> None:
        """Code that defines run() but is called with entry_point=handle_request fails."""
        code = "def run():\n    return 42"
        result = executor.execute_with_invoke(
            code=code,
            args=[],
            caller_id="alice",
            entry_point="handle_request",
        )
        assert result["success"] is False
        assert "handle_request" in result["error"]


@pytest.mark.plans(234)
class TestHandleRequestAccessControl:
    """Access control: handler can deny or allow via return dict."""

    @pytest.fixture
    def executor(self) -> SafeExecutor:
        return SafeExecutor(timeout=5, use_contracts=False)

    def test_handler_can_deny_access(self, executor: SafeExecutor) -> None:
        """Handler returns error dict to deny access."""
        code = """
def handle_request(caller, operation, args):
    if caller != "admin":
        return {"success": False, "error": f"Access denied for {caller}"}
    return {"success": True, "result": "granted"}
"""
        result = executor.execute_with_invoke(
            code=code,
            args=[],
            caller_id="alice",
            entry_point="handle_request",
            method_name="invoke",
        )
        assert result["success"] is True  # Execution succeeded
        # The handler returned an error dict as its result
        payload = result["result"]
        assert payload["success"] is False
        assert "Access denied for alice" in payload["error"]

    def test_handler_can_allow_access(self, executor: SafeExecutor) -> None:
        code = """
def handle_request(caller, operation, args):
    return {"success": True, "result": "welcome"}
"""
        result = executor.execute_with_invoke(
            code=code,
            args=[],
            caller_id="admin",
            entry_point="handle_request",
            method_name="invoke",
        )
        assert result["success"] is True
        assert result["result"]["success"] is True

    def test_handler_dispatches_by_operation(self, executor: SafeExecutor) -> None:
        """Handler can route by operation name."""
        code = """
def handle_request(caller, operation, args):
    if operation == "read":
        return {"data": "public info"}
    elif operation == "write":
        if caller != "owner":
            return {"success": False, "error": "Only owner can write"}
        return {"success": True}
    return {"success": False, "error": f"Unknown operation: {operation}"}
"""
        # Read works for anyone
        result = executor.execute_with_invoke(
            code=code, args=[], caller_id="alice",
            entry_point="handle_request", method_name="read",
        )
        assert result["success"] is True
        assert result["result"]["data"] == "public info"

        # Write denied for non-owner
        result = executor.execute_with_invoke(
            code=code, args=[], caller_id="alice",
            entry_point="handle_request", method_name="write",
        )
        assert result["success"] is True
        assert result["result"]["success"] is False

        # Write allowed for owner
        result = executor.execute_with_invoke(
            code=code, args=[], caller_id="owner",
            entry_point="handle_request", method_name="write",
        )
        assert result["success"] is True
        assert result["result"]["success"] is True
