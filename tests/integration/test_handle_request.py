"""Integration tests for handle_request interface (Plan #234, ADR-0024).

Tests the full invoke flow: permission skip, handler denial, backwards compat,
nested invocation, and charge delegation interaction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.world.world import World, ConfigDict
from src.world.actions import InvokeArtifactIntent
from src.world.kernel_interface import KernelActions, KernelState


@pytest.fixture
def world_for_handle_request(tmp_path: Path) -> World:
    """World configured for handle_request testing."""
    log_file = tmp_path / "handle_request_test.jsonl"
    config: ConfigDict = {
        "world": {},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
        "logging": {"output_file": str(log_file)},
        "principals": [
            {"id": "alice", "starting_scrip": 1000},
            {"id": "bob", "starting_scrip": 500},
        ],
        "rights": {
            "default_quotas": {"compute": 100.0, "disk": 10000.0},
        },
    }
    world = World(config)
    world.increment_event_counter()
    return world


def _write_executable(
    world: World,
    artifact_id: str,
    code: str,
    created_by: str,
    price: int = 0,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Helper to write an executable artifact."""
    world.artifacts.write(
        artifact_id,
        "executable",
        code,
        created_by,
        executable=True,
        price=price,
        code=code,
        metadata=metadata or {},
    )


@pytest.mark.plans(234)
class TestHandleRequestPermissionSkip:
    """handle_request artifacts skip kernel permission check."""

    def test_handle_request_invoked_without_kernel_permission_check(
        self, world_for_handle_request: World
    ) -> None:
        """handle_request artifact is invocable even with restrictive contract."""
        w = world_for_handle_request

        # Create artifact with handle_request
        code = """
def handle_request(caller, operation, args):
    return {"success": True, "result": f"hello {caller}"}
"""
        _write_executable(w, "hr_service", code, "alice")

        # Set restrictive access contract that would block run() artifacts
        artifact = w.artifacts.get("hr_service")
        assert artifact is not None
        artifact.access_contract_id = "genesis_contract_private"

        # Bob invokes — kernel permission check is skipped for handle_request
        intent = InvokeArtifactIntent(
            principal_id="bob",
            artifact_id="hr_service",
            method="run",
        )
        result = w.execute_action(intent)
        assert result.success, f"Expected success but got: {result.message}"
        assert "hello bob" in str(result.data)


@pytest.mark.plans(234)
class TestHandleRequestBackwardsCompat:
    """run() artifacts still get kernel permission check."""

    def test_run_artifact_still_checked_by_kernel(
        self, world_for_handle_request: World
    ) -> None:
        """Legacy run() artifact with private contract is blocked."""
        w = world_for_handle_request

        code = "def run(*args):\n    return 'secret'"
        _write_executable(w, "private_service", code, "alice")

        # Set private contract
        artifact = w.artifacts.get("private_service")
        assert artifact is not None
        artifact.access_contract_id = "genesis_contract_private"

        # Bob tries to invoke — should be denied by kernel permission
        intent = InvokeArtifactIntent(
            principal_id="bob",
            artifact_id="private_service",
            method="run",
        )
        result = w.execute_action(intent)
        assert result.success is False

    def test_run_artifact_freeware_still_works(
        self, world_for_handle_request: World
    ) -> None:
        """Legacy run() artifact with freeware contract still invocable."""
        w = world_for_handle_request

        code = "def run(*args):\n    return 42"
        _write_executable(w, "free_service", code, "alice")

        intent = InvokeArtifactIntent(
            principal_id="bob",
            artifact_id="free_service",
            method="run",
        )
        result = w.execute_action(intent)
        assert result.success, f"Expected success: {result.message}"
        assert result.data.get("result") == 42


@pytest.mark.plans(234)
class TestHandleRequestHandlerDenial:
    """Handler can deny access, and caller gets the error."""

    def test_handler_denial_propagated_to_caller(
        self, world_for_handle_request: World
    ) -> None:
        """When handler returns error, caller sees it in action result."""
        w = world_for_handle_request

        code = """
def handle_request(caller, operation, args):
    if caller != "alice":
        return {"success": False, "error": f"Only alice allowed, not {caller}"}
    return {"success": True, "result": "welcome alice"}
"""
        _write_executable(w, "restricted_service", code, "alice")

        # Bob invokes — handler denies
        intent = InvokeArtifactIntent(
            principal_id="bob",
            artifact_id="restricted_service",
            method="access",
        )
        result = w.execute_action(intent)
        # Execution itself succeeds (handler ran), but handler returned denial
        assert result.success is True
        payload = result.data.get("result", {})
        assert payload.get("success") is False
        assert "Only alice allowed" in payload.get("error", "")

    def test_handler_allows_authorized_caller(
        self, world_for_handle_request: World
    ) -> None:
        w = world_for_handle_request

        code = """
def handle_request(caller, operation, args):
    if caller != "alice":
        return {"success": False, "error": "denied"}
    return {"success": True, "result": "welcome"}
"""
        _write_executable(w, "restricted_service", code, "alice")

        intent = InvokeArtifactIntent(
            principal_id="alice",
            artifact_id="restricted_service",
            method="access",
        )
        result = w.execute_action(intent)
        assert result.success is True
        payload = result.data.get("result", {})
        assert payload.get("success") is True


@pytest.mark.plans(234)
class TestHandleRequestNestedInvoke:
    """handle_request artifact invoked from another artifact."""

    def test_nested_invoke_of_handle_request_artifact(
        self, world_for_handle_request: World
    ) -> None:
        """Artifact A (run) invokes Artifact B (handle_request)."""
        w = world_for_handle_request

        # Create handle_request service
        hr_code = """
def handle_request(caller, operation, args):
    return {"success": True, "result": f"served {caller} via {operation}"}
"""
        _write_executable(w, "hr_backend", hr_code, "alice")

        # Create run() artifact that invokes the handle_request artifact
        caller_code = """
def run(*args):
    result = invoke("hr_backend", "test_data")
    return result
"""
        _write_executable(w, "caller_artifact", caller_code, "bob")

        intent = InvokeArtifactIntent(
            principal_id="bob",
            artifact_id="caller_artifact",
            method="run",
        )
        result = w.execute_action(intent)
        assert result.success, f"Expected success: {result.message}"
        # The outer result is the invoke() return dict from caller_artifact
        invoke_result = result.data.get("result", {})
        assert invoke_result.get("success") is True
        # The inner result is from hr_backend's handle_request
        hr_result = invoke_result.get("result", {})
        assert hr_result.get("success") is True
        assert "served" in hr_result.get("result", "")


@pytest.mark.plans([234, 236])
class TestHandleRequestChargeIntegration:
    """handle_request works with Plan #236 charge delegation."""

    def test_handle_request_with_charge_to_caller(
        self, world_for_handle_request: World
    ) -> None:
        """handle_request artifact with price charges the caller."""
        w = world_for_handle_request
        state = KernelState(w)

        bob_initial = state.get_balance("bob")

        code = """
def handle_request(caller, operation, args):
    return {"success": True, "result": "served"}
"""
        _write_executable(w, "paid_hr_service", code, "alice", price=25)

        intent = InvokeArtifactIntent(
            principal_id="bob",
            artifact_id="paid_hr_service",
            method="run",
        )
        result = w.execute_action(intent)
        assert result.success, f"Expected success: {result.message}"

        # Bob should have been charged 25 scrip
        assert state.get_balance("bob") == bob_initial - 25


@pytest.mark.plans(234)
class TestHandleRequestOperationRouting:
    """method_name from InvokeArtifactIntent flows to handle_request."""

    def test_method_name_passed_as_operation(
        self, world_for_handle_request: World
    ) -> None:
        """The intent's method field becomes the operation parameter."""
        w = world_for_handle_request

        code = """
def handle_request(caller, operation, args):
    return {"caller": caller, "operation": operation, "args_len": len(args)}
"""
        _write_executable(w, "routing_service", code, "alice")

        intent = InvokeArtifactIntent(
            principal_id="bob",
            artifact_id="routing_service",
            method="get_status",
            args=["param1"],
        )
        result = w.execute_action(intent)
        assert result.success, f"Expected success: {result.message}"
        payload = result.data.get("result", {})
        assert payload["caller"] == "bob"
        assert payload["operation"] == "get_status"
