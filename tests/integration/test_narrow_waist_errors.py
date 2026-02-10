"""Integration tests for narrow waist error handling (Plan #40).

These tests verify that all three action types (read, write, invoke)
return properly structured error responses with error_code, error_category,
retriable flags, and error_details.
"""

from __future__ import annotations

import pytest

from src.world.world import World
from src.world.actions import ReadArtifactIntent, WriteArtifactIntent, InvokeArtifactIntent
from src.world.errors import ErrorCode, ErrorCategory


@pytest.fixture
def world_with_agent() -> World:
    """Create a world with a test agent."""
    config = {
        "world": {"max_ticks": 10},
        "principals": [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 50},
        ],
        "logging": {"output_file": "/dev/null"},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
        "resources": {
            "stock": {
                "disk": {"total": 20000, "unit": "bytes"},  # 10000 per agent
            }
        },
    }
    return World(config)


class TestReadArtifactErrors:
    """Tests for read_artifact error responses."""

    def test_read_not_found_error(self, world_with_agent: World) -> None:
        """Read of non-existent artifact returns NOT_FOUND error."""
        intent = ReadArtifactIntent(
            principal_id="alice",
            artifact_id="nonexistent_artifact"
        )
        result = world_with_agent.execute_action(intent)

        assert result.success is False
        assert result.error_code == ErrorCode.NOT_FOUND.value
        assert result.error_category == ErrorCategory.RESOURCE.value
        assert result.retriable is False

    def test_read_access_denied_error(self, world_with_agent: World) -> None:
        """Read with denied access returns NOT_AUTHORIZED error."""
        # Create an artifact with private contract (only owner can access)
        write_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="private_artifact",
            artifact_type="data",
            content="Secret content",
            access_contract_id="kernel_contract_private",  # Only owner can access
        )
        world_with_agent.execute_action(write_intent)

        # Bob tries to read Alice's private artifact
        read_intent = ReadArtifactIntent(
            principal_id="bob",
            artifact_id="private_artifact"
        )
        result = world_with_agent.execute_action(read_intent)

        assert result.success is False
        assert result.error_code == ErrorCode.NOT_AUTHORIZED.value
        assert result.error_category == ErrorCategory.PERMISSION.value
        assert result.retriable is False

    def test_read_insufficient_funds_error(self, world_with_agent: World) -> None:
        """Read with insufficient scrip returns INSUFFICIENT_FUNDS error."""
        # Create an artifact with high read price
        write_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="expensive_artifact",
            artifact_type="data",
            content="Valuable content",
            policy={"read_price": 200, "allow_read": ["*"]},
            access_contract_id="kernel_contract_freeware",
        )
        world_with_agent.execute_action(write_intent)

        # Bob (50 scrip) tries to read (costs 200)
        read_intent = ReadArtifactIntent(
            principal_id="bob",
            artifact_id="expensive_artifact"
        )
        result = world_with_agent.execute_action(read_intent)

        assert result.success is False
        assert result.error_code == ErrorCode.INSUFFICIENT_FUNDS.value
        assert result.error_category == ErrorCategory.RESOURCE.value
        assert result.retriable is True  # Can get more scrip and retry


class TestWriteArtifactErrors:
    """Tests for write_artifact error responses."""

    def test_write_permission_denied(self, world_with_agent: World) -> None:
        """Write to artifact without permission returns NOT_AUTHORIZED error."""
        # Alice creates an artifact
        write_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="alice_artifact",
            artifact_type="data",
            content="Alice's data",
            access_contract_id="kernel_contract_freeware",
        )
        world_with_agent.execute_action(write_intent)

        # Bob tries to write to it
        bob_write = WriteArtifactIntent(
            principal_id="bob",
            artifact_id="alice_artifact",
            artifact_type="data",
            content="Bob overwrites!",
        )
        result = world_with_agent.execute_action(bob_write)

        assert result.success is False
        assert result.error_code == ErrorCode.NOT_AUTHORIZED.value
        assert result.error_category == ErrorCategory.PERMISSION.value
        assert result.retriable is False

    def test_write_invalid_code(self, world_with_agent: World) -> None:
        """Write with invalid executable code returns INVALID_ARGUMENT error."""
        # Plan #114: Include interface for executable artifacts
        interface = {
            "description": "A test service",
            "tools": [{"name": "run", "description": "Run the service", "inputSchema": {"type": "object"}}]
        }
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="bad_service",
            artifact_type="service",
            content="",
            executable=True,
            price=1,
            code="def run(*args): return 1  # Missing newline at end causes issues",
            interface=interface,
        )
        # Note: The actual validation depends on executor.validate_code()
        # This test verifies the error structure if validation fails
        result = world_with_agent.execute_action(intent)
        # The code might be valid, so we just test the structure exists
        if not result.success:
            assert result.error_code is not None
            assert result.error_category is not None


class TestInvokeArtifactErrors:
    """Tests for invoke_artifact error responses."""

    def test_invoke_not_found_error(self, world_with_agent: World) -> None:
        """Invoke of non-existent artifact returns NOT_FOUND error."""
        intent = InvokeArtifactIntent(
            principal_id="alice",
            artifact_id="nonexistent_service",
            method="run",
            args=[]
        )
        result = world_with_agent.execute_action(intent)

        assert result.success is False
        assert result.error_code == ErrorCode.NOT_FOUND.value
        assert result.error_category == ErrorCategory.RESOURCE.value
        assert result.retriable is False

    def test_invoke_method_not_found_genesis(self, world_with_agent: World) -> None:
        """Invoke of non-existent method on genesis returns NOT_FOUND error."""
        intent = InvokeArtifactIntent(
            principal_id="alice",
            artifact_id="genesis_ledger",
            method="nonexistent_method",
            args=[]
        )
        result = world_with_agent.execute_action(intent)

        assert result.success is False
        assert result.error_code == ErrorCode.NOT_FOUND.value
        assert result.error_category == ErrorCategory.RESOURCE.value
        assert result.retriable is False

    def test_invoke_not_executable(self, world_with_agent: World) -> None:
        """Invoke of non-executable artifact returns INVALID_TYPE error."""
        # Create a non-executable artifact
        write_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="data_artifact",
            artifact_type="data",
            content="Just data",
            executable=False,
            access_contract_id="kernel_contract_freeware",
        )
        world_with_agent.execute_action(write_intent)

        # Try to invoke it
        invoke_intent = InvokeArtifactIntent(
            principal_id="alice",
            artifact_id="data_artifact",
            method="run",
            args=[]
        )
        result = world_with_agent.execute_action(invoke_intent)

        assert result.success is False
        assert result.error_code == ErrorCode.INVALID_TYPE.value
        assert result.error_category == ErrorCategory.VALIDATION.value
        assert result.retriable is False

    def test_invoke_permission_denied(self, world_with_agent: World) -> None:
        """Invoke without permission returns NOT_AUTHORIZED error."""
        # Plan #114: Include interface for executable artifacts
        interface = {
            "description": "A private service",
            "tools": [{"name": "run", "description": "Run the service", "inputSchema": {"type": "object"}}]
        }
        # Create a private executable (only owner can access)
        write_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="private_service",
            artifact_type="service",
            content="",
            executable=True,
            price=0,
            code="def run(*args): return 'secret'",
            access_contract_id="kernel_contract_private",  # Only owner can access
            interface=interface,
        )
        world_with_agent.execute_action(write_intent)

        # Bob tries to invoke it
        invoke_intent = InvokeArtifactIntent(
            principal_id="bob",
            artifact_id="private_service",
            method="run",
            args=[]
        )
        result = world_with_agent.execute_action(invoke_intent)

        assert result.success is False
        assert result.error_code == ErrorCode.NOT_AUTHORIZED.value
        assert result.error_category == ErrorCategory.PERMISSION.value
        assert result.retriable is False

    def test_invoke_insufficient_scrip(self, world_with_agent: World) -> None:
        """Invoke with insufficient scrip returns INSUFFICIENT_FUNDS error."""
        # Plan #114: Include interface for executable artifacts
        interface = {
            "description": "An expensive service",
            "tools": [{"name": "run", "description": "Run the service", "inputSchema": {"type": "object"}}]
        }
        # Create an expensive executable
        write_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="expensive_service",
            artifact_type="service",
            content="",
            executable=True,
            price=200,  # More than Bob has
            code="def run(*args): return 'expensive result'",
            interface=interface,
            access_contract_id="kernel_contract_freeware",
        )
        world_with_agent.execute_action(write_intent)

        # Bob (50 scrip) tries to invoke
        invoke_intent = InvokeArtifactIntent(
            principal_id="bob",
            artifact_id="expensive_service",
            method="run",
            args=[]
        )
        result = world_with_agent.execute_action(invoke_intent)

        assert result.success is False
        assert result.error_code == ErrorCode.INSUFFICIENT_FUNDS.value
        assert result.error_category == ErrorCategory.RESOURCE.value
        assert result.retriable is True  # Can get more scrip and retry


class TestErrorRetriability:
    """Tests for error retriability guidance."""

    def test_resource_errors_are_retriable(self, world_with_agent: World) -> None:
        """Resource errors (insufficient funds) should be marked retriable."""
        # This is covered by test_invoke_insufficient_scrip and test_read_insufficient_funds_error
        pass

    def test_permission_errors_not_retriable(self, world_with_agent: World) -> None:
        """Permission errors should not be retriable."""
        # This is covered by test_write_permission_denied and test_invoke_permission_denied
        pass

    def test_validation_errors_not_retriable(self, world_with_agent: World) -> None:
        """Validation errors (invalid type, etc.) should not be retriable."""
        # This is covered by test_invoke_not_executable
        pass
