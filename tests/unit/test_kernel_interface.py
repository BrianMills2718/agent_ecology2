"""Unit tests for Kernel State/Actions interfaces - Plan #39

Tests that kernel interfaces provide equal access to all artifacts
(genesis and agent-built) without privilege.
"""

import pytest
import tempfile
from typing import Any

from src.world.world import World
from src.world.kernel_interface import KernelState, KernelActions


@pytest.fixture
def world_config() -> dict[str, Any]:
    """Minimal world config for testing."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output_file = f.name

    return {
        "world": {},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
        "logging": {"output_file": output_file},
        "principals": [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 200},
        ],
        "rights": {
            "default_quotas": {"compute": 100.0, "disk": 10000.0}
        },
        "rate_limiting": {
            "enabled": True,
            "window_seconds": 60.0,
            "resources": {"llm_tokens": {"max_per_window": 1000}}
        },
    }


@pytest.fixture
def world(world_config: dict[str, Any]) -> World:
    """Create world instance."""
    return World(world_config)


class TestKernelStateRead:
    """Test KernelState read operations."""

    def test_get_balance_public(self, world: World) -> None:
        """Any caller can read any principal's balance."""
        state = KernelState(world)

        # Alice can read Bob's balance
        assert state.get_balance("bob") == 200
        # Bob can read Alice's balance
        assert state.get_balance("alice") == 100

    def test_get_resource_public(self, world: World) -> None:
        """Any caller can read any principal's stock resources."""
        state = KernelState(world)
        world.increment_event_counter()

        # Set up test resources in ledger (disk is tracked by rights_registry, not ledger)
        world.ledger.credit_resource("alice", "test_resource", 100.0)
        world.ledger.credit_resource("bob", "test_resource", 200.0)

        # Can read stock resources
        assert state.get_resource("alice", "test_resource") == 100.0
        assert state.get_resource("bob", "test_resource") == 200.0

    def test_list_artifacts_by_owner_public(self, world: World) -> None:
        """Any caller can list artifacts owned by any principal."""
        state = KernelState(world)

        # Create some artifacts
        world.artifacts.write("art_1", "generic", "content1", "alice")
        world.artifacts.write("art_2", "generic", "content2", "alice")
        world.artifacts.write("art_3", "generic", "content3", "bob")

        # Can list anyone's artifacts
        assert set(state.list_artifacts_by_owner("alice")) == {"art_1", "art_2"}
        assert set(state.list_artifacts_by_owner("bob")) == {"art_3"}

    def test_get_artifact_metadata_public(self, world: World) -> None:
        """Any caller can read artifact metadata."""
        state = KernelState(world)

        world.artifacts.write("test_art", "generic", "content", "alice")

        metadata = state.get_artifact_metadata("test_art")
        assert metadata is not None
        assert metadata["created_by"] == "alice"
        assert metadata["type"] == "generic"
        assert "id" in metadata

    def test_get_nonexistent_returns_none(self, world: World) -> None:
        """Querying nonexistent data returns None, not error."""
        state = KernelState(world)

        assert state.get_artifact_metadata("nonexistent") is None
        assert state.list_artifacts_by_owner("nonexistent") == []


class TestKernelStateAccessControl:
    """Test that artifact content respects access controls."""

    def test_read_artifact_owner_allowed(self, world: World) -> None:
        """Owner can read their own artifact content."""
        state = KernelState(world)

        world.artifacts.write("alice_art", "generic", "secret content", "alice")

        # Alice (owner) can read
        content = state.read_artifact("alice_art", caller_id="alice")
        assert content == "secret content"

    def test_read_artifact_non_owner_default_allowed(self, world: World) -> None:
        """By default, artifacts are readable by anyone."""
        state = KernelState(world)

        world.artifacts.write("alice_art", "generic", "public content", "alice")

        # Bob can read Alice's artifact (default policy allows read)
        content = state.read_artifact("alice_art", caller_id="bob")
        assert content == "public content"


class TestKernelActionsVerifyCaller:
    """Test that KernelActions verifies caller identity."""

    def test_transfer_scrip_from_self(self, world: World) -> None:
        """Can transfer scrip from own account."""
        actions = KernelActions(world)

        # Alice transfers to Bob
        result = actions.transfer_scrip(caller_id="alice", to="bob", amount=50)
        assert result is True

        # Verify balances changed
        assert world.ledger.get_scrip("alice") == 50
        assert world.ledger.get_scrip("bob") == 250

    def test_transfer_scrip_insufficient_funds(self, world: World) -> None:
        """Cannot transfer more than balance."""
        actions = KernelActions(world)

        # Alice tries to transfer more than she has
        result = actions.transfer_scrip(caller_id="alice", to="bob", amount=500)
        assert result is False

        # Balances unchanged
        assert world.ledger.get_scrip("alice") == 100
        assert world.ledger.get_scrip("bob") == 200

    def test_transfer_resource_from_self(self, world: World) -> None:
        """Can transfer stock resources from own account."""
        actions = KernelActions(world)
        world.increment_event_counter()

        # Set up test resources in ledger (disk is tracked by rights_registry)
        world.ledger.credit_resource("alice", "test_resource", 100.0)
        world.ledger.credit_resource("bob", "test_resource", 100.0)

        # Alice transfers test_resource to Bob
        result = actions.transfer_resource(
            caller_id="alice", to="bob", resource="test_resource", amount=30.0
        )
        assert result is True

        # Verify resources changed
        assert world.ledger.get_resource("alice", "test_resource") == 70.0
        assert world.ledger.get_resource("bob", "test_resource") == 130.0


class TestKernelInterfaceEquality:
    """Test that genesis and agent artifacts get equal access."""

    def test_interface_available_in_sandbox(self, world: World) -> None:
        """Kernel interfaces are available to artifact code."""
        # This tests that when we execute artifact code,
        # kernel_state and kernel_actions are in the sandbox globals
        from src.world.executor import SafeExecutor

        executor = SafeExecutor(ledger=world.ledger)

        # Create an artifact that uses kernel_state
        artifact_code = '''
def run(*args):
    # kernel_state should be available in sandbox
    balance = kernel_state.get_balance("alice")
    return {"balance": balance}
'''
        world.artifacts.write(
            "test_artifact",
            "executable",
            artifact_code,
            "alice",
            executable=True,
            code=artifact_code
        )

        # Execute the artifact
        result = executor.execute_with_invoke(
            artifact_code,
            args=[],
            artifact_id="test_artifact",
            caller_id="bob",
            ledger=world.ledger,
            artifact_store=world.artifacts,
            world=world
        )

        assert result["success"]
        assert result["result"].get("balance") == 100

    def test_agent_can_build_ledger_equivalent(self, world: World) -> None:
        """Agent-built artifact can provide same functionality as genesis_ledger."""
        from src.world.executor import SafeExecutor

        executor = SafeExecutor(ledger=world.ledger)

        # Agent creates a "my_ledger" artifact that wraps kernel interfaces
        my_ledger_code = '''
def run(*args):
    method = args[0] if args else None

    if method == "get_balance":
        target = args[1] if len(args) > 1 else None
        return {"balance": kernel_state.get_balance(target)}

    elif method == "transfer":
        to = args[1] if len(args) > 1 else None
        amount = args[2] if len(args) > 2 else 0
        # caller_id is injected by kernel
        success = kernel_actions.transfer_scrip(caller_id, to, amount)
        return {"success": success}

    return {"error": "unknown method"}
'''
        world.artifacts.write(
            "my_ledger",
            "executable",
            my_ledger_code,
            "bob",
            executable=True,
            code=my_ledger_code
        )

        # Use my_ledger to check balance (should work like genesis_ledger)
        result = executor.execute_with_invoke(
            my_ledger_code,
            args=["get_balance", "alice"],
            artifact_id="my_ledger",
            caller_id="bob",
            ledger=world.ledger,
            artifact_store=world.artifacts,
            world=world
        )

        assert result["success"]
        assert result["result"].get("balance") == 100


