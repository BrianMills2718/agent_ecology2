"""Unit tests for GenesisDebtContract.

Tests the non-privileged debt contract example that demonstrates
credit/lending patterns without kernel-level enforcement.
"""

import pytest
from src.world.genesis import GenesisDebtContract
from src.world.ledger import Ledger


class TestGenesisDebtContract:
    """Test the debt contract genesis artifact."""

    @pytest.fixture
    def ledger(self) -> Ledger:
        """Create a fresh ledger with test principals."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100)
        ledger.create_principal("bob", starting_scrip=100)
        ledger.create_principal("charlie", starting_scrip=50)
        return ledger

    @pytest.fixture
    def debt_contract(self, ledger: Ledger) -> GenesisDebtContract:
        """Create a debt contract instance."""
        contract = GenesisDebtContract(ledger=ledger)
        contract.set_tick(0)
        return contract

    def test_issue_debt_creates_pending_debt(
        self, debt_contract: GenesisDebtContract
    ) -> None:
        """Issuing debt creates a pending record."""
        result = debt_contract._issue(
            args=["bob", 50, 0.01, 100],  # creditor, principal, rate, due_tick
            invoker_id="alice"  # alice becomes debtor
        )

        assert result["success"] is True
        assert "debt_id" in result
        assert result["debtor"] == "alice"
        assert result["creditor"] == "bob"
        assert result["principal"] == 50

    def test_issue_validates_inputs(
        self, debt_contract: GenesisDebtContract
    ) -> None:
        """Issue validates input parameters."""
        # Missing args
        result = debt_contract._issue(args=[], invoker_id="alice")
        assert result["success"] is False
        assert "requires" in result["error"]

        # Invalid principal
        result = debt_contract._issue(
            args=["bob", -10, 0.01, 100],
            invoker_id="alice"
        )
        assert result["success"] is False
        assert "positive integer" in result["error"]

        # Invalid interest rate
        result = debt_contract._issue(
            args=["bob", 50, -0.1, 100],
            invoker_id="alice"
        )
        assert result["success"] is False
        assert "non-negative" in result["error"]

        # Due tick in past
        result = debt_contract._issue(
            args=["bob", 50, 0.01, 0],  # due_tick = 0, current = 0
            invoker_id="alice"
        )
        assert result["success"] is False
        assert "greater than current tick" in result["error"]

        # Cannot issue to self
        result = debt_contract._issue(
            args=["alice", 50, 0.01, 100],
            invoker_id="alice"
        )
        assert result["success"] is False
        assert "yourself" in result["error"]

    def test_accept_activates_debt(
        self, debt_contract: GenesisDebtContract
    ) -> None:
        """Creditor accepting debt activates it."""
        # Issue debt
        issue_result = debt_contract._issue(
            args=["bob", 50, 0.01, 100],
            invoker_id="alice"
        )
        debt_id = issue_result["debt_id"]

        # Accept as creditor
        result = debt_contract._accept(
            args=[debt_id],
            invoker_id="bob"
        )

        assert result["success"] is True
        assert result["debt_id"] == debt_id

        # Check debt is now active
        check_result = debt_contract._check(args=[debt_id], invoker_id="alice")
        assert check_result["debt"]["status"] == "active"

    def test_only_creditor_can_accept(
        self, debt_contract: GenesisDebtContract
    ) -> None:
        """Only the designated creditor can accept."""
        issue_result = debt_contract._issue(
            args=["bob", 50, 0.01, 100],
            invoker_id="alice"
        )
        debt_id = issue_result["debt_id"]

        # Try to accept as wrong person
        result = debt_contract._accept(
            args=[debt_id],
            invoker_id="charlie"
        )
        assert result["success"] is False
        assert "creditor" in result["error"].lower()

    def test_repay_transfers_scrip(
        self, debt_contract: GenesisDebtContract, ledger: Ledger
    ) -> None:
        """Repaying debt transfers scrip to creditor."""
        # Issue and accept debt
        issue_result = debt_contract._issue(
            args=["bob", 50, 0.0, 100],  # No interest for simplicity
            invoker_id="alice"
        )
        debt_id = issue_result["debt_id"]
        debt_contract._accept(args=[debt_id], invoker_id="bob")

        # Check initial balances
        assert ledger.get_scrip("alice") == 100
        assert ledger.get_scrip("bob") == 100

        # Repay part of debt
        result = debt_contract._repay(
            args=[debt_id, 20],
            invoker_id="alice"
        )

        assert result["success"] is True
        assert result["amount_paid"] == 20
        assert result["remaining"] == 30
        assert ledger.get_scrip("alice") == 80
        assert ledger.get_scrip("bob") == 120

    def test_repay_fully_marks_paid(
        self, debt_contract: GenesisDebtContract
    ) -> None:
        """Full repayment marks debt as paid."""
        issue_result = debt_contract._issue(
            args=["bob", 50, 0.0, 100],
            invoker_id="alice"
        )
        debt_id = issue_result["debt_id"]
        debt_contract._accept(args=[debt_id], invoker_id="bob")

        # Repay full amount
        result = debt_contract._repay(
            args=[debt_id, 50],
            invoker_id="alice"
        )

        assert result["success"] is True
        assert result["status"] == "paid"
        assert result["remaining"] == 0

    def test_collect_after_due_tick(
        self, debt_contract: GenesisDebtContract, ledger: Ledger
    ) -> None:
        """Creditor can collect after due tick."""
        # Issue and accept debt
        issue_result = debt_contract._issue(
            args=["bob", 30, 0.0, 5],  # Due at tick 5
            invoker_id="alice"
        )
        debt_id = issue_result["debt_id"]
        debt_contract._accept(args=[debt_id], invoker_id="bob")

        # Cannot collect before due
        result = debt_contract._collect(args=[debt_id], invoker_id="bob")
        assert result["success"] is False
        assert "not yet due" in result["error"]

        # Advance to after due tick
        debt_contract.set_tick(10)

        # Now collection works
        result = debt_contract._collect(args=[debt_id], invoker_id="bob")
        assert result["success"] is True
        assert result["collected"] == 30
        assert result["status"] == "paid"

    def test_collect_partial_when_insufficient(
        self, debt_contract: GenesisDebtContract, ledger: Ledger
    ) -> None:
        """Partial collection when debtor has some but not all scrip."""
        # Reduce alice's balance
        ledger.transfer_scrip("alice", "charlie", 80)  # Alice has 20
        assert ledger.get_scrip("alice") == 20

        # Issue and accept debt
        issue_result = debt_contract._issue(
            args=["bob", 50, 0.0, 5],
            invoker_id="alice"
        )
        debt_id = issue_result["debt_id"]
        debt_contract._accept(args=[debt_id], invoker_id="bob")

        # Advance past due
        debt_contract.set_tick(10)

        # Partial collection
        result = debt_contract._collect(args=[debt_id], invoker_id="bob")
        assert result["success"] is True
        assert result["collected"] == 20
        assert result["remaining"] == 30
        assert result["status"] == "active"

    def test_collect_fails_when_broke(
        self, debt_contract: GenesisDebtContract, ledger: Ledger
    ) -> None:
        """Collection fails and marks default when debtor is broke."""
        # Empty alice's balance
        ledger.transfer_scrip("alice", "charlie", 100)
        assert ledger.get_scrip("alice") == 0

        # Issue and accept
        issue_result = debt_contract._issue(
            args=["bob", 50, 0.0, 5],
            invoker_id="alice"
        )
        debt_id = issue_result["debt_id"]
        debt_contract._accept(args=[debt_id], invoker_id="bob")

        # Advance past due
        debt_contract.set_tick(10)

        # Collection fails, marks as defaulted
        result = debt_contract._collect(args=[debt_id], invoker_id="bob")
        assert result["success"] is False
        assert result["status"] == "defaulted"
        assert "no scrip" in result["error"].lower()

    def test_transfer_creditor_sells_debt(
        self, debt_contract: GenesisDebtContract
    ) -> None:
        """Creditor can transfer rights to another principal."""
        # Issue and accept
        issue_result = debt_contract._issue(
            args=["bob", 50, 0.0, 100],
            invoker_id="alice"
        )
        debt_id = issue_result["debt_id"]
        debt_contract._accept(args=[debt_id], invoker_id="bob")

        # Bob sells debt to charlie
        result = debt_contract._transfer_creditor(
            args=[debt_id, "charlie"],
            invoker_id="bob"
        )

        assert result["success"] is True
        assert result["old_creditor"] == "bob"
        assert result["new_creditor"] == "charlie"

        # Charlie is now the creditor
        check = debt_contract._check(args=[debt_id], invoker_id="anyone")
        assert check["debt"]["creditor_id"] == "charlie"

    def test_list_debts_for_principal(
        self, debt_contract: GenesisDebtContract
    ) -> None:
        """List debts filters by principal."""
        # Create multiple debts
        debt_contract._issue(args=["bob", 10, 0.0, 100], invoker_id="alice")
        debt_contract._issue(args=["charlie", 20, 0.0, 100], invoker_id="alice")
        debt_contract._issue(args=["alice", 30, 0.0, 100], invoker_id="bob")

        # Alice should see 3 debts (2 as debtor, 1 as creditor)
        result = debt_contract._list_debts(args=["alice"], invoker_id="anyone")
        assert result["success"] is True
        assert result["count"] == 3

        # Bob should see 2 debts
        result = debt_contract._list_debts(args=["bob"], invoker_id="anyone")
        assert result["count"] == 2

    def test_interest_accrues_over_time(
        self, debt_contract: GenesisDebtContract, ledger: Ledger
    ) -> None:
        """Interest accrues based on ticks elapsed."""
        # Issue debt with 10% per tick interest
        issue_result = debt_contract._issue(
            args=["bob", 100, 0.1, 50],  # 10% per tick
            invoker_id="alice"
        )
        debt_id = issue_result["debt_id"]
        debt_contract._accept(args=[debt_id], invoker_id="bob")

        # Initially owes 100
        check = debt_contract._check(args=[debt_id], invoker_id="alice")
        assert check["debt"]["current_owed"] == 100

        # After 5 ticks: 100 + (100 * 0.1 * 5) = 150
        debt_contract.set_tick(5)
        check = debt_contract._check(args=[debt_id], invoker_id="alice")
        assert check["debt"]["current_owed"] == 150

        # After 10 ticks: 100 + (100 * 0.1 * 10) = 200
        debt_contract.set_tick(10)
        check = debt_contract._check(args=[debt_id], invoker_id="alice")
        assert check["debt"]["current_owed"] == 200
