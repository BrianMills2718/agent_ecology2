"""Unit tests for self-referencing contract bootstrap and kernel contract rejection (Plan #317).

Tests:
1. Self-referencing bootstrap succeeds (executable + check_permission)
2. Self-referencing fails without check_permission
3. Self-referencing fails for non-executable
4. Kernel contract rejection when config is False
5. Kernel contracts allowed when config is True (default)
6. Agent-created contract resolves during permission checks
7. Genesis artifacts still work (kernel contracts still resolve for reads/writes)
"""

from __future__ import annotations

import pytest

from src.world.world import World
from src.world.actions import (
    WriteArtifactIntent,
    ReadArtifactIntent,
)
from src.world.artifacts import ArtifactStore
from src.world.contracts import ExecutableContract, PermissionAction, PermissionResult
from src.world.errors import ErrorCode, ErrorCategory
from src.world.permission_checker import get_contract_with_fallback_info


SELF_REF_CONTRACT_CODE = """\
def check_permission(caller, action, target, context, ledger):
    state = context.get('_artifact_state', {})
    writer = state.get('writer', '')
    if action in ('write', 'edit', 'delete'):
        return {'allowed': caller == writer, 'reason': 'writer-only modify'}
    return {'allowed': True, 'reason': 'public read/invoke'}
"""


@pytest.fixture
def world_kernel_contracts_disabled() -> World:
    """Create a world with kernel contracts disabled for agents."""
    config = {
        "world": {"max_ticks": 10},
        "principals": [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 100},
        ],
        "logging": {"output_file": "/dev/null"},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
        "contracts": {
            "allow_kernel_contracts_for_agents": False,
        },
    }
    return World(config)


@pytest.fixture
def world_kernel_contracts_enabled() -> World:
    """Create a world with kernel contracts enabled (default)."""
    config = {
        "world": {"max_ticks": 10},
        "principals": [
            {"id": "alice", "starting_scrip": 100},
        ],
        "logging": {"output_file": "/dev/null"},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
        "contracts": {
            "allow_kernel_contracts_for_agents": True,
        },
    }
    return World(config)


class TestSelfReferencingBootstrap:
    """Test that self-referencing contract bootstrap works."""

    def test_bootstrap_succeeds(self, world_kernel_contracts_disabled: World) -> None:
        """Self-referencing executable artifact with check_permission creates successfully."""
        w = world_kernel_contracts_disabled
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="alice_contract",
            artifact_type="contract",
            content="Access contract for alice's artifacts",
            code=SELF_REF_CONTRACT_CODE,
            executable=True,
            access_contract_id="alice_contract",  # self-referencing
        )
        result = w.execute_action(intent)
        assert result.success is True, f"Expected success, got: {result.message}"

        # Verify artifact was created
        artifact = w.artifacts.get("alice_contract")
        assert artifact is not None
        assert artifact.executable is True
        assert artifact.access_contract_id == "alice_contract"

    def test_bootstrap_fails_not_executable(
        self, world_kernel_contracts_disabled: World
    ) -> None:
        """Self-referencing non-executable artifact fails."""
        w = world_kernel_contracts_disabled
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="bad_contract",
            artifact_type="contract",
            content="Not executable",
            executable=False,
            access_contract_id="bad_contract",
        )
        result = w.execute_action(intent)
        assert result.success is False
        assert "must be executable" in result.message
        assert result.error_code == ErrorCode.INVALID_ARGUMENT.value

    def test_bootstrap_fails_no_check_permission(
        self, world_kernel_contracts_disabled: World
    ) -> None:
        """Self-referencing executable without check_permission fails."""
        w = world_kernel_contracts_disabled
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="bad_contract",
            artifact_type="contract",
            content="Missing check_permission",
            code="def run(): return 'hello'",
            executable=True,
            access_contract_id="bad_contract",
        )
        result = w.execute_action(intent)
        assert result.success is False
        assert "check_permission()" in result.message
        assert result.error_code == ErrorCode.INVALID_ARGUMENT.value


class TestKernelContractRejection:
    """Test that kernel contracts are rejected for new artifacts when disabled."""

    def test_kernel_freeware_rejected(
        self, world_kernel_contracts_disabled: World
    ) -> None:
        """kernel_contract_freeware is rejected for new artifacts."""
        w = world_kernel_contracts_disabled
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="my_doc",
            artifact_type="data",
            content="hello",
            access_contract_id="kernel_contract_freeware",
        )
        result = w.execute_action(intent)
        assert result.success is False
        assert "Kernel contracts are disabled" in result.message
        assert "self-referencing" in result.message
        assert result.error_code == ErrorCode.NOT_AUTHORIZED.value
        assert result.retriable is True

    def test_kernel_private_rejected(
        self, world_kernel_contracts_disabled: World
    ) -> None:
        """kernel_contract_private is rejected for new artifacts."""
        w = world_kernel_contracts_disabled
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="my_doc",
            artifact_type="data",
            content="hello",
            access_contract_id="kernel_contract_private",
        )
        result = w.execute_action(intent)
        assert result.success is False
        assert "Kernel contracts are disabled" in result.message

    def test_kernel_contracts_allowed_when_enabled(
        self, world_kernel_contracts_enabled: World
    ) -> None:
        """Kernel contracts work normally when allow_kernel_contracts_for_agents is True."""
        w = world_kernel_contracts_enabled
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="my_doc",
            artifact_type="data",
            content="hello",
            access_contract_id="kernel_contract_freeware",
        )
        result = w.execute_action(intent)
        assert result.success is True

    def test_non_kernel_contract_id_not_rejected(
        self, world_kernel_contracts_disabled: World
    ) -> None:
        """Non-kernel contract IDs are not blocked by the rejection check.

        They will still fail if the contract doesn't exist (dangling),
        but the error is different from kernel contract rejection.
        """
        w = world_kernel_contracts_disabled
        # First create a self-referencing contract
        contract_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="alice_contract",
            artifact_type="contract",
            content="My contract",
            code=SELF_REF_CONTRACT_CODE,
            executable=True,
            access_contract_id="alice_contract",
        )
        result = w.execute_action(contract_intent)
        assert result.success is True

        # Now create an artifact using the agent-created contract
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="my_doc",
            artifact_type="data",
            content="hello",
            access_contract_id="alice_contract",
        )
        result = w.execute_action(intent)
        assert result.success is True


class TestAgentCreatedContractResolution:
    """Test that agent-created contracts resolve during permission checks."""

    def test_agent_contract_resolves_for_read(
        self, world_kernel_contracts_disabled: World
    ) -> None:
        """Agent-created contract is found in artifact store during read permission check."""
        w = world_kernel_contracts_disabled

        # Create self-referencing contract
        contract_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="alice_contract",
            artifact_type="contract",
            content="My contract",
            code=SELF_REF_CONTRACT_CODE,
            executable=True,
            access_contract_id="alice_contract",
        )
        w.execute_action(contract_intent)

        # Create artifact using that contract
        write_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="my_doc",
            artifact_type="data",
            content="readable content",
            access_contract_id="alice_contract",
        )
        w.execute_action(write_intent)

        # Anyone can read (per the contract code: public read/invoke)
        read_intent = ReadArtifactIntent(
            principal_id="bob",
            artifact_id="my_doc",
        )
        result = w.execute_action(read_intent)
        assert result.success is True
        assert result.data is not None
        assert result.data["artifact"]["content"] == "readable content"

    def test_agent_contract_enforces_write_restriction(
        self, world_kernel_contracts_disabled: World
    ) -> None:
        """Agent-created contract properly restricts writes to writer only."""
        w = world_kernel_contracts_disabled

        # Create self-referencing contract
        contract_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="alice_contract",
            artifact_type="contract",
            content="My contract",
            code=SELF_REF_CONTRACT_CODE,
            executable=True,
            access_contract_id="alice_contract",
        )
        w.execute_action(contract_intent)

        # Create artifact using that contract
        write_intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="my_doc",
            artifact_type="data",
            content="alice's content",
            access_contract_id="alice_contract",
        )
        w.execute_action(write_intent)

        # Bob tries to overwrite — should be denied
        overwrite_intent = WriteArtifactIntent(
            principal_id="bob",
            artifact_id="my_doc",
            artifact_type="data",
            content="bob's content",
            access_contract_id="alice_contract",
        )
        result = w.execute_action(overwrite_intent)
        assert result.success is False


class TestArtifactStoreLookup:
    """Test the artifact store lookup in get_contract_with_fallback_info."""

    def test_artifact_store_lookup_finds_contract(self) -> None:
        """Executable artifact with check_permission is found as contract."""
        store = ArtifactStore()
        store.write(
            artifact_id="my_contract",
            type="contract",
            content="contract",
            created_by="alice",
            code=SELF_REF_CONTRACT_CODE,
            executable=True,
            access_contract_id="my_contract",
        )
        cache: dict[str, object] = {}
        dangling: list[int] = [0]
        contract, is_fallback, orig_id = get_contract_with_fallback_info(
            "my_contract", cache, dangling, artifact_store=store  # type: ignore[arg-type]
        )
        assert isinstance(contract, ExecutableContract)
        assert is_fallback is False
        assert orig_id is None
        assert dangling[0] == 0  # Not counted as dangling

    def test_artifact_store_non_executable_falls_through(self) -> None:
        """Non-executable artifact in store is not used as contract."""
        store = ArtifactStore()
        store.write(
            artifact_id="not_a_contract",
            type="data",
            content="just data",
            created_by="alice",
            access_contract_id="kernel_contract_freeware",
        )
        cache: dict[str, object] = {}
        dangling: list[int] = [0]
        contract, is_fallback, orig_id = get_contract_with_fallback_info(
            "not_a_contract", cache, dangling, artifact_store=store  # type: ignore[arg-type]
        )
        # Should fall through to dangling fallback
        assert is_fallback is True
        assert dangling[0] == 1

    def test_artifact_store_no_check_permission_falls_through(self) -> None:
        """Executable artifact without check_permission falls through."""
        store = ArtifactStore()
        store.write(
            artifact_id="bad_contract",
            type="contract",
            content="no check_permission",
            created_by="alice",
            code="def run(): return 'hello'",
            executable=True,
            access_contract_id="bad_contract",
        )
        cache: dict[str, object] = {}
        dangling: list[int] = [0]
        contract, is_fallback, orig_id = get_contract_with_fallback_info(
            "bad_contract", cache, dangling, artifact_store=store  # type: ignore[arg-type]
        )
        assert is_fallback is True
        assert dangling[0] == 1


class TestGenesisArtifactsStillWork:
    """Genesis artifacts use kernel contracts that still resolve for permission checks."""

    def test_genesis_kernel_contract_resolves(self) -> None:
        """Kernel contracts still resolve normally in permission checks."""
        cache: dict[str, object] = {}
        dangling: list[int] = [0]
        contract, is_fallback, orig_id = get_contract_with_fallback_info(
            "kernel_contract_freeware", cache, dangling  # type: ignore[arg-type]
        )
        assert contract is not None
        assert is_fallback is False
        assert dangling[0] == 0
