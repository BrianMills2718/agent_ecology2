"""Unit tests for genesis contracts.

Tests each of the four genesis contracts defined in src/world/genesis_contracts.py:
- FreewareContract: Open read/execute/invoke, owner-only write/delete/transfer
- SelfOwnedContract: Self or owner access only
- PrivateContract: Owner-only access
- PublicContract: Open access for all actions

Also tests the helper functions:
- get_genesis_contract()
- get_contract_by_id()
- list_genesis_contracts()
- GENESIS_CONTRACTS registry
"""

from __future__ import annotations

import pytest

from src.world.contracts import AccessContract, PermissionAction, PermissionResult
from src.world.genesis_contracts import (
    GENESIS_CONTRACTS,
    FreewareContract,
    PrivateContract,
    PublicContract,
    SelfOwnedContract,
    get_contract_by_id,
    get_genesis_contract,
    list_genesis_contracts,
)


class TestFreewareContract:
    """Tests for FreewareContract."""

    @pytest.fixture
    def contract(self) -> FreewareContract:
        """Create a freeware contract instance."""
        return FreewareContract()

    @pytest.fixture
    def context(self) -> dict[str, object]:
        """Create standard context with target_created_by."""
        return {"target_created_by": "owner_agent"}

    def test_contract_id(self, contract: FreewareContract) -> None:
        """Verify contract has correct ID."""
        assert contract.contract_id == "genesis_contract_freeware"

    def test_contract_type(self, contract: FreewareContract) -> None:
        """Verify contract has correct type."""
        assert contract.contract_type == "freeware"

    def test_implements_protocol(self, contract: FreewareContract) -> None:
        """Verify contract implements AccessContract protocol."""
        assert isinstance(contract, AccessContract)

    def test_read_anyone(
        self, contract: FreewareContract, context: dict[str, object]
    ) -> None:
        """Verify anyone can read freeware artifacts."""
        result = contract.check_permission(
            caller="any_agent",
            action=PermissionAction.READ,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is True
        assert "open access" in result.reason

    def test_execute_anyone(
        self, contract: FreewareContract, context: dict[str, object]
    ) -> None:
        """Verify anyone can execute freeware artifacts."""
        result = contract.check_permission(
            caller="any_agent",
            action=PermissionAction.EXECUTE,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is True

    def test_invoke_anyone(
        self, contract: FreewareContract, context: dict[str, object]
    ) -> None:
        """Verify anyone can invoke freeware artifacts."""
        result = contract.check_permission(
            caller="any_agent",
            action=PermissionAction.INVOKE,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is True

    def test_write_owner(
        self, contract: FreewareContract, context: dict[str, object]
    ) -> None:
        """Verify owner can write to freeware artifacts."""
        result = contract.check_permission(
            caller="owner_agent",
            action=PermissionAction.WRITE,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is True
        assert "owner access" in result.reason

    def test_write_other_denied(
        self, contract: FreewareContract, context: dict[str, object]
    ) -> None:
        """Verify non-owner cannot write to freeware artifacts."""
        result = contract.check_permission(
            caller="other_agent",
            action=PermissionAction.WRITE,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is False
        assert "only owner" in result.reason

    def test_delete_owner(
        self, contract: FreewareContract, context: dict[str, object]
    ) -> None:
        """Verify owner can delete freeware artifacts."""
        result = contract.check_permission(
            caller="owner_agent",
            action=PermissionAction.DELETE,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is True

    def test_delete_other_denied(
        self, contract: FreewareContract, context: dict[str, object]
    ) -> None:
        """Verify non-owner cannot delete freeware artifacts."""
        result = contract.check_permission(
            caller="other_agent",
            action=PermissionAction.DELETE,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is False

    def test_transfer_owner(
        self, contract: FreewareContract, context: dict[str, object]
    ) -> None:
        """Verify owner can transfer freeware artifacts."""
        result = contract.check_permission(
            caller="owner_agent",
            action=PermissionAction.TRANSFER,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is True

    def test_transfer_other_denied(
        self, contract: FreewareContract, context: dict[str, object]
    ) -> None:
        """Verify non-owner cannot transfer freeware artifacts."""
        result = contract.check_permission(
            caller="other_agent",
            action=PermissionAction.TRANSFER,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is False

    def test_no_context_owner_check(self, contract: FreewareContract) -> None:
        """Verify write fails gracefully without context."""
        result = contract.check_permission(
            caller="any_agent",
            action=PermissionAction.WRITE,
            target="artifact_1",
            context=None,
        )
        # Without context, owner is None, so caller != owner
        assert result.allowed is False


class TestSelfOwnedContract:
    """Tests for SelfOwnedContract."""

    @pytest.fixture
    def contract(self) -> SelfOwnedContract:
        """Create a self-owned contract instance."""
        return SelfOwnedContract()

    @pytest.fixture
    def context(self) -> dict[str, object]:
        """Create standard context with target_created_by."""
        return {"target_created_by": "owner_agent"}

    def test_contract_id(self, contract: SelfOwnedContract) -> None:
        """Verify contract has correct ID."""
        assert contract.contract_id == "genesis_contract_self_owned"

    def test_contract_type(self, contract: SelfOwnedContract) -> None:
        """Verify contract has correct type."""
        assert contract.contract_type == "self_owned"

    def test_implements_protocol(self, contract: SelfOwnedContract) -> None:
        """Verify contract implements AccessContract protocol."""
        assert isinstance(contract, AccessContract)

    def test_self_access_read(
        self, contract: SelfOwnedContract, context: dict[str, object]
    ) -> None:
        """Verify artifact can read itself."""
        result = contract.check_permission(
            caller="artifact_1",  # Same as target
            action=PermissionAction.READ,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is True
        assert "self access" in result.reason

    def test_self_access_write(
        self, contract: SelfOwnedContract, context: dict[str, object]
    ) -> None:
        """Verify artifact can write to itself."""
        result = contract.check_permission(
            caller="artifact_1",
            action=PermissionAction.WRITE,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is True

    def test_owner_access_read(
        self, contract: SelfOwnedContract, context: dict[str, object]
    ) -> None:
        """Verify owner can read the artifact."""
        result = contract.check_permission(
            caller="owner_agent",
            action=PermissionAction.READ,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is True
        assert "owner access" in result.reason

    def test_owner_access_all_actions(
        self, contract: SelfOwnedContract, context: dict[str, object]
    ) -> None:
        """Verify owner has access to all actions."""
        for action in PermissionAction:
            result = contract.check_permission(
                caller="owner_agent",
                action=action,
                target="artifact_1",
                context=context,
            )
            assert result.allowed is True, f"Owner should have {action} access"

    def test_other_denied_read(
        self, contract: SelfOwnedContract, context: dict[str, object]
    ) -> None:
        """Verify others cannot read the artifact."""
        result = contract.check_permission(
            caller="other_agent",
            action=PermissionAction.READ,
            target="artifact_1",
            context=context,
        )
        assert result.allowed is False
        assert "access denied" in result.reason

    def test_other_denied_all_actions(
        self, contract: SelfOwnedContract, context: dict[str, object]
    ) -> None:
        """Verify others cannot perform any action."""
        for action in PermissionAction:
            result = contract.check_permission(
                caller="other_agent",
                action=action,
                target="artifact_1",
                context=context,
            )
            assert result.allowed is False, f"Other should not have {action} access"


class TestPrivateContract:
    """Tests for PrivateContract."""

    @pytest.fixture
    def contract(self) -> PrivateContract:
        """Create a private contract instance."""
        return PrivateContract()

    @pytest.fixture
    def context(self) -> dict[str, object]:
        """Create standard context with target_created_by."""
        return {"target_created_by": "owner_agent"}

    def test_contract_id(self, contract: PrivateContract) -> None:
        """Verify contract has correct ID."""
        assert contract.contract_id == "genesis_contract_private"

    def test_contract_type(self, contract: PrivateContract) -> None:
        """Verify contract has correct type."""
        assert contract.contract_type == "private"

    def test_implements_protocol(self, contract: PrivateContract) -> None:
        """Verify contract implements AccessContract protocol."""
        assert isinstance(contract, AccessContract)

    def test_owner_access_all_actions(
        self, contract: PrivateContract, context: dict[str, object]
    ) -> None:
        """Verify owner has access to all actions."""
        for action in PermissionAction:
            result = contract.check_permission(
                caller="owner_agent",
                action=action,
                target="artifact_1",
                context=context,
            )
            assert result.allowed is True, f"Owner should have {action} access"
            assert "owner access" in result.reason

    def test_other_denied_all_actions(
        self, contract: PrivateContract, context: dict[str, object]
    ) -> None:
        """Verify others cannot perform any action."""
        for action in PermissionAction:
            result = contract.check_permission(
                caller="other_agent",
                action=action,
                target="artifact_1",
                context=context,
            )
            assert result.allowed is False
            assert "access denied" in result.reason

    def test_self_access_denied(
        self, contract: PrivateContract, context: dict[str, object]
    ) -> None:
        """Verify self-access is denied (unlike self_owned)."""
        result = contract.check_permission(
            caller="artifact_1",  # Same as target
            action=PermissionAction.READ,
            target="artifact_1",
            context=context,
        )
        # Private contract does NOT allow self-access
        assert result.allowed is False


class TestPublicContract:
    """Tests for PublicContract."""

    @pytest.fixture
    def contract(self) -> PublicContract:
        """Create a public contract instance."""
        return PublicContract()

    def test_contract_id(self, contract: PublicContract) -> None:
        """Verify contract has correct ID."""
        assert contract.contract_id == "genesis_contract_public"

    def test_contract_type(self, contract: PublicContract) -> None:
        """Verify contract has correct type."""
        assert contract.contract_type == "public"

    def test_implements_protocol(self, contract: PublicContract) -> None:
        """Verify contract implements AccessContract protocol."""
        assert isinstance(contract, AccessContract)

    def test_anyone_any_action(self, contract: PublicContract) -> None:
        """Verify anyone can perform any action."""
        for action in PermissionAction:
            result = contract.check_permission(
                caller="any_agent",
                action=action,
                target="artifact_1",
                context={"target_created_by": "someone_else"},
            )
            assert result.allowed is True, f"Public should allow {action}"
            assert "open access" in result.reason

    def test_no_context_still_allowed(self, contract: PublicContract) -> None:
        """Verify public works without context."""
        result = contract.check_permission(
            caller="any_agent",
            action=PermissionAction.DELETE,
            target="artifact_1",
            context=None,
        )
        assert result.allowed is True

    def test_dangerous_actions_allowed(self, contract: PublicContract) -> None:
        """Verify even dangerous actions are allowed (intentional)."""
        # Delete allowed
        delete_result = contract.check_permission(
            caller="random_agent",
            action=PermissionAction.DELETE,
            target="artifact_1",
        )
        assert delete_result.allowed is True

        # Transfer allowed
        transfer_result = contract.check_permission(
            caller="random_agent",
            action=PermissionAction.TRANSFER,
            target="artifact_1",
        )
        assert transfer_result.allowed is True


class TestGenesisContractsRegistry:
    """Tests for the GENESIS_CONTRACTS registry."""

    def test_registry_contains_all_contracts(self) -> None:
        """Verify registry contains all four genesis contracts."""
        expected_types = {"freeware", "self_owned", "private", "public"}
        assert set(GENESIS_CONTRACTS.keys()) == expected_types

    def test_registry_values_are_contracts(self) -> None:
        """Verify all registry values implement AccessContract."""
        for name, contract in GENESIS_CONTRACTS.items():
            assert isinstance(
                contract, AccessContract
            ), f"{name} should implement AccessContract"

    def test_registry_contracts_have_correct_types(self) -> None:
        """Verify registry contracts have matching types."""
        for name, contract in GENESIS_CONTRACTS.items():
            assert (
                contract.contract_type == name
            ), f"Contract type should match registry key"

    def test_registry_contracts_are_singletons(self) -> None:
        """Verify registry returns same instances."""
        contract1 = GENESIS_CONTRACTS["freeware"]
        contract2 = GENESIS_CONTRACTS["freeware"]
        assert contract1 is contract2


class TestGetGenesisContract:
    """Tests for get_genesis_contract() helper."""

    def test_get_freeware(self) -> None:
        """Verify can get freeware contract."""
        contract = get_genesis_contract("freeware")
        assert isinstance(contract, FreewareContract)
        assert contract.contract_type == "freeware"

    def test_get_self_owned(self) -> None:
        """Verify can get self_owned contract."""
        contract = get_genesis_contract("self_owned")
        assert isinstance(contract, SelfOwnedContract)

    def test_get_private(self) -> None:
        """Verify can get private contract."""
        contract = get_genesis_contract("private")
        assert isinstance(contract, PrivateContract)

    def test_get_public(self) -> None:
        """Verify can get public contract."""
        contract = get_genesis_contract("public")
        assert isinstance(contract, PublicContract)

    def test_invalid_type_raises(self) -> None:
        """Verify invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown genesis contract type"):
            get_genesis_contract("invalid")

    def test_error_message_shows_valid_types(self) -> None:
        """Verify error message lists valid types."""
        with pytest.raises(ValueError) as exc_info:
            get_genesis_contract("bad_type")
        error_msg = str(exc_info.value)
        assert "freeware" in error_msg
        assert "private" in error_msg


class TestGetContractById:
    """Tests for get_contract_by_id() helper."""

    def test_get_by_freeware_id(self) -> None:
        """Verify can get contract by freeware ID."""
        contract = get_contract_by_id("genesis_contract_freeware")
        assert contract is not None
        assert isinstance(contract, FreewareContract)

    def test_get_by_self_owned_id(self) -> None:
        """Verify can get contract by self_owned ID."""
        contract = get_contract_by_id("genesis_contract_self_owned")
        assert contract is not None
        assert isinstance(contract, SelfOwnedContract)

    def test_get_by_private_id(self) -> None:
        """Verify can get contract by private ID."""
        contract = get_contract_by_id("genesis_contract_private")
        assert contract is not None
        assert isinstance(contract, PrivateContract)

    def test_get_by_public_id(self) -> None:
        """Verify can get contract by public ID."""
        contract = get_contract_by_id("genesis_contract_public")
        assert contract is not None
        assert isinstance(contract, PublicContract)

    def test_invalid_id_returns_none(self) -> None:
        """Verify invalid ID returns None (not raises)."""
        result = get_contract_by_id("invalid_contract_id")
        assert result is None

    def test_partial_id_returns_none(self) -> None:
        """Verify partial match returns None."""
        result = get_contract_by_id("freeware")
        assert result is None


class TestListGenesisContracts:
    """Tests for list_genesis_contracts() helper."""

    def test_returns_all_types(self) -> None:
        """Verify returns all four types."""
        types = list_genesis_contracts()
        assert set(types) == {"freeware", "self_owned", "private", "public"}

    def test_returns_list(self) -> None:
        """Verify returns a list."""
        result = list_genesis_contracts()
        assert isinstance(result, list)

    def test_returns_strings(self) -> None:
        """Verify all items are strings."""
        types = list_genesis_contracts()
        assert all(isinstance(t, str) for t in types)


class TestContractComparison:
    """Tests comparing behavior across different contracts."""

    @pytest.fixture
    def all_contracts(self) -> dict[str, AccessContract]:
        """Get all genesis contracts."""
        return dict(GENESIS_CONTRACTS)

    @pytest.fixture
    def context(self) -> dict[str, object]:
        """Standard context with target_created_by."""
        return {"target_created_by": "owner_agent"}

    def test_owner_always_allowed_except_public(
        self, all_contracts: dict[str, AccessContract], context: dict[str, object]
    ) -> None:
        """Verify owner has write access on all contracts."""
        for name, contract in all_contracts.items():
            result = contract.check_permission(
                caller="owner_agent",
                action=PermissionAction.WRITE,
                target="artifact_1",
                context=context,
            )
            assert result.allowed is True, f"{name} should allow owner write"

    def test_stranger_read_behavior(
        self, all_contracts: dict[str, AccessContract], context: dict[str, object]
    ) -> None:
        """Compare stranger read access across contracts."""
        expected = {
            "freeware": True,  # Open read
            "self_owned": False,  # Only self/owner
            "private": False,  # Only owner
            "public": True,  # Open everything
        }

        for name, contract in all_contracts.items():
            result = contract.check_permission(
                caller="stranger",
                action=PermissionAction.READ,
                target="artifact_1",
                context=context,
            )
            assert (
                result.allowed == expected[name]
            ), f"{name} read access mismatch: expected {expected[name]}"

    def test_stranger_write_behavior(
        self, all_contracts: dict[str, AccessContract], context: dict[str, object]
    ) -> None:
        """Compare stranger write access across contracts."""
        expected = {
            "freeware": False,  # Owner only
            "self_owned": False,  # Self/owner only
            "private": False,  # Owner only
            "public": True,  # Open everything
        }

        for name, contract in all_contracts.items():
            result = contract.check_permission(
                caller="stranger",
                action=PermissionAction.WRITE,
                target="artifact_1",
                context=context,
            )
            assert (
                result.allowed == expected[name]
            ), f"{name} write access mismatch: expected {expected[name]}"

    def test_self_access_behavior(
        self, all_contracts: dict[str, AccessContract], context: dict[str, object]
    ) -> None:
        """Compare self-access (artifact accessing itself) across contracts."""
        expected = {
            "freeware": True,  # Open read (but not write)
            "self_owned": True,  # Self has full access
            "private": False,  # Only owner, not self
            "public": True,  # Open everything
        }

        for name, contract in all_contracts.items():
            result = contract.check_permission(
                caller="artifact_1",  # Same as target
                action=PermissionAction.READ,
                target="artifact_1",
                context=context,
            )
            assert (
                result.allowed == expected[name]
            ), f"{name} self-read access mismatch: expected {expected[name]}"

    def test_all_results_have_reasons(
        self, all_contracts: dict[str, AccessContract], context: dict[str, object]
    ) -> None:
        """Verify all contracts provide meaningful reasons."""
        for name, contract in all_contracts.items():
            result = contract.check_permission(
                caller="test_agent",
                action=PermissionAction.READ,
                target="artifact_1",
                context=context,
            )
            assert result.reason, f"{name} should provide a reason"
            assert len(result.reason) > 0

    def test_zero_cost_by_default(
        self, all_contracts: dict[str, AccessContract], context: dict[str, object]
    ) -> None:
        """Verify genesis contracts don't charge by default."""
        for name, contract in all_contracts.items():
            result = contract.check_permission(
                caller="owner_agent",
                action=PermissionAction.READ,
                target="artifact_1",
                context=context,
            )
            assert result.cost == 0, f"{name} should have zero cost by default"
