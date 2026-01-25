"""Unit tests for GenesisDebtContract.

Tests the non-privileged debt contract example that demonstrates
credit/lending patterns without kernel-level enforcement.

Plan #167: Updated to use time-based scheduling instead of ticks.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.world.genesis import GenesisDebtContract
from src.world.ledger import Ledger


def make_now() -> datetime:
    """Create a consistent 'now' for testing."""
    return datetime(2026, 1, 24, 12, 0, 0, tzinfo=timezone.utc)


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
        return GenesisDebtContract(ledger=ledger)

    def test_issue_debt_creates_pending_debt(
        self, debt_contract: GenesisDebtContract
    ) -> None:
        """Issuing debt creates a pending record."""
        result = debt_contract._issue(
            args=["bob", 50, 0.01, 86400],  # creditor, principal, rate_per_day, due_in_seconds
            invoker_id="alice"  # alice becomes debtor
        )

        assert result["success"] is True
        assert "debt_id" in result
        assert result["debtor"] == "alice"
        assert result["creditor"] == "bob"
        assert result["principal"] == 50
        assert "due_at" in result  # Time-based (Plan #167)

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
            args=["bob", -10, 0.01, 86400],
            invoker_id="alice"
        )
        assert result["success"] is False
        assert "positive integer" in result["error"]

        # Invalid interest rate
        result = debt_contract._issue(
            args=["bob", 50, -0.1, 86400],
            invoker_id="alice"
        )
        assert result["success"] is False
        assert "non-negative" in result["error"]

        # Due in past (negative seconds)
        result = debt_contract._issue(
            args=["bob", 50, 0.01, -100],
            invoker_id="alice"
        )
        assert result["success"] is False
        assert "positive" in result["error"].lower()

        # Cannot issue to self
        result = debt_contract._issue(
            args=["alice", 50, 0.01, 86400],
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
            args=["bob", 50, 0.01, 86400],
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
            args=["bob", 50, 0.01, 86400],
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
        # Issue and accept debt (no interest for simplicity)
        issue_result = debt_contract._issue(
            args=["bob", 50, 0.0, 86400],
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
            args=["bob", 50, 0.0, 86400],
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

    def test_collect_after_due_time(
        self, debt_contract: GenesisDebtContract, ledger: Ledger
    ) -> None:
        """Creditor can collect after due time (Plan #167: time-based)."""
        now = make_now()

        # Mock _now() method
        with patch.object(debt_contract, "_now", return_value=now):
            # Issue debt due in 1 hour (3600 seconds)
            issue_result = debt_contract._issue(
                args=["bob", 30, 0.0, 3600],
                invoker_id="alice"
            )
            debt_id = issue_result["debt_id"]
            debt_contract._accept(args=[debt_id], invoker_id="bob")

            # Cannot collect before due
            result = debt_contract._collect(args=[debt_id], invoker_id="bob")
            assert result["success"] is False
            assert "not yet due" in result["error"]

        # Advance time past due
        with patch.object(debt_contract, "_now", return_value=now + timedelta(hours=2)):
            # Now collection works
            result = debt_contract._collect(args=[debt_id], invoker_id="bob")
            assert result["success"] is True
            assert result["collected"] == 30
            assert result["status"] == "paid"

    def test_collect_partial_when_insufficient(
        self, debt_contract: GenesisDebtContract, ledger: Ledger
    ) -> None:
        """Partial collection when debtor has some but not all scrip."""
        now = make_now()

        # Reduce alice's balance
        ledger.transfer_scrip("alice", "charlie", 80)  # Alice has 20
        assert ledger.get_scrip("alice") == 20

        with patch.object(debt_contract, "_now", return_value=now):
            # Issue and accept debt
            issue_result = debt_contract._issue(
                args=["bob", 50, 0.0, 3600],
                invoker_id="alice"
            )
            debt_id = issue_result["debt_id"]
            debt_contract._accept(args=[debt_id], invoker_id="bob")

        # Advance past due
        with patch.object(debt_contract, "_now", return_value=now + timedelta(hours=2)):
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
        now = make_now()

        # Empty alice's balance
        ledger.transfer_scrip("alice", "charlie", 100)
        assert ledger.get_scrip("alice") == 0

        with patch.object(debt_contract, "_now", return_value=now):
            # Issue and accept
            issue_result = debt_contract._issue(
                args=["bob", 50, 0.0, 3600],
                invoker_id="alice"
            )
            debt_id = issue_result["debt_id"]
            debt_contract._accept(args=[debt_id], invoker_id="bob")

        # Advance past due
        with patch.object(debt_contract, "_now", return_value=now + timedelta(hours=2)):
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
            args=["bob", 50, 0.0, 86400],
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
        debt_contract._issue(args=["bob", 10, 0.0, 86400], invoker_id="alice")
        debt_contract._issue(args=["charlie", 20, 0.0, 86400], invoker_id="alice")
        debt_contract._issue(args=["alice", 30, 0.0, 86400], invoker_id="bob")

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
        """Interest accrues based on time elapsed (Plan #167)."""
        now = make_now()

        with patch.object(debt_contract, "_now", return_value=now):
            # Issue debt with 10% per day interest rate
            issue_result = debt_contract._issue(
                args=["bob", 100, 0.1, 86400 * 10],  # 10% per day, due in 10 days
                invoker_id="alice"
            )
            debt_id = issue_result["debt_id"]
            debt_contract._accept(args=[debt_id], invoker_id="bob")

            # Initially owes 100 (no time elapsed)
            check = debt_contract._check(args=[debt_id], invoker_id="alice")
            assert check["debt"]["current_owed"] == 100

        # After 1 day: 100 + (100 * 0.1 * 1) = 110
        with patch.object(debt_contract, "_now", return_value=now + timedelta(days=1)):
            check = debt_contract._check(args=[debt_id], invoker_id="alice")
            assert check["debt"]["current_owed"] == 110

        # After 5 days: 100 + (100 * 0.1 * 5) = 150
        with patch.object(debt_contract, "_now", return_value=now + timedelta(days=5)):
            check = debt_contract._check(args=[debt_id], invoker_id="alice")
            assert check["debt"]["current_owed"] == 150

        # After 10 days: 100 + (100 * 0.1 * 10) = 200
        with patch.object(debt_contract, "_now", return_value=now + timedelta(days=10)):
            check = debt_contract._check(args=[debt_id], invoker_id="alice")
            assert check["debt"]["current_owed"] == 200

    def test_check_returns_time_fields(
        self, debt_contract: GenesisDebtContract
    ) -> None:
        """Check returns time-based fields (Plan #167)."""
        issue_result = debt_contract._issue(
            args=["bob", 50, 0.01, 86400],
            invoker_id="alice"
        )
        debt_id = issue_result["debt_id"]
        debt_contract._accept(args=[debt_id], invoker_id="bob")

        check = debt_contract._check(args=[debt_id], invoker_id="alice")
        debt = check["debt"]

        # Should have time-based fields
        assert "created_at" in debt
        assert "due_at" in debt
        assert "rate_per_day" in debt

        # Should NOT have tick-based fields
        assert "due_tick" not in debt
        assert "created_tick" not in debt
