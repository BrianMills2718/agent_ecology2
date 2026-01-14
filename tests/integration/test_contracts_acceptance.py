"""Feature acceptance tests for contracts - maps to features/contracts.yaml.

Run with: pytest --feature contracts tests/
"""

from __future__ import annotations

import pytest

from src.world.contracts import (
    ExecutableContract,
    PermissionAction,
)
from src.world.ledger import Ledger


@pytest.mark.feature("contracts")
class TestContractsFeature:
    """Tests mapping to features/contracts.yaml acceptance criteria."""

    # AC-1: Contract allows action based on caller (happy_path)
    def test_ac_1_contract_allows_based_on_caller(self) -> None:
        """AC-1: Contract allows action based on caller."""
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
        """AC-2: Contract denies action with reason."""
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
            caller="agent_a",
            action=PermissionAction.READ,
            target="artifact_x",
            context={"owner": "agent_b"},
        )

        assert result.allowed is False
        assert "only owner" in result.reason.lower()

    # AC-3: Contract specifies cost for action (happy_path)
    def test_ac_3_contract_specifies_cost(self) -> None:
        """AC-3: Contract specifies cost for action."""
        contract = ExecutableContract(
            contract_id="cost_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    return {"allowed": True, "reason": "Action allowed with cost", "cost": 10}
'''
        )

        result = contract.check_permission(
            caller="agent_a",
            action=PermissionAction.READ,
            target="artifact_x",
        )

        assert result.allowed is True
        assert result.cost == 10


@pytest.mark.feature("contracts")
class TestContractsEdgeCases:
    """Additional edge case tests for contracts robustness."""

    def test_contract_with_ledger_access(self) -> None:
        """Contract can read ledger data for decisions."""
        ledger = Ledger()
        ledger.create_principal("rich_agent", starting_scrip=1000, starting_compute=50)
        ledger.create_principal("poor_agent", starting_scrip=10, starting_compute=50)

        contract = ExecutableContract(
            contract_id="rich_only_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    if ledger is not None:
        balance = ledger.get_scrip(caller)
        if balance >= 100:
            return {"allowed": True, "reason": "Sufficient balance", "cost": 0}
    return {"allowed": False, "reason": "Insufficient balance for access", "cost": 0}
'''
        )

        # Rich agent can access
        result = contract.check_permission(
            caller="rich_agent",
            action=PermissionAction.READ,
            target="artifact",
            ledger=ledger,
        )
        assert result.allowed is True

        # Poor agent cannot access
        result = contract.check_permission(
            caller="poor_agent",
            action=PermissionAction.READ,
            target="artifact",
            ledger=ledger,
        )
        assert result.allowed is False

    def test_contract_code_error_returns_denied(self) -> None:
        """Contract code error results in access denied."""
        contract = ExecutableContract(
            contract_id="buggy_contract",
            code='''
def check_permission(caller, action, target, context, ledger):
    # This will cause an error
    return 1 / 0
'''
        )

        result = contract.check_permission(
            caller="agent_a",
            action=PermissionAction.READ,
            target="artifact",
        )

        assert result.allowed is False
        assert "error" in result.reason.lower() or "exception" in result.reason.lower()
