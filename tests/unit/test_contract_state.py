"""Unit tests for contract state management (Plan #311).

Tests the state_updates flow:
1. Artifact.state is populated at creation time (writer/principal)
2. Contracts receive state via context["_artifact_state"]
3. Contracts can return state_updates in PermissionResult
4. Kernel applies state_updates to artifact.state after permission check
"""

from __future__ import annotations

import pytest

from src.world.artifacts import Artifact, ArtifactStore
from src.world.constants import (
    KERNEL_CONTRACT_FREEWARE,
    KERNEL_CONTRACT_SELF_OWNED,
    KERNEL_CONTRACT_PRIVATE,
    KERNEL_CONTRACT_TRANSFERABLE_FREEWARE,
)
from src.world.contracts import (
    ExecutableContract,
    PermissionAction,
    PermissionResult,
)
from src.world.permission_checker import check_permission_via_contract


class TestArtifactStatePopulation:
    """Test that artifact.state is auto-populated at creation time."""

    def test_freeware_gets_writer(self) -> None:
        """Freeware artifacts get state["writer"] = created_by."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="doc_1",
            type="generic",
            content="hello",
            created_by="alice",
            access_contract_id=KERNEL_CONTRACT_FREEWARE,
        )
        assert artifact.state["writer"] == "alice"

    def test_transferable_freeware_gets_writer(self) -> None:
        """Transferable freeware artifacts get state["writer"] = created_by."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="doc_2",
            type="generic",
            content="hello",
            created_by="bob",
            access_contract_id=KERNEL_CONTRACT_TRANSFERABLE_FREEWARE,
        )
        assert artifact.state["writer"] == "bob"

    def test_self_owned_gets_principal(self) -> None:
        """Self-owned artifacts get state["principal"] = created_by."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="mem_1",
            type="memory",
            content="private data",
            created_by="alice",
            access_contract_id=KERNEL_CONTRACT_SELF_OWNED,
        )
        assert artifact.state["principal"] == "alice"

    def test_private_gets_principal(self) -> None:
        """Private artifacts get state["principal"] = created_by."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="secret_1",
            type="generic",
            content="secret",
            created_by="charlie",
            access_contract_id=KERNEL_CONTRACT_PRIVATE,
        )
        assert artifact.state["principal"] == "charlie"

    def test_explicit_state_not_overwritten(self) -> None:
        """If state is provided explicitly, auto-population doesn't overwrite."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="doc_3",
            type="generic",
            content="hello",
            created_by="alice",
            access_contract_id=KERNEL_CONTRACT_FREEWARE,
            state={"writer": "bob"},
        )
        assert artifact.state["writer"] == "bob"

    def test_state_in_to_dict(self) -> None:
        """Artifact.to_dict() includes state when non-empty."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="doc_4",
            type="generic",
            content="hello",
            created_by="alice",
            access_contract_id=KERNEL_CONTRACT_FREEWARE,
        )
        d = artifact.to_dict()
        assert d["state"] == {"writer": "alice"}

    def test_empty_state_not_in_to_dict(self) -> None:
        """Artifact.to_dict() omits state when empty."""
        artifact = Artifact(
            id="test",
            type="generic",
            content="",
            created_by="x",
            created_at="",
            updated_at="",
            state={},
        )
        d = artifact.to_dict()
        assert "state" not in d


class TestStateInjectionIntoContext:
    """Test that contracts receive _artifact_state in context."""

    def test_freeware_reads_writer_from_state(self) -> None:
        """FreewareContract uses _artifact_state['writer'] for authorization."""
        from src.world.kernel_contracts import FreewareContract
        contract = FreewareContract()
        context: dict[str, object] = {
            "_artifact_state": {"writer": "alice"},
        }
        # Writer can write
        result = contract.check_permission(
            caller="alice",
            action=PermissionAction.WRITE,
            target="doc_1",
            context=context,
        )
        assert result.allowed is True

        # Non-writer cannot write
        result = contract.check_permission(
            caller="bob",
            action=PermissionAction.WRITE,
            target="doc_1",
            context=context,
        )
        assert result.allowed is False

    def test_self_owned_reads_principal_from_state(self) -> None:
        """SelfOwnedContract uses _artifact_state['principal'] for authorization."""
        from src.world.kernel_contracts import SelfOwnedContract
        contract = SelfOwnedContract()
        context: dict[str, object] = {
            "_artifact_state": {"principal": "alice"},
        }
        # Principal can access
        result = contract.check_permission(
            caller="alice",
            action=PermissionAction.READ,
            target="mem_1",
            context=context,
        )
        assert result.allowed is True

        # Non-principal cannot access
        result = contract.check_permission(
            caller="bob",
            action=PermissionAction.READ,
            target="mem_1",
            context=context,
        )
        assert result.allowed is False


class TestStateUpdatesApplication:
    """Test that state_updates from PermissionResult are applied to artifact.state."""

    def _make_artifact_and_store(self) -> tuple[Artifact, ArtifactStore]:
        """Create a test artifact in a store."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="tradeable_1",
            type="generic",
            content="valuable thing",
            created_by="alice",
            access_contract_id=KERNEL_CONTRACT_FREEWARE,
        )
        return artifact, store

    def test_state_updates_applied(self) -> None:
        """When a contract returns state_updates, they are merged into artifact.state."""
        artifact, store = self._make_artifact_and_store()
        assert artifact.state["writer"] == "alice"

        # Create an executable contract that transfers writer on invoke
        class TransferContract:
            contract_id = "test_transfer_contract"
            contract_type = "test"
            cache_policy = None

            def check_permission(
                self, caller: str, action: PermissionAction, target: str,
                context: dict[str, object] | None = None,
                ledger: object = None,
            ) -> PermissionResult:
                return PermissionResult(
                    allowed=True,
                    reason="transfer: allowed",
                    state_updates={"writer": "bob"},
                )

        contract_cache: dict[str, object] = {
            KERNEL_CONTRACT_FREEWARE: TransferContract(),
        }

        from src.world.contracts import PermissionCache
        perm_cache = PermissionCache()

        dangling_tracker = [0]
        result = check_permission_via_contract(
            caller="alice",
            action="write",
            artifact=artifact,
            contract_cache=contract_cache,  # type: ignore[arg-type]
            permission_cache=perm_cache,
            dangling_count_tracker=dangling_tracker,
            ledger=None,
            max_contract_depth=10,
            artifact_store=store,
        )

        assert result.allowed is True
        # state_updates should have been applied
        assert artifact.state["writer"] == "bob"
        # Verify via store lookup too
        stored = store.get("tradeable_1")
        assert stored is not None
        assert stored.state["writer"] == "bob"

    def test_state_updates_not_applied_without_store(self) -> None:
        """When artifact_store is None, state_updates are silently skipped."""
        artifact, store = self._make_artifact_and_store()
        assert artifact.state["writer"] == "alice"

        class UpdatingContract:
            contract_id = "test_updating_contract"
            contract_type = "test"
            cache_policy = None

            def check_permission(
                self, caller: str, action: PermissionAction, target: str,
                context: dict[str, object] | None = None,
                ledger: object = None,
            ) -> PermissionResult:
                return PermissionResult(
                    allowed=True,
                    reason="test: allowed",
                    state_updates={"writer": "charlie"},
                )

        contract_cache: dict[str, object] = {
            KERNEL_CONTRACT_FREEWARE: UpdatingContract(),
        }

        from src.world.contracts import PermissionCache
        perm_cache = PermissionCache()

        dangling_tracker = [0]
        result = check_permission_via_contract(
            caller="alice",
            action="write",
            artifact=artifact,
            contract_cache=contract_cache,  # type: ignore[arg-type]
            permission_cache=perm_cache,
            dangling_count_tracker=dangling_tracker,
            ledger=None,
            max_contract_depth=10,
            artifact_store=None,  # No store
        )

        assert result.allowed is True
        # state should NOT have changed (no store to apply to)
        assert artifact.state["writer"] == "alice"

    def test_state_updates_none_is_noop(self) -> None:
        """When state_updates is None, artifact.state is unchanged."""
        artifact, store = self._make_artifact_and_store()
        assert artifact.state["writer"] == "alice"

        from src.world.kernel_contracts import FreewareContract
        contract_cache: dict[str, object] = {
            KERNEL_CONTRACT_FREEWARE: FreewareContract(),
        }

        from src.world.contracts import PermissionCache
        perm_cache = PermissionCache()

        dangling_tracker = [0]
        result = check_permission_via_contract(
            caller="alice",
            action="write",
            artifact=artifact,
            contract_cache=contract_cache,  # type: ignore[arg-type]
            permission_cache=perm_cache,
            dangling_count_tracker=dangling_tracker,
            ledger=None,
            max_contract_depth=10,
            artifact_store=store,
        )

        assert result.allowed is True
        # state unchanged — kernel contracts don't return state_updates
        assert artifact.state["writer"] == "alice"

    def test_state_updates_merge_not_replace(self) -> None:
        """state_updates are merged (dict.update), not replaced entirely."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="multi_state",
            type="generic",
            content="test",
            created_by="alice",
            access_contract_id=KERNEL_CONTRACT_FREEWARE,
            state={"writer": "alice", "custom_field": "keep_me"},
        )

        class MergingContract:
            contract_id = "test_merging"
            contract_type = "test"
            cache_policy = None

            def check_permission(
                self, caller: str, action: PermissionAction, target: str,
                context: dict[str, object] | None = None,
                ledger: object = None,
            ) -> PermissionResult:
                return PermissionResult(
                    allowed=True,
                    reason="merge test",
                    state_updates={"writer": "bob", "new_field": "added"},
                )

        contract_cache: dict[str, object] = {
            KERNEL_CONTRACT_FREEWARE: MergingContract(),
        }

        from src.world.contracts import PermissionCache
        perm_cache = PermissionCache()

        dangling_tracker = [0]
        check_permission_via_contract(
            caller="alice",
            action="write",
            artifact=artifact,
            contract_cache=contract_cache,  # type: ignore[arg-type]
            permission_cache=perm_cache,
            dangling_count_tracker=dangling_tracker,
            ledger=None,
            max_contract_depth=10,
            artifact_store=store,
        )

        # writer updated, custom_field preserved, new_field added
        assert artifact.state["writer"] == "bob"
        assert artifact.state["custom_field"] == "keep_me"
        assert artifact.state["new_field"] == "added"


class TestNoKernelOwnerBypass:
    """Verify contracts don't use created_by for authorization (ADR-0028).

    This is a regression guard: if created_by differs from the state field,
    the contract must use the state field, not created_by.
    """

    def test_freeware_uses_state_not_created_by(self) -> None:
        """Freeware checks state['writer'], not created_by."""
        from src.world.kernel_contracts import FreewareContract
        contract = FreewareContract()

        # created_by is alice, but state says bob is writer
        context: dict[str, object] = {
            "target_created_by": "alice",
            "_artifact_state": {"writer": "bob"},
        }

        # alice (creator) cannot write — she's not the writer
        result = contract.check_permission(
            caller="alice",
            action=PermissionAction.WRITE,
            target="doc_1",
            context=context,
        )
        assert result.allowed is False

        # bob (state writer) can write
        result = contract.check_permission(
            caller="bob",
            action=PermissionAction.WRITE,
            target="doc_1",
            context=context,
        )
        assert result.allowed is True

    def test_self_owned_uses_state_not_created_by(self) -> None:
        """SelfOwned checks state['principal'], not created_by."""
        from src.world.kernel_contracts import SelfOwnedContract
        contract = SelfOwnedContract()

        # created_by is alice, but state says bob is principal
        context: dict[str, object] = {
            "target_created_by": "alice",
            "_artifact_state": {"principal": "bob"},
        }

        # alice (creator) cannot access
        result = contract.check_permission(
            caller="alice",
            action=PermissionAction.READ,
            target="mem_1",
            context=context,
        )
        assert result.allowed is False

        # bob (state principal) can access
        result = contract.check_permission(
            caller="bob",
            action=PermissionAction.READ,
            target="mem_1",
            context=context,
        )
        assert result.allowed is True
