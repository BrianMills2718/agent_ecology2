"""Unit tests for the contract-based access control system.

Tests the core interfaces defined in src/world/contracts.py:
- PermissionAction enum
- PermissionResult dataclass
- AccessContract protocol
- ExecutableContract with dynamic code execution
- ReadOnlyLedger wrapper for sandbox safety

These tests verify the interfaces work correctly and that custom
implementations can be created that satisfy the protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from src.world.contracts import (
    AccessContract,
    ContractExecutionError,
    ContractTimeoutError,
    ExecutableContract,
    PermissionAction,
    PermissionResult,
    ReadOnlyLedger,
)
from src.world.ledger import Ledger


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


class TestReadOnlyLedger:
    """Tests for the ReadOnlyLedger wrapper."""

    def test_get_scrip(self) -> None:
        """Verify get_scrip returns correct balance."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100)

        readonly = ReadOnlyLedger(ledger)
        assert readonly.get_scrip("alice") == 100
        assert readonly.get_scrip("nonexistent") == 0

    def test_can_afford_scrip(self) -> None:
        """Verify can_afford_scrip checks correctly."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100)

        readonly = ReadOnlyLedger(ledger)
        assert readonly.can_afford_scrip("alice", 50) is True
        assert readonly.can_afford_scrip("alice", 100) is True
        assert readonly.can_afford_scrip("alice", 150) is False

    def test_get_resource(self) -> None:
        """Verify get_resource returns correct balance."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=0, starting_resources={"compute": 500.0})

        readonly = ReadOnlyLedger(ledger)
        assert readonly.get_resource("alice", "compute") == 500.0
        assert readonly.get_resource("alice", "nonexistent") == 0.0

    def test_can_spend_resource(self) -> None:
        """Verify can_spend_resource checks correctly."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=0, starting_resources={"compute": 500.0})

        readonly = ReadOnlyLedger(ledger)
        assert readonly.can_spend_resource("alice", "compute", 250.0) is True
        assert readonly.can_spend_resource("alice", "compute", 600.0) is False

    def test_get_all_resources(self) -> None:
        """Verify get_all_resources returns all resources."""
        ledger = Ledger()
        ledger.create_principal(
            "alice",
            starting_scrip=0,
            starting_resources={"compute": 500.0, "disk": 1000.0}
        )

        readonly = ReadOnlyLedger(ledger)
        resources = readonly.get_all_resources("alice")
        assert resources == {"compute": 500.0, "disk": 1000.0}

    def test_principal_exists(self) -> None:
        """Verify principal_exists checks correctly."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100)

        readonly = ReadOnlyLedger(ledger)
        assert readonly.principal_exists("alice") is True
        assert readonly.principal_exists("bob") is False

    def test_no_write_methods(self) -> None:
        """Verify ReadOnlyLedger has no write methods."""
        ledger = Ledger()
        readonly = ReadOnlyLedger(ledger)

        # These methods should not exist on ReadOnlyLedger
        assert not hasattr(readonly, "deduct_scrip")
        assert not hasattr(readonly, "credit_scrip")
        assert not hasattr(readonly, "transfer_scrip")
        assert not hasattr(readonly, "spend_resource")
        assert not hasattr(readonly, "credit_resource")


class TestExecutableContract:
    """Tests for ExecutableContract with dynamic code."""

    def test_basic_allow_all(self) -> None:
        """Test a simple contract that allows everything."""
        contract = ExecutableContract(
            contract_id="allow_all",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "All access allowed", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )

        assert result.allowed is True
        assert result.reason == "All access allowed"
        assert result.cost == 0

    def test_basic_deny_all(self) -> None:
        """Test a simple contract that denies everything."""
        contract = ExecutableContract(
            contract_id="deny_all",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": False, "reason": "No access allowed", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )

        assert result.allowed is False
        assert result.reason == "No access allowed"

    def test_owner_only_access(self) -> None:
        """Test a contract that allows only owner access."""
        contract = ExecutableContract(
            contract_id="owner_only",
            code='''
def check_permission(caller, action, target, context, ledger):
    owner = context.get("owner")
    if caller == owner:
        return {"allowed": True, "reason": "Owner access", "cost": 0}
    return {"allowed": False, "reason": "Only owner can access", "cost": 0}
'''
        )

        # Owner access
        result = contract.check_permission(
            caller="alice",
            action=PermissionAction.READ,
            target="artifact_1",
            context={"owner": "alice"},
        )
        assert result.allowed is True

        # Non-owner access
        result = contract.check_permission(
            caller="bob",
            action=PermissionAction.READ,
            target="artifact_1",
            context={"owner": "alice"},
        )
        assert result.allowed is False

    def test_action_based_access(self) -> None:
        """Test a contract with different rules per action."""
        contract = ExecutableContract(
            contract_id="action_based",
            code='''
def check_permission(caller, action, target, context, ledger):
    if action in ("read", "execute", "invoke"):
        return {"allowed": True, "reason": "Read access allowed", "cost": 0}
    return {"allowed": False, "reason": "Write access denied", "cost": 0}
'''
        )

        # Read should be allowed
        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is True

        # Write should be denied
        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.WRITE,
            target="artifact_1",
        )
        assert result.allowed is False

    def test_pay_per_use_with_ledger(self) -> None:
        """Test a pay-per-use contract that checks ledger balance."""
        ledger = Ledger()
        ledger.create_principal("rich_user", starting_scrip=100)
        ledger.create_principal("poor_user", starting_scrip=5)

        contract = ExecutableContract(
            contract_id="pay_per_use",
            code='''
def check_permission(caller, action, target, context, ledger):
    price = 10
    if ledger is None:
        return {"allowed": False, "reason": "Ledger required", "cost": 0}
    if not ledger.can_afford_scrip(caller, price):
        return {"allowed": False, "reason": "Insufficient scrip", "cost": 0}
    return {"allowed": True, "reason": "Paid access", "cost": price}
'''
        )

        # Rich user can afford
        result = contract.check_permission(
            caller="rich_user",
            action=PermissionAction.INVOKE,
            target="service_1",
            ledger=ledger,
        )
        assert result.allowed is True
        assert result.cost == 10

        # Poor user cannot afford
        result = contract.check_permission(
            caller="poor_user",
            action=PermissionAction.INVOKE,
            target="service_1",
            ledger=ledger,
        )
        assert result.allowed is False
        assert "Insufficient" in result.reason

    def test_time_based_access(self) -> None:
        """Test a contract using time module."""
        contract = ExecutableContract(
            contract_id="time_based",
            code='''
def check_permission(caller, action, target, context, ledger):
    # time module is pre-loaded in CONTRACT_ALLOWED_MODULES
    current_time = time.time()
    if current_time > 0:
        return {"allowed": True, "reason": "Time check passed", "cost": 0}
    return {"allowed": False, "reason": "Time check failed", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is True
        assert "Time check passed" in result.reason

    def test_math_module_available(self) -> None:
        """Test that math module is available in contract code."""
        contract = ExecutableContract(
            contract_id="math_user",
            code='''
def check_permission(caller, action, target, context, ledger):
    # Use math module
    value = math.sqrt(16)
    return {"allowed": value == 4.0, "reason": f"sqrt(16) = {value}", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is True

    def test_json_module_available(self) -> None:
        """Test that json module is available in contract code."""
        contract = ExecutableContract(
            contract_id="json_user",
            code='''
def check_permission(caller, action, target, context, ledger):
    data = json.dumps({"key": "value"})
    parsed = json.loads(data)
    return {"allowed": parsed["key"] == "value", "reason": "JSON works", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is True

    def test_random_module_available(self) -> None:
        """Test that random module is available in contract code."""
        contract = ExecutableContract(
            contract_id="random_user",
            code='''
def check_permission(caller, action, target, context, ledger):
    random.seed(42)
    value = random.randint(1, 100)
    return {"allowed": 1 <= value <= 100, "reason": f"Random: {value}", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is True

    def test_empty_code_fails(self) -> None:
        """Test that empty code fails validation."""
        contract = ExecutableContract(
            contract_id="empty",
            code=""
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is False
        assert "Empty" in result.reason or "Invalid" in result.reason

    def test_missing_check_permission_fails(self) -> None:
        """Test that code without check_permission fails."""
        contract = ExecutableContract(
            contract_id="no_check",
            code='''
def some_other_function():
    return True
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is False
        assert "check_permission" in result.reason

    def test_syntax_error_fails(self) -> None:
        """Test that syntax errors are caught."""
        contract = ExecutableContract(
            contract_id="syntax_error",
            code='''
def check_permission(caller, action, target, context, ledger
    return {"allowed": True}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is False
        assert "Syntax" in result.reason or "syntax" in result.reason

    def test_runtime_error_caught(self) -> None:
        """Test that runtime errors are caught gracefully."""
        contract = ExecutableContract(
            contract_id="runtime_error",
            code='''
def check_permission(caller, action, target, context, ledger):
    x = 1 / 0  # Division by zero
    return {"allowed": True, "reason": "ok", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is False
        assert "ZeroDivision" in result.reason or "error" in result.reason.lower()

    def test_invalid_return_type_handled(self) -> None:
        """Test that invalid return types are handled."""
        contract = ExecutableContract(
            contract_id="bad_return",
            code='''
def check_permission(caller, action, target, context, ledger):
    return "not a dict"
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is False
        assert "invalid" in result.reason.lower() or "type" in result.reason.lower()

    def test_invalid_allowed_type_handled(self) -> None:
        """Test that invalid allowed type is handled."""
        contract = ExecutableContract(
            contract_id="bad_allowed",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": "yes", "reason": "test", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is False
        assert "bool" in result.reason.lower()

    def test_cost_conversion(self) -> None:
        """Test that cost is properly converted to int."""
        contract = ExecutableContract(
            contract_id="float_cost",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "test", "cost": 10.5}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is True
        assert result.cost == 10
        assert isinstance(result.cost, int)

    def test_negative_cost_becomes_zero(self) -> None:
        """Test that negative cost becomes zero."""
        contract = ExecutableContract(
            contract_id="negative_cost",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "test", "cost": -5}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is True
        assert result.cost == 0

    def test_dangerous_builtins_removed(self) -> None:
        """Test that dangerous builtins are not available."""
        # Test open
        contract = ExecutableContract(
            contract_id="try_open",
            code='''
def check_permission(caller, action, target, context, ledger):
    try:
        f = open("/etc/passwd")
        return {"allowed": True, "reason": "opened file", "cost": 0}
    except NameError:
        return {"allowed": False, "reason": "open not available", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        # open should not be available
        assert result.allowed is False
        assert "open not available" in result.reason

    def test_eval_not_available(self) -> None:
        """Test that eval is not available in contract code."""
        contract = ExecutableContract(
            contract_id="try_eval",
            code='''
def check_permission(caller, action, target, context, ledger):
    try:
        result = eval("1 + 1")
        return {"allowed": True, "reason": "eval works", "cost": 0}
    except NameError:
        return {"allowed": False, "reason": "eval not available", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is False
        assert "eval not available" in result.reason

    def test_exec_not_available(self) -> None:
        """Test that exec is not available in contract code."""
        contract = ExecutableContract(
            contract_id="try_exec",
            code='''
def check_permission(caller, action, target, context, ledger):
    try:
        exec("x = 1")
        return {"allowed": True, "reason": "exec works", "cost": 0}
    except NameError:
        return {"allowed": False, "reason": "exec not available", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is False
        assert "exec not available" in result.reason

    def test_import_not_available(self) -> None:
        """Test that __import__ is not available in contract code."""
        contract = ExecutableContract(
            contract_id="try_import",
            code='''
def check_permission(caller, action, target, context, ledger):
    try:
        os = __import__("os")
        return {"allowed": True, "reason": "import works", "cost": 0}
    except NameError:
        return {"allowed": False, "reason": "import not available", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )
        assert result.allowed is False
        assert "import not available" in result.reason

    def test_context_passed_correctly(self) -> None:
        """Test that context is passed correctly to contract code."""
        contract = ExecutableContract(
            contract_id="context_check",
            code='''
def check_permission(caller, action, target, context, ledger):
    owner = context.get("owner", "unknown")
    artifact_type = context.get("artifact_type", "unknown")
    tick = context.get("tick", -1)
    return {
        "allowed": True,
        "reason": f"owner={owner}, type={artifact_type}, tick={tick}",
        "cost": 0
    }
'''
        )

        result = contract.check_permission(
            caller="alice",
            action=PermissionAction.READ,
            target="artifact_1",
            context={"owner": "bob", "artifact_type": "code", "tick": 42},
        )
        assert result.allowed is True
        assert "owner=bob" in result.reason
        assert "type=code" in result.reason
        assert "tick=42" in result.reason

    def test_contract_type_is_executable(self) -> None:
        """Test that contract_type is 'executable'."""
        contract = ExecutableContract(
            contract_id="test",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "ok", "cost": 0}
'''
        )

        assert contract.contract_type == "executable"

    def test_contract_id_stored(self) -> None:
        """Test that contract_id is stored correctly."""
        contract = ExecutableContract(
            contract_id="my_custom_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "ok", "cost": 0}
'''
        )

        assert contract.contract_id == "my_custom_contract"

    def test_ledger_none_handled(self) -> None:
        """Test that None ledger is handled gracefully."""
        contract = ExecutableContract(
            contract_id="ledger_check",
            code='''
def check_permission(caller, action, target, context, ledger):
    if ledger is None:
        return {"allowed": True, "reason": "No ledger, free access", "cost": 0}
    return {"allowed": True, "reason": "Ledger present", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
            ledger=None,
        )
        assert result.allowed is True
        assert "No ledger" in result.reason


class TestExecutableContractWithExecutor:
    """Tests for ExecutableContract integration with SafeExecutor."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        from src.world.executor import SafeExecutor
        from src.world.artifacts import Artifact
        from datetime import datetime

        self.ledger = Ledger()
        self.ledger.create_principal("rich_user", starting_scrip=100)
        self.ledger.create_principal("poor_user", starting_scrip=5)
        self.ledger.create_principal("owner", starting_scrip=50)

        self.executor = SafeExecutor(timeout=5, use_contracts=True, ledger=self.ledger)

        # Create test artifact
        self.artifact = Artifact(
            id="test_artifact",
            type="test",
            content="test content",
            owner_id="owner",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

    def test_register_executable_contract(self) -> None:
        """Test registering an executable contract with executor."""
        contract = ExecutableContract(
            contract_id="custom_pay_per_use",
            code='''
def check_permission(caller, action, target, context, ledger):
    price = 10
    if ledger and not ledger.can_afford_scrip(caller, price):
        return {"allowed": False, "reason": "Insufficient scrip", "cost": 0}
    return {"allowed": True, "reason": "Paid access", "cost": price}
'''
        )

        self.executor.register_executable_contract(contract)

        # Verify contract is cached
        assert "custom_pay_per_use" in self.executor._contract_cache
        assert self.executor._contract_cache["custom_pay_per_use"] is contract

    def test_executable_contract_permission_check(self) -> None:
        """Test permission check via executable contract."""
        contract = ExecutableContract(
            contract_id="custom_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    price = 10
    if ledger and not ledger.can_afford_scrip(caller, price):
        return {"allowed": False, "reason": "Insufficient scrip", "cost": 0}
    return {"allowed": True, "reason": "Paid access", "cost": price}
'''
        )

        self.executor.register_executable_contract(contract)

        # Set artifact to use this contract
        self.artifact.access_contract_id = "custom_contract"  # type: ignore[attr-defined]

        # Rich user should be allowed
        result = self.executor._check_permission_via_contract(
            "rich_user", "read", self.artifact
        )
        assert result.allowed is True
        assert result.cost == 10

        # Poor user should be denied
        result = self.executor._check_permission_via_contract(
            "poor_user", "read", self.artifact
        )
        assert result.allowed is False
        assert "Insufficient" in result.reason

    def test_set_ledger(self) -> None:
        """Test setting ledger on executor."""
        from src.world.executor import SafeExecutor

        executor = SafeExecutor(timeout=5)
        assert executor._ledger is None

        executor.set_ledger(self.ledger)
        assert executor._ledger is self.ledger

    def test_fallback_to_genesis_contracts(self) -> None:
        """Test that unknown contracts fall back to freeware."""
        # Set artifact to use unknown contract
        self.artifact.access_contract_id = "nonexistent_contract"  # type: ignore[attr-defined]

        # Should fall back to freeware (allow read)
        result = self.executor._check_permission_via_contract(
            "anyone", "read", self.artifact
        )
        assert result.allowed is True
        assert "freeware" in result.reason.lower()

    def test_genesis_contracts_still_work(self) -> None:
        """Test that genesis contracts still work with executable contract support."""
        # Use private contract
        self.artifact.access_contract_id = "genesis_contract_private"  # type: ignore[attr-defined]

        # Owner should have access
        result = self.executor._check_permission_via_contract(
            "owner", "read", self.artifact
        )
        assert result.allowed is True

        # Non-owner should be denied
        result = self.executor._check_permission_via_contract(
            "stranger", "read", self.artifact
        )
        assert result.allowed is False


class TestContractDepthLimit:
    """Tests for contract execution depth limiting (Plan #100).

    Per ADR-0018 and Plan #100, contract execution depth must be tracked
    to prevent infinite recursion in permission check chains.
    """

    def setup_method(self) -> None:
        """Set up test fixtures."""
        from src.world.artifacts import Artifact
        from src.world.executor import SafeExecutor
        from src.world.ledger import Ledger

        from decimal import Decimal

        self.ledger = Ledger()
        self.ledger.create_principal("test_user", Decimal("1000"))
        self.ledger.create_principal("owner", Decimal("0"))

        self.executor = SafeExecutor(timeout=5)
        self.executor.set_ledger(self.ledger)

        from datetime import datetime

        # Create a basic artifact
        self.artifact = Artifact(
            id="test_artifact",
            type="test",
            content="test content",
            owner_id="owner",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        self.artifact.access_contract_id = "genesis_contract_freeware"  # type: ignore[attr-defined]

    def test_permission_check_at_depth_zero(self) -> None:
        """Test that permission checks work at default depth 0."""
        result = self.executor._check_permission_via_contract(
            caller="test_user",
            action="read",
            artifact=self.artifact,
        )
        assert result.allowed is True

    def test_permission_check_with_explicit_depth(self) -> None:
        """Test that permission checks accept depth parameter."""
        result = self.executor._check_permission_via_contract(
            caller="test_user",
            action="read",
            artifact=self.artifact,
            contract_depth=5,
        )
        assert result.allowed is True

    def test_permission_denied_at_max_depth(self) -> None:
        """Test that permission is denied when depth exceeds max_contract_depth."""
        # Default max is 10, so depth 10 should be denied
        result = self.executor._check_permission_via_contract(
            caller="test_user",
            action="read",
            artifact=self.artifact,
            contract_depth=10,
        )
        assert result.allowed is False
        assert "depth" in result.reason.lower()

    def test_depth_limit_configurable(self) -> None:
        """Test that max_contract_depth is configurable."""
        from src.world.executor import SafeExecutor

        # Create executor with custom depth limit
        executor = SafeExecutor(timeout=5, max_contract_depth=3)
        executor.set_ledger(self.ledger)

        # Depth 2 should work
        result = executor._check_permission_via_contract(
            caller="test_user",
            action="read",
            artifact=self.artifact,
            contract_depth=2,
        )
        assert result.allowed is True

        # Depth 3 should be denied (at limit)
        result = executor._check_permission_via_contract(
            caller="test_user",
            action="read",
            artifact=self.artifact,
            contract_depth=3,
        )
        assert result.allowed is False

    def test_depth_limit_error_message_informative(self) -> None:
        """Test that depth limit error message is informative."""
        result = self.executor._check_permission_via_contract(
            caller="test_user",
            action="read",
            artifact=self.artifact,
            contract_depth=10,
        )
        assert result.allowed is False
        # Error message should mention depth and limit
        assert "10" in result.reason or "depth" in result.reason.lower()
        assert "exceeded" in result.reason.lower() or "limit" in result.reason.lower()
