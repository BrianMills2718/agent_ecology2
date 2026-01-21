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
        """Verify all expected actions are defined (ADR-0019)."""
        # ADR-0019 defines five kernel actions
        expected_actions = {"read", "write", "edit", "invoke", "delete"}
        actual_actions = {action.value for action in PermissionAction}
        assert actual_actions == expected_actions

    def test_action_string_values(self) -> None:
        """Verify actions have correct string values."""
        assert PermissionAction.READ.value == "read"
        assert PermissionAction.WRITE.value == "write"
        assert PermissionAction.EDIT.value == "edit"
        assert PermissionAction.INVOKE.value == "invoke"
        assert PermissionAction.DELETE.value == "delete"

    def test_action_from_string(self) -> None:
        """Verify actions can be created from strings."""
        assert PermissionAction("read") == PermissionAction.READ
        assert PermissionAction("write") == PermissionAction.WRITE
        assert PermissionAction("edit") == PermissionAction.EDIT
        assert PermissionAction("invoke") == PermissionAction.INVOKE
        assert PermissionAction("delete") == PermissionAction.DELETE

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
        read_actions = {PermissionAction.READ, PermissionAction.INVOKE}
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
        """Verify common action groupings work as expected (ADR-0019)."""
        read_only_actions = (PermissionAction.READ, PermissionAction.INVOKE)
        modify_actions = (PermissionAction.WRITE, PermissionAction.EDIT, PermissionAction.DELETE)

        # Verify no overlap
        assert set(read_only_actions).isdisjoint(set(modify_actions))

        # Verify complete coverage
        all_actions = set(read_only_actions) | set(modify_actions)
        assert all_actions == set(PermissionAction)

    def test_action_iteration(self) -> None:
        """Verify PermissionAction can be iterated."""
        actions = list(PermissionAction)
        assert len(actions) == 5  # ADR-0019: read, write, edit, invoke, delete
        assert PermissionAction.READ in actions
        assert PermissionAction.EDIT in actions

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
            created_by="owner",
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
            created_by="owner",
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


class TestContractTimeoutConfiguration:
    """Tests for contract timeout configuration (Plan #100).

    Per Plan #100 Phase 2:
    - Base permission checks: 5 seconds (configurable from config)
    - Contracts with `call_llm` capability: 30 seconds
    - Configurable per contract via `timeout_seconds` field
    """

    def test_default_timeout_from_config(self) -> None:
        """Test that ExecutableContract uses config-based default timeout."""
        # Contract without explicit timeout should use config default (5s)
        contract = ExecutableContract(
            contract_id="default_timeout",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "ok", "cost": 0}
'''
        )

        # Default should be 5 seconds from config, not hardcoded 1 second
        from src.config import get_validated_config
        expected_default = get_validated_config().executor.contract_timeout
        assert contract.timeout == expected_default
        assert contract.timeout == 5  # Plan specifies 5s default

    def test_custom_timeout_per_contract(self) -> None:
        """Test that contracts can override default timeout."""
        contract = ExecutableContract(
            contract_id="custom_timeout",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "ok", "cost": 0}
''',
            timeout=10  # Custom timeout
        )

        assert contract.timeout == 10

    def test_llm_capability_extended_timeout(self) -> None:
        """Test that contracts declaring LLM capability get extended timeout."""
        # Contract with call_llm capability should default to 30 seconds
        contract = ExecutableContract(
            contract_id="llm_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "ok", "cost": 0}
''',
            capabilities=["call_llm"]  # Declares LLM capability
        )

        # Should default to 30 seconds for LLM contracts
        from src.config import get_validated_config
        expected_llm_timeout = get_validated_config().executor.contract_llm_timeout
        assert contract.timeout == expected_llm_timeout
        assert contract.timeout == 30  # Plan specifies 30s for LLM

    def test_llm_capability_can_override_timeout(self) -> None:
        """Test that LLM contracts can still set custom timeout."""
        contract = ExecutableContract(
            contract_id="llm_custom_timeout",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "ok", "cost": 0}
''',
            capabilities=["call_llm"],
            timeout=60  # Explicit override
        )

        # Explicit timeout should override LLM default
        assert contract.timeout == 60

    def test_timeout_enforcement_uses_configured_value(self) -> None:
        """Test that timeout is actually enforced using configured value."""
        # Create a contract that sleeps for 2 seconds
        # Note: time module is pre-loaded in CONTRACT_ALLOWED_MODULES, no import needed
        contract = ExecutableContract(
            contract_id="slow_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    # time module is already available (pre-loaded)
    time.sleep(2)
    return {"allowed": True, "reason": "ok", "cost": 0}
''',
            timeout=1  # 1 second timeout - should fail
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )

        # Should timeout
        assert result.allowed is False
        assert "timed out" in result.reason.lower()

    def test_no_timeout_with_sufficient_time(self) -> None:
        """Test that contract completes when given sufficient time."""
        # Create a contract that sleeps briefly
        # Note: time module is pre-loaded in CONTRACT_ALLOWED_MODULES, no import needed
        contract = ExecutableContract(
            contract_id="quick_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    # time module is already available (pre-loaded)
    time.sleep(0.1)  # 100ms sleep
    return {"allowed": True, "reason": "completed", "cost": 0}
''',
            timeout=5  # 5 second timeout - plenty of time
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact_1",
        )

        # Should complete successfully
        assert result.allowed is True
        assert "completed" in result.reason

    def test_capabilities_field_exists(self) -> None:
        """Test that ExecutableContract accepts capabilities field."""
        contract = ExecutableContract(
            contract_id="capable_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "ok", "cost": 0}
''',
            capabilities=["call_llm", "invoke_artifact"]
        )

        # Should have capabilities attribute
        assert hasattr(contract, 'capabilities')
        assert "call_llm" in contract.capabilities
        assert "invoke_artifact" in contract.capabilities

    def test_empty_capabilities_by_default(self) -> None:
        """Test that contracts have no capabilities by default."""
        contract = ExecutableContract(
            contract_id="basic_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "ok", "cost": 0}
'''
        )

        # Should have empty capabilities by default
        assert hasattr(contract, 'capabilities')
        assert contract.capabilities == []


class TestContractPermissionCaching:
    """Tests for TTL-based permission caching (Plan #100 Phase 2).

    Per Plan #100:
    - Caching is opt-in via contract field `cache_policy: {ttl_seconds: N}`
    - No caching by default (explicit is better)
    - Cache key: (artifact_id, action, requester_id, contract_version)
    """

    def test_cache_policy_field_exists(self) -> None:
        """Test that ExecutableContract accepts cache_policy field."""
        contract = ExecutableContract(
            contract_id="cached_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "ok", "cost": 0}
''',
            cache_policy={"ttl_seconds": 60}
        )

        assert hasattr(contract, 'cache_policy')
        assert contract.cache_policy == {"ttl_seconds": 60}

    def test_no_cache_policy_by_default(self) -> None:
        """Test that contracts have no cache_policy by default."""
        contract = ExecutableContract(
            contract_id="uncached_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "ok", "cost": 0}
'''
        )

        # Should have None cache_policy by default (no caching)
        assert contract.cache_policy is None

    def test_cache_policy_ttl_seconds_required(self) -> None:
        """Test that cache_policy must have ttl_seconds."""
        contract = ExecutableContract(
            contract_id="valid_cache",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "ok", "cost": 0}
''',
            cache_policy={"ttl_seconds": 30}
        )

        assert contract.cache_policy is not None
        assert contract.cache_policy["ttl_seconds"] == 30

    def test_permission_cache_stores_results(self) -> None:
        """Test that permission cache stores results when cache_policy is set."""
        from src.world.contracts import PermissionCache

        cache = PermissionCache()
        result = PermissionResult(allowed=True, reason="cached", cost=0)

        # Store a result
        cache_key = ("artifact_1", "read", "user_1", "v1")
        cache.put(cache_key, result, ttl_seconds=60)

        # Should retrieve the same result
        cached = cache.get(cache_key)
        assert cached is not None
        assert cached.allowed == result.allowed
        assert cached.reason == result.reason

    def test_permission_cache_respects_ttl(self) -> None:
        """Test that cached results expire after TTL."""
        from src.world.contracts import PermissionCache
        import time

        cache = PermissionCache()
        result = PermissionResult(allowed=True, reason="cached", cost=0)

        # Store with 0.1 second TTL
        cache_key = ("artifact_1", "read", "user_1", "v1")
        cache.put(cache_key, result, ttl_seconds=0.1)

        # Should be present immediately
        assert cache.get(cache_key) is not None

        # Wait for expiry
        time.sleep(0.15)

        # Should be expired
        assert cache.get(cache_key) is None

    def test_permission_cache_miss_returns_none(self) -> None:
        """Test that cache miss returns None."""
        from src.world.contracts import PermissionCache

        cache = PermissionCache()
        cache_key = ("nonexistent", "read", "user", "v1")

        assert cache.get(cache_key) is None

    def test_permission_cache_key_components(self) -> None:
        """Test that cache key includes all required components."""
        from src.world.contracts import PermissionCache

        cache = PermissionCache()
        result = PermissionResult(allowed=True, reason="test", cost=0)

        # Store with specific key
        key1 = ("artifact_1", "read", "user_1", "v1")
        cache.put(key1, result, ttl_seconds=60)

        # Different artifact should miss
        key2 = ("artifact_2", "read", "user_1", "v1")
        assert cache.get(key2) is None

        # Different action should miss
        key3 = ("artifact_1", "write", "user_1", "v1")
        assert cache.get(key3) is None

        # Different user should miss
        key4 = ("artifact_1", "read", "user_2", "v1")
        assert cache.get(key4) is None

        # Different version should miss
        key5 = ("artifact_1", "read", "user_1", "v2")
        assert cache.get(key5) is None

        # Original key should still hit
        assert cache.get(key1) is not None

    def test_executor_uses_cache_when_policy_set(self) -> None:
        """Test that executor uses permission cache when contract has cache_policy."""
        from src.world.executor import SafeExecutor
        from src.world.artifacts import Artifact
        from datetime import datetime

        ledger = Ledger()
        ledger.create_principal("test_user", starting_scrip=100)
        ledger.create_principal("owner", starting_scrip=0)

        executor = SafeExecutor(timeout=5, use_contracts=True, ledger=ledger)

        # Create contract with cache_policy
        contract = ExecutableContract(
            contract_id="cached_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "cached result", "cost": 0}
''',
            cache_policy={"ttl_seconds": 60}
        )
        executor.register_executable_contract(contract)

        artifact = Artifact(
            id="test_artifact",
            type="test",
            content="test",
            created_by="owner",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        artifact.access_contract_id = "cached_contract"  # type: ignore[attr-defined]

        # Permission cache should be empty before first call
        cache_key = ("test_artifact", "read", "test_user", "v1")
        assert executor._permission_cache.get(cache_key) is None

        # First call should execute contract and populate cache
        result1 = executor._check_permission_via_contract(
            "test_user", "read", artifact
        )
        assert result1.allowed is True
        assert "cached result" in result1.reason

        # Permission cache should now have the result
        cached_result = executor._permission_cache.get(cache_key)
        assert cached_result is not None
        assert cached_result.allowed is True
        assert "cached result" in cached_result.reason

        # Second call should use cache (same result)
        result2 = executor._check_permission_via_contract(
            "test_user", "read", artifact
        )
        assert result2.allowed is True
        assert "cached result" in result2.reason

    def test_executor_no_cache_without_policy(self) -> None:
        """Test that executor does not cache when contract has no cache_policy."""
        from src.world.executor import SafeExecutor
        from src.world.artifacts import Artifact
        from datetime import datetime

        ledger = Ledger()
        ledger.create_principal("test_user", starting_scrip=100)
        ledger.create_principal("owner", starting_scrip=0)

        executor = SafeExecutor(timeout=5, use_contracts=True, ledger=ledger)

        # Create contract WITHOUT cache_policy
        contract = ExecutableContract(
            contract_id="uncached_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "not cached", "cost": 0}
'''
            # No cache_policy
        )
        executor.register_executable_contract(contract)

        artifact = Artifact(
            id="test_artifact",
            type="test",
            content="test",
            created_by="owner",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        artifact.access_contract_id = "uncached_contract"  # type: ignore[attr-defined]

        # First call
        result1 = executor._check_permission_via_contract(
            "test_user", "read", artifact
        )
        assert result1.allowed is True

        # Permission cache should be empty (no cache_policy)
        cache_key = ("test_artifact", "read", "test_user", "v1")
        assert executor._permission_cache.get(cache_key) is None

        # Second call
        result2 = executor._check_permission_via_contract(
            "test_user", "read", artifact
        )
        assert result2.allowed is True

        # Permission cache should still be empty
        assert executor._permission_cache.get(cache_key) is None

    def test_cache_invalidated_on_different_context(self) -> None:
        """Test that cache respects different request contexts."""
        from src.world.contracts import PermissionCache

        cache = PermissionCache()
        result1 = PermissionResult(allowed=True, reason="allowed", cost=0)
        result2 = PermissionResult(allowed=False, reason="denied", cost=0)

        # Same artifact but different callers
        key1 = ("artifact_1", "read", "alice", "v1")
        key2 = ("artifact_1", "read", "bob", "v1")

        cache.put(key1, result1, ttl_seconds=60)
        cache.put(key2, result2, ttl_seconds=60)

        # Should get correct result for each caller
        assert cache.get(key1).allowed is True
        assert cache.get(key2).allowed is False

    def test_cache_clear_removes_all_entries(self) -> None:
        """Test that cache can be cleared."""
        from src.world.contracts import PermissionCache

        cache = PermissionCache()
        result = PermissionResult(allowed=True, reason="test", cost=0)

        cache.put(("a1", "read", "u1", "v1"), result, ttl_seconds=60)
        cache.put(("a2", "read", "u2", "v1"), result, ttl_seconds=60)

        assert cache.get(("a1", "read", "u1", "v1")) is not None
        assert cache.get(("a2", "read", "u2", "v1")) is not None

        cache.clear()

        assert cache.get(("a1", "read", "u1", "v1")) is None
        assert cache.get(("a2", "read", "u2", "v1")) is None

    def test_executor_permission_cache_configurable(self) -> None:
        """Test that executor permission cache can be enabled/disabled."""
        from src.world.executor import SafeExecutor

        # Default executor should have permission cache enabled
        executor = SafeExecutor(timeout=5, use_contracts=True)
        assert hasattr(executor, '_permission_cache')

        # Should be able to clear cache
        executor.clear_permission_cache()

    def test_contract_version_affects_cache_key(self) -> None:
        """Test that contract version is part of cache key."""
        from src.world.contracts import PermissionCache

        cache = PermissionCache()
        result_v1 = PermissionResult(allowed=True, reason="v1", cost=0)
        result_v2 = PermissionResult(allowed=False, reason="v2", cost=0)

        # Same artifact/action/user but different contract versions
        cache.put(("artifact", "read", "user", "v1"), result_v1, ttl_seconds=60)
        cache.put(("artifact", "read", "user", "v2"), result_v2, ttl_seconds=60)

        assert cache.get(("artifact", "read", "user", "v1")).allowed is True
        assert cache.get(("artifact", "read", "user", "v2")).allowed is False


class TestDanglingContractHandling:
    """Tests for dangling contract handling (Plan #100 Phase 2, ADR-0017).

    When an artifact's access_contract_id points to a deleted/missing contract,
    the system should fail open to a configurable default contract.
    """

    def setup_method(self) -> None:
        """Set up test fixtures."""
        from src.world.executor import SafeExecutor
        from src.world.artifacts import Artifact
        from datetime import datetime

        self.ledger = Ledger()
        self.ledger.create_principal("test_user", starting_scrip=100)
        self.ledger.create_principal("owner", starting_scrip=0)

        self.executor = SafeExecutor(timeout=5, use_contracts=True, ledger=self.ledger)

        # Create artifact with a non-existent contract
        self.artifact = Artifact(
            id="test_artifact",
            type="test",
            content="test content",
            created_by="owner",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        self.artifact.access_contract_id = "deleted_contract_xyz"  # type: ignore[attr-defined]

    def test_missing_contract_falls_back_to_default(self) -> None:
        """Test that missing contract falls back to default (freeware)."""
        # Access should succeed because freeware allows reads
        result = self.executor._check_permission_via_contract(
            "test_user", "read", self.artifact
        )
        assert result.allowed is True
        # Should indicate it's using freeware fallback
        assert "freeware" in result.reason.lower()

    def test_missing_contract_logs_warning(self) -> None:
        """Test that missing contract logs a warning."""
        import logging

        # Capture warnings
        with self.assertLogs('src.world.executor', level='WARNING') as cm:
            self.executor._check_permission_via_contract(
                "test_user", "read", self.artifact
            )

        # Should have logged a warning about dangling contract
        assert any("dangling" in log.lower() or "missing" in log.lower() for log in cm.output)

    def test_dangling_contract_info_returned(self) -> None:
        """Test that dangling contract information is available."""
        result = self.executor._check_permission_via_contract(
            "test_user", "read", self.artifact
        )

        # The result should indicate it was a fallback
        assert result.allowed is True
        # Conditions should contain dangling info (for observability)
        assert result.conditions is not None
        assert result.conditions.get("dangling_contract") is True
        assert result.conditions.get("original_contract_id") == "deleted_contract_xyz"

    def test_default_contract_configurable(self) -> None:
        """Test that default contract for dangling refs is configurable."""
        from src.config import get

        # Default should be freeware
        default = get("contracts.default_on_missing")
        assert default == "genesis_contract_freeware"

    def test_private_artifact_accessible_after_contract_deletion(self) -> None:
        """Test that previously private artifact becomes accessible via freeware."""
        # Set artifact to use a "private" contract that doesn't exist
        self.artifact.access_contract_id = "deleted_private_contract"  # type: ignore[attr-defined]

        # With freeware fallback, reads should be allowed
        result = self.executor._check_permission_via_contract(
            "test_user", "read", self.artifact
        )
        assert result.allowed is True

        # But writes should still be denied (freeware requires ownership)
        result = self.executor._check_permission_via_contract(
            "test_user", "write", self.artifact
        )
        assert result.allowed is False

    def test_owner_can_still_write_after_contract_deletion(self) -> None:
        """Test that owner retains write access via freeware fallback."""
        self.artifact.access_contract_id = "deleted_contract"  # type: ignore[attr-defined]

        # Owner should be able to write (freeware allows owner writes)
        result = self.executor._check_permission_via_contract(
            "owner", "write", self.artifact
        )
        assert result.allowed is True

    def test_executor_has_dangling_contract_tracking(self) -> None:
        """Test that executor can report dangling contract occurrences."""
        # First access with dangling contract
        self.executor._check_permission_via_contract(
            "test_user", "read", self.artifact
        )

        # Executor should track dangling contracts for observability
        assert hasattr(self.executor, 'get_dangling_contract_count')
        count = self.executor.get_dangling_contract_count()
        assert count >= 1

    def test_valid_contract_does_not_trigger_dangling_logic(self) -> None:
        """Test that valid contracts don't trigger dangling contract handling."""
        # Use a valid genesis contract
        self.artifact.access_contract_id = "genesis_contract_freeware"  # type: ignore[attr-defined]

        result = self.executor._check_permission_via_contract(
            "test_user", "read", self.artifact
        )

        # Should not have dangling contract conditions
        assert result.allowed is True
        if result.conditions:
            assert result.conditions.get("dangling_contract") is not True

    # Helper for assertLogs context manager
    def assertLogs(self, logger_name: str, level: str = 'WARNING'):
        """Context manager for capturing logs."""
        import logging
        return _LogCapture(logger_name, level)


class _LogCapture:
    """Helper class for capturing log messages in tests."""

    def __init__(self, logger_name: str, level: str):
        import logging
        self.logger_name = logger_name
        self.level = getattr(logging, level)
        self.handler: logging.Handler | None = None
        self.output: list[str] = []

    def __enter__(self) -> "_LogCapture":
        import logging

        class ListHandler(logging.Handler):
            def __init__(self, output_list: list[str]):
                super().__init__()
                self.output_list = output_list

            def emit(self, record: logging.LogRecord) -> None:
                self.output_list.append(self.format(record))

        logger = logging.getLogger(self.logger_name)
        self.handler = ListHandler(self.output)
        self.handler.setLevel(self.level)
        logger.addHandler(self.handler)
        self._original_level = logger.level
        logger.setLevel(self.level)
        return self

    def __exit__(self, *args: object) -> None:
        import logging
        logger = logging.getLogger(self.logger_name)
        if self.handler:
            logger.removeHandler(self.handler)
        logger.setLevel(self._original_level)
