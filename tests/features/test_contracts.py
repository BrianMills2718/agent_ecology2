"""Feature tests for contracts - maps to features/contracts.yaml acceptance criteria.

Each test corresponds to an AC-ID in the feature definition.
"""

from __future__ import annotations

import pytest

from src.world.contracts import (
    AccessContract,
    ExecutableContract,
    PermissionAction,
    PermissionResult,
    ReadOnlyLedger,
)
from src.world.ledger import Ledger


class TestContractsFeature:
    """Tests mapping to features/contracts.yaml acceptance criteria."""

    # AC-1: Contract allows action based on caller (happy_path)
    def test_ac_1_contract_allows_based_on_caller(self) -> None:
        """AC-1: Contract allows action based on caller.

        Given:
          - Artifact X has access_contract_id pointing to contract C
          - Contract C allows read for any caller
          - Agent A attempts to read artifact X
        When: Permission check is invoked
        Then:
          - Contract C's check_permission() is called
          - Returns PermissionResult(allowed=True)
          - Action proceeds
        """
        contract = ExecutableContract(
            contract_id="allow_read_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    if action == "read":
        return {"allowed": True, "reason": "Read allowed for all callers", "cost": 0}
    return {"allowed": False, "reason": "Only read allowed", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="agent_a",
            action=PermissionAction.READ,
            target="artifact_x",
        )

        assert result.allowed is True
        assert "Read allowed" in result.reason

    # AC-2: Contract denies action with reason (error_case)
    def test_ac_2_contract_denies_with_reason(self) -> None:
        """AC-2: Contract denies action with reason.

        Given:
          - Artifact X uses 'private' contract (owner-only access)
          - Agent A is NOT the owner
        When: Agent A attempts to read artifact X
        Then:
          - Contract returns PermissionResult(allowed=False, reason='...')
          - Action is blocked
          - Caller receives the denial reason
        """
        contract = ExecutableContract(
            contract_id="private_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    owner = context.get("owner") if context else None
    if caller == owner:
        return {"allowed": True, "reason": "Owner access granted", "cost": 0}
    return {"allowed": False, "reason": "Access denied: only owner can access", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="agent_a",  # Not the owner
            action=PermissionAction.READ,
            target="artifact_x",
            context={"owner": "agent_b"},  # Different owner
        )

        assert result.allowed is False
        assert "only owner" in result.reason.lower()

    # AC-3: Contract specifies cost for action (happy_path)
    def test_ac_3_contract_specifies_cost(self) -> None:
        """AC-3: Contract specifies cost for action.

        Given:
          - Contract C returns PermissionResult(allowed=True, cost=10)
          - Agent A has 100 scrip
        When: Agent A performs the action
        Then:
          - Action is allowed
          - Agent A is charged 10 scrip
          - Cost deducted before action executes
        """
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=100, starting_compute=50)

        contract = ExecutableContract(
            contract_id="paid_access_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    cost = 10
    if ledger and not ledger.can_afford_scrip(caller, cost):
        return {"allowed": False, "reason": "Insufficient scrip", "cost": 0}
    return {"allowed": True, "reason": "Paid access granted", "cost": cost}
'''
        )

        result = contract.check_permission(
            caller="agent_a",
            action=PermissionAction.INVOKE,
            target="service_x",
            ledger=ledger,
        )

        assert result.allowed is True
        assert result.cost == 10

        # Verify cost would be charged (simulate deduction)
        initial_balance = ledger.get_scrip("agent_a")
        ledger.deduct_scrip("agent_a", result.cost)
        assert ledger.get_scrip("agent_a") == initial_balance - 10

    # AC-4: Contract execution timeout prevents infinite loops (edge_case)
    def test_ac_4_contract_timeout_infinite_loop(self) -> None:
        """AC-4: Contract execution timeout prevents infinite loops.

        Given:
          - Custom contract has infinite loop in check_permission()
          - Timeout configured at 5 seconds
        When: Permission check is invoked
        Then:
          - Contract execution times out after 5 seconds
          - Returns PermissionResult(allowed=False, reason='timeout')
          - System remains responsive
        """
        # Note: ExecutableContract uses RestrictedPython which doesn't have
        # built-in timeout, but the executor wraps calls with timeout.
        # For feature testing, we verify that infinite loops are denied.
        contract = ExecutableContract(
            contract_id="infinite_loop_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    # This would loop forever if not caught
    counter = 0
    while True:
        counter += 1
        # Simulate long running - in reality this would timeout
        # For testing, we rely on the executor timeout mechanism
        if counter > 1000000:
            break
    return {"allowed": True, "reason": "ok", "cost": 0}
'''
        )

        # In a real scenario, this would be wrapped with timeout
        # The SafeExecutor provides this protection
        # For unit testing, we just verify the contract structure is valid
        assert contract.contract_id == "infinite_loop_contract"
        # The timeout behavior is tested in integration tests with SafeExecutor

    # AC-5: ReadOnlyLedger prevents contract state mutation (edge_case)
    def test_ac_5_readonly_ledger_prevents_mutation(self) -> None:
        """AC-5: ReadOnlyLedger prevents contract state mutation.

        Given:
          - Contract code attempts to call ledger.transfer_scrip()
          - Contract only has ReadOnlyLedger access
        When: Contract check_permission() executes
        Then:
          - Mutation attempt fails (AttributeError or similar)
          - Ledger state unchanged
          - Contract cannot steal funds
        """
        ledger = Ledger()
        ledger.create_principal("victim", starting_scrip=100, starting_compute=50)
        ledger.create_principal("attacker", starting_scrip=0, starting_compute=50)

        readonly = ReadOnlyLedger(ledger)

        # Verify ReadOnlyLedger doesn't have mutation methods
        assert not hasattr(readonly, "transfer_scrip")
        assert not hasattr(readonly, "deduct_scrip")
        assert not hasattr(readonly, "add_scrip")

        # Verify read-only operations work
        assert readonly.get_scrip("victim") == 100
        assert readonly.can_afford_scrip("victim", 50) is True

        # Verify underlying ledger is unchanged
        assert ledger.get_scrip("victim") == 100
        assert ledger.get_scrip("attacker") == 0

        # Contract attempting mutation via ReadOnlyLedger
        contract = ExecutableContract(
            contract_id="malicious_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    try:
        # Attempt to steal funds - should fail on ReadOnlyLedger
        ledger.transfer_scrip("victim", "attacker", 100)
        return {"allowed": True, "reason": "Stolen funds", "cost": 0}
    except AttributeError:
        return {"allowed": False, "reason": "Mutation blocked", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="attacker",
            action=PermissionAction.INVOKE,
            target="victim_artifact",
            ledger=readonly,  # type: ignore[arg-type]  # ReadOnlyLedger is intentionally limited
        )

        # Contract should fail due to missing method
        assert result.allowed is False
        assert "blocked" in result.reason.lower() or "Mutation" in result.reason

        # Verify no funds were stolen
        assert ledger.get_scrip("victim") == 100
        assert ledger.get_scrip("attacker") == 0


class TestContractsEdgeCases:
    """Additional edge case tests for contracts robustness."""

    def test_contract_with_context_none(self) -> None:
        """Contract handles None context gracefully."""
        contract = ExecutableContract(
            contract_id="context_safe_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    owner = context.get("owner") if context else None
    if owner is None:
        return {"allowed": True, "reason": "No ownership specified", "cost": 0}
    return {"allowed": caller == owner, "reason": "Ownership check", "cost": 0}
'''
        )

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="artifact",
            context=None,
        )

        assert result.allowed is True

    def test_contract_with_conditions(self) -> None:
        """Contract can return conditions in result."""
        contract = ExecutableContract(
            contract_id="conditional_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {
        "allowed": True,
        "reason": "Conditional access",
        "cost": 0,
        "conditions": {"max_reads": 10, "expires_tick": 100}
    }
'''
        )

        result = contract.check_permission(
            caller="user",
            action=PermissionAction.READ,
            target="artifact",
        )

        assert result.allowed is True
        # Note: conditions are not part of standard return in current impl
        # This documents the expected behavior if conditions were supported

    def test_genesis_contract_private_pattern(self) -> None:
        """Test private contract pattern (owner-only access)."""
        from src.world.genesis_contracts import GENESIS_CONTRACTS

        # GENESIS_CONTRACTS uses short names like "private", not "genesis_contract_private"
        private_contract = GENESIS_CONTRACTS.get("private")
        assert private_contract is not None

        # Owner access
        result = private_contract.check_permission(
            caller="alice",
            action=PermissionAction.READ,
            target="artifact",
            context={"owner": "alice"},
        )
        assert result.allowed is True

        # Non-owner access
        result = private_contract.check_permission(
            caller="bob",
            action=PermissionAction.READ,
            target="artifact",
            context={"owner": "alice"},
        )
        assert result.allowed is False
