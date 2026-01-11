"""Tests for pay() capability in artifact execution."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from world.executor import SafeExecutor
from world.ledger import Ledger


class TestPayCapability:
    """Test that artifacts can pay from their wallet during execution."""

    def test_pay_transfers_scrip(self) -> None:
        """pay() should transfer scrip from artifact to target."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=0, starting_compute=0)
        # Fund the contract
        ledger.transfer_scrip("alice", "payout_contract", 100)
        # Actually alice starts with 0 and we transfer 100 from nowhere, let's fix:
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=0)
        ledger.transfer_scrip("alice", "payout_contract", 100)

        code = '''
def run(recipient):
    result = pay(recipient, 50)
    return {"paid": result["success"], "balance": get_balance()}
'''
        executor = SafeExecutor(timeout=5)
        result = executor.execute_with_wallet(
            code,
            args=["alice"],
            artifact_id="payout_contract",
            ledger=ledger
        )

        assert result["success"] is True
        assert result["result"]["paid"] is True
        assert result["result"]["balance"] == 50
        assert ledger.get_scrip("alice") == 50  # Alice received payment
        assert ledger.get_scrip("payout_contract") == 50  # Contract spent 50

    def test_pay_insufficient_funds_fails(self) -> None:
        """pay() should fail if artifact doesn't have enough scrip."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=0)
        ledger.transfer_scrip("alice", "small_contract", 10)

        code = '''
def run(recipient):
    result = pay(recipient, 50)  # Try to pay more than balance
    return {"success": result["success"], "error": result["error"]}
'''
        executor = SafeExecutor(timeout=5)
        result = executor.execute_with_wallet(
            code,
            args=["alice"],
            artifact_id="small_contract",
            ledger=ledger
        )

        assert result["success"] is True  # Execution succeeded
        assert result["result"]["success"] is False  # But payment failed
        assert "Insufficient" in result["result"]["error"]

    def test_pay_negative_amount_rejected(self) -> None:
        """pay() should reject negative amounts."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=0)
        ledger.transfer_scrip("alice", "contract", 50)

        code = '''
def run(recipient):
    result = pay(recipient, -10)
    return result
'''
        executor = SafeExecutor(timeout=5)
        result = executor.execute_with_wallet(
            code,
            args=["alice"],
            artifact_id="contract",
            ledger=ledger
        )

        assert result["success"] is True
        assert result["result"]["success"] is False
        assert "positive" in result["result"]["error"]

    def test_get_balance_returns_current_balance(self) -> None:
        """get_balance() should return artifact's current scrip."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100, starting_compute=0)
        ledger.transfer_scrip("alice", "contract", 75)

        code = '''
def run():
    return get_balance()
'''
        executor = SafeExecutor(timeout=5)
        result = executor.execute_with_wallet(
            code,
            args=[],
            artifact_id="contract",
            ledger=ledger
        )

        assert result["success"] is True
        assert result["result"] == 75

    def test_multiple_payments(self) -> None:
        """Artifact can make multiple payments in one execution."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=0, starting_compute=0)
        ledger.create_principal("bob", starting_scrip=0, starting_compute=0)
        ledger.ensure_principal("rich_contract")
        ledger.credit_scrip("rich_contract", 100)

        code = '''
def run():
    pay("alice", 30)
    pay("bob", 20)
    return get_balance()
'''
        executor = SafeExecutor(timeout=5)
        result = executor.execute_with_wallet(
            code,
            args=[],
            artifact_id="rich_contract",
            ledger=ledger
        )

        assert result["success"] is True
        assert result["result"] == 50  # 100 - 30 - 20
        assert ledger.get_scrip("alice") == 30
        assert ledger.get_scrip("bob") == 20

    def test_pay_creates_recipient_wallet(self) -> None:
        """pay() to non-existent recipient should create their wallet."""
        ledger = Ledger()
        ledger.ensure_principal("contract")
        ledger.credit_scrip("contract", 100)

        code = '''
def run():
    result = pay("new_agent", 25)
    return result["success"]
'''
        executor = SafeExecutor(timeout=5)
        result = executor.execute_with_wallet(
            code,
            args=[],
            artifact_id="contract",
            ledger=ledger
        )

        assert result["success"] is True
        assert result["result"] is True
        assert ledger.get_scrip("new_agent") == 25


class TestPayCapabilityWithoutWallet:
    """Test execution without wallet context."""

    def test_no_wallet_means_no_pay(self) -> None:
        """Without wallet context, pay() shouldn't be available."""
        code = '''
def run():
    try:
        pay("someone", 10)
        return "pay exists"
    except NameError:
        return "pay not defined"
'''
        executor = SafeExecutor(timeout=5)
        # Execute without wallet context
        result = executor.execute_with_wallet(code, args=[])

        assert result["success"] is True
        assert result["result"] == "pay not defined"

    def test_regular_execute_has_no_pay(self) -> None:
        """Regular execute() should not have pay()."""
        code = '''
def run():
    try:
        pay("someone", 10)
        return "pay exists"
    except NameError:
        return "pay not defined"
'''
        executor = SafeExecutor(timeout=5)
        result = executor.execute(code, args=[])

        assert result["success"] is True
        assert result["result"] == "pay not defined"


class TestPayCapabilitySecurity:
    """Security tests for pay capability."""

    def test_cannot_spend_other_wallets(self) -> None:
        """pay() can only spend from the artifact's own wallet."""
        ledger = Ledger()
        ledger.create_principal("rich_agent", starting_scrip=1000, starting_compute=0)
        ledger.ensure_principal("contract")
        ledger.credit_scrip("contract", 10)

        # Contract only has 10 scrip, even though rich_agent has 1000
        code = '''
def run():
    # Try to pay more than contract has
    result = pay("thief", 100)
    return {"success": result["success"], "contract_balance": get_balance()}
'''
        executor = SafeExecutor(timeout=5)
        result = executor.execute_with_wallet(
            code,
            args=[],
            artifact_id="contract",
            ledger=ledger
        )

        assert result["success"] is True
        assert result["result"]["success"] is False  # Payment failed
        assert result["result"]["contract_balance"] == 10  # Contract still has 10
        assert ledger.get_scrip("rich_agent") == 1000  # Rich agent untouched
