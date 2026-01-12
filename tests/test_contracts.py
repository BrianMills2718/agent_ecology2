"""Unit tests for the contract-based access control system.

Tests the core interfaces defined in src/world/contracts.py:
- PermissionAction enum
- PermissionResult dataclass
- AccessContract protocol

These tests verify the interfaces work correctly and that custom
implementations can be created that satisfy the protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from src.world.contracts import (
    AccessContract,
    PermissionAction,
    PermissionResult,
)


class TestPermissionAction:
    """Tests for the PermissionAction enum."""

    def test_all_actions_defined(self) -> None:
        """Verify all expected actions are defined."""
        expected_actions = {"read", "write", "execute", "invoke", "delete", "transfer"}
        actual_actions = {action.value for action in PermissionAction}
        assert actual_actions == expected_actions

    def test_action_string_values(self) -> None:
        """Verify actions have correct string values."""
        assert PermissionAction.READ.value == "read"
        assert PermissionAction.WRITE.value == "write"
        assert PermissionAction.EXECUTE.value == "execute"
        assert PermissionAction.INVOKE.value == "invoke"
        assert PermissionAction.DELETE.value == "delete"
        assert PermissionAction.TRANSFER.value == "transfer"

    def test_action_from_string(self) -> None:
        """Verify actions can be created from strings."""
        assert PermissionAction("read") == PermissionAction.READ
        assert PermissionAction("write") == PermissionAction.WRITE
        assert PermissionAction("invoke") == PermissionAction.INVOKE

    def test_action_invalid_string_raises(self) -> None:
        """Verify invalid action strings raise ValueError."""
        with pytest.raises(ValueError):
            PermissionAction("invalid_action")

    def test_action_is_str_enum(self) -> None:
        """Verify PermissionAction is both str and Enum."""
        action = PermissionAction.READ
        # Can be used as string in comparisons
        assert action == "read"
        # Value is the string
        assert action.value == "read"
        # Is instance of str (because str, Enum)
        assert isinstance(action, str)

    def test_action_in_collection(self) -> None:
        """Verify actions can be used in collections."""
        read_actions = {PermissionAction.READ, PermissionAction.EXECUTE}
        assert PermissionAction.READ in read_actions
        assert PermissionAction.WRITE not in read_actions


class TestPermissionResult:
    """Tests for the PermissionResult dataclass."""

    def test_basic_allowed_result(self) -> None:
        """Verify basic allowed result creation."""
        result = PermissionResult(allowed=True, reason="test: allowed")
        assert result.allowed is True
        assert result.reason == "test: allowed"
        assert result.cost == 0
        assert result.conditions is None

    def test_basic_denied_result(self) -> None:
        """Verify basic denied result creation."""
        result = PermissionResult(allowed=False, reason="test: denied")
        assert result.allowed is False
        assert result.reason == "test: denied"

    def test_result_with_cost(self) -> None:
        """Verify result with cost."""
        result = PermissionResult(allowed=True, reason="test: with cost", cost=50)
        assert result.allowed is True
        assert result.cost == 50

    def test_result_with_zero_cost(self) -> None:
        """Verify result with explicit zero cost."""
        result = PermissionResult(allowed=True, reason="test: free", cost=0)
        assert result.cost == 0

    def test_result_with_conditions(self) -> None:
        """Verify result with conditions dict."""
        conditions = {"max_reads": 10, "expires_tick": 100}
        result = PermissionResult(
            allowed=True,
            reason="test: conditional",
            conditions=conditions,
        )
        assert result.conditions == conditions
        assert result.conditions["max_reads"] == 10

    def test_result_negative_cost_raises(self) -> None:
        """Verify negative cost raises ValueError."""
        with pytest.raises(ValueError, match="cost cannot be negative"):
            PermissionResult(allowed=True, reason="test", cost=-1)

    def test_result_equality(self) -> None:
        """Verify result equality comparison."""
        result1 = PermissionResult(allowed=True, reason="same")
        result2 = PermissionResult(allowed=True, reason="same")
        result3 = PermissionResult(allowed=False, reason="same")

        assert result1 == result2
        assert result1 != result3

    def test_result_cost_equality(self) -> None:
        """Verify results with different costs are not equal."""
        result1 = PermissionResult(allowed=True, reason="test", cost=10)
        result2 = PermissionResult(allowed=True, reason="test", cost=20)
        assert result1 != result2

    def test_result_immutable_conditions(self) -> None:
        """Verify conditions dict is stored as provided."""
        conditions: dict[str, object] = {"key": "value"}
        result = PermissionResult(allowed=True, reason="test", conditions=conditions)
        # Modifying original should not affect result if we want immutability
        # Note: dataclass doesn't enforce immutability, so this just documents behavior
        assert result.conditions is conditions


class TestAccessContractProtocol:
    """Tests for the AccessContract protocol."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Verify AccessContract can be used with isinstance()."""
        # Create a minimal implementation
        @dataclass
        class MinimalContract:
            contract_id: str = "test_contract"
            contract_type: str = "test"

            def check_permission(
                self,
                caller: str,
                action: PermissionAction,
                target: str,
                context: Optional[dict[str, object]] = None,
            ) -> PermissionResult:
                return PermissionResult(allowed=True, reason="test")

        contract = MinimalContract()
        assert isinstance(contract, AccessContract)

    def test_non_contract_fails_isinstance(self) -> None:
        """Verify non-implementing classes fail isinstance check."""

        class NotAContract:
            pass

        obj = NotAContract()
        assert not isinstance(obj, AccessContract)

    def test_partial_implementation_fails(self) -> None:
        """Verify partial implementations fail isinstance check."""

        @dataclass
        class PartialContract:
            contract_id: str = "partial"
            # Missing contract_type and check_permission

        obj = PartialContract()
        assert not isinstance(obj, AccessContract)

    def test_custom_contract_implementation(self) -> None:
        """Verify custom contract can be created and used."""

        @dataclass
        class CustomContract:
            """A custom contract that allows only specific users."""

            contract_id: str = "custom_whitelist"
            contract_type: str = "custom"
            allowed_users: tuple[str, ...] = ("alice", "bob")

            def check_permission(
                self,
                caller: str,
                action: PermissionAction,
                target: str,
                context: Optional[dict[str, object]] = None,
            ) -> PermissionResult:
                if caller in self.allowed_users:
                    return PermissionResult(allowed=True, reason="user in whitelist")
                return PermissionResult(allowed=False, reason="user not in whitelist")

        contract = CustomContract()
        assert isinstance(contract, AccessContract)

        # Test the custom logic
        result_alice = contract.check_permission(
            "alice", PermissionAction.READ, "artifact_1"
        )
        assert result_alice.allowed is True

        result_charlie = contract.check_permission(
            "charlie", PermissionAction.READ, "artifact_1"
        )
        assert result_charlie.allowed is False

    def test_contract_with_context_usage(self) -> None:
        """Verify contracts can use context dict."""

        @dataclass
        class ContextAwareContract:
            contract_id: str = "context_aware"
            contract_type: str = "custom"

            def check_permission(
                self,
                caller: str,
                action: PermissionAction,
                target: str,
                context: Optional[dict[str, object]] = None,
            ) -> PermissionResult:
                if context is None:
                    return PermissionResult(allowed=False, reason="context required")

                owner = context.get("owner")
                if caller == owner:
                    return PermissionResult(allowed=True, reason="caller is owner")
                return PermissionResult(allowed=False, reason="caller is not owner")

        contract = ContextAwareContract()

        # Without context
        result_no_ctx = contract.check_permission(
            "alice", PermissionAction.WRITE, "artifact_1"
        )
        assert result_no_ctx.allowed is False
        assert "context required" in result_no_ctx.reason

        # With context - owner
        result_owner = contract.check_permission(
            "alice",
            PermissionAction.WRITE,
            "artifact_1",
            context={"owner": "alice"},
        )
        assert result_owner.allowed is True

        # With context - not owner
        result_other = contract.check_permission(
            "bob",
            PermissionAction.WRITE,
            "artifact_1",
            context={"owner": "alice"},
        )
        assert result_other.allowed is False

    def test_contract_with_cost(self) -> None:
        """Verify contracts can return costs."""

        @dataclass
        class PaidAccessContract:
            contract_id: str = "paid_access"
            contract_type: str = "custom"
            read_cost: int = 10
            write_cost: int = 50

            def check_permission(
                self,
                caller: str,
                action: PermissionAction,
                target: str,
                context: Optional[dict[str, object]] = None,
            ) -> PermissionResult:
                if action == PermissionAction.READ:
                    return PermissionResult(
                        allowed=True, reason="read allowed", cost=self.read_cost
                    )
                if action == PermissionAction.WRITE:
                    return PermissionResult(
                        allowed=True, reason="write allowed", cost=self.write_cost
                    )
                return PermissionResult(allowed=False, reason="action not supported")

        contract = PaidAccessContract()

        read_result = contract.check_permission(
            "user", PermissionAction.READ, "artifact"
        )
        assert read_result.allowed is True
        assert read_result.cost == 10

        write_result = contract.check_permission(
            "user", PermissionAction.WRITE, "artifact"
        )
        assert write_result.allowed is True
        assert write_result.cost == 50


class TestPermissionActionUsagePatterns:
    """Tests for common usage patterns with PermissionAction."""

    def test_action_grouping(self) -> None:
        """Verify common action groupings work as expected."""
        read_only_actions = (
            PermissionAction.READ,
            PermissionAction.EXECUTE,
            PermissionAction.INVOKE,
        )
        modify_actions = (
            PermissionAction.WRITE,
            PermissionAction.DELETE,
            PermissionAction.TRANSFER,
        )

        # Verify no overlap
        assert set(read_only_actions).isdisjoint(set(modify_actions))

        # Verify complete coverage
        all_actions = set(read_only_actions) | set(modify_actions)
        assert all_actions == set(PermissionAction)

    def test_action_iteration(self) -> None:
        """Verify PermissionAction can be iterated."""
        actions = list(PermissionAction)
        assert len(actions) == 6
        assert PermissionAction.READ in actions

    def test_action_membership_check(self) -> None:
        """Verify membership checks work with different types."""
        action = PermissionAction.READ

        # Check against enum values
        assert action in [PermissionAction.READ, PermissionAction.WRITE]

        # Check against strings (works because str enum)
        assert action == "read"


class TestPermissionResultUsagePatterns:
    """Tests for common usage patterns with PermissionResult."""

    def test_result_as_boolean(self) -> None:
        """Verify result.allowed can be used in boolean context."""
        allowed_result = PermissionResult(allowed=True, reason="ok")
        denied_result = PermissionResult(allowed=False, reason="no")

        # Direct use in conditionals
        if allowed_result.allowed:
            passed = True
        else:
            passed = False
        assert passed is True

        if denied_result.allowed:
            passed = True
        else:
            passed = False
        assert passed is False

    def test_result_chaining(self) -> None:
        """Verify results can be used in chained checks."""

        def check_all_permissions(
            contract: AccessContract,
            caller: str,
            actions: list[PermissionAction],
            target: str,
        ) -> bool:
            """Check if caller has all specified permissions."""
            for action in actions:
                result = contract.check_permission(caller, action, target)
                if not result.allowed:
                    return False
            return True

        @dataclass
        class SimpleContract:
            contract_id: str = "simple"
            contract_type: str = "test"

            def check_permission(
                self,
                caller: str,
                action: PermissionAction,
                target: str,
                context: Optional[dict[str, object]] = None,
            ) -> PermissionResult:
                # Only allow read and invoke
                if action in (PermissionAction.READ, PermissionAction.INVOKE):
                    return PermissionResult(allowed=True, reason="allowed")
                return PermissionResult(allowed=False, reason="denied")

        contract = SimpleContract()

        # Should pass - both allowed
        assert check_all_permissions(
            contract,
            "user",
            [PermissionAction.READ, PermissionAction.INVOKE],
            "artifact",
        )

        # Should fail - write not allowed
        assert not check_all_permissions(
            contract,
            "user",
            [PermissionAction.READ, PermissionAction.WRITE],
            "artifact",
        )
