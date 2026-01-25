"""Integration tests for genesis_debt_contract - non-privileged debt/credit patterns.

Plan #167: Updated to use time-based scheduling instead of ticks.
"""

import pytest
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.world.artifacts import ArtifactStore
from src.world.ledger import Ledger
from src.world.genesis import GenesisDebtContract


def make_now() -> datetime:
    """Create a consistent 'now' for testing."""
    return datetime(2026, 1, 24, 12, 0, 0, tzinfo=timezone.utc)


class TestDebtContractLifecycle:
    """Test complete debt contract lifecycle."""

    def test_full_loan_cycle(self) -> None:
        """Complete loan cycle: issue -> accept -> repay -> paid."""
        ledger = Ledger()
        ledger.create_principal("alice", starting_scrip=100)
        ledger.create_principal("bob", starting_scrip=200)

        contract = GenesisDebtContract(ledger=ledger)

        # Alice requests loan from Bob (due in 1 hour)
        issue_result = contract._issue(
            args=["bob", 50, 0.0, 3600],  # creditor, principal, rate_per_day, due_in_seconds
            invoker_id="alice"
        )
        assert issue_result["success"] is True
        debt_id = issue_result["debt_id"]

        # Bob accepts the loan
        accept_result = contract._accept(args=[debt_id], invoker_id="bob")
        assert accept_result["success"] is True

        # Alice repays in full
        repay_result = contract._repay(args=[debt_id, 50], invoker_id="alice")
        assert repay_result["success"] is True
        assert repay_result["status"] == "paid"

        # Verify final balances
        assert ledger.get_scrip("alice") == 50  # 100 - 50 repaid
        assert ledger.get_scrip("bob") == 250  # 200 + 50 repaid

    def test_loan_with_interest(self) -> None:
        """Loan with interest requires more to repay."""
        ledger = Ledger()
        ledger.create_principal("borrower", starting_scrip=150)
        ledger.create_principal("lender", starting_scrip=100)

        contract = GenesisDebtContract(ledger=ledger)
        now = make_now()

        with patch.object(contract, "_now", return_value=now):
            # Borrower takes 100 scrip loan at 10% per day
            issue = contract._issue(
                args=["lender", 100, 0.1, 86400 * 10],  # 10% per day, due in 10 days
                invoker_id="borrower"
            )
            debt_id = issue["debt_id"]
            contract._accept(args=[debt_id], invoker_id="lender")

        # After 5 days, interest accrued: 100 + (100 * 0.1 * 5) = 150
        with patch.object(contract, "_now", return_value=now + timedelta(days=5)):
            check = contract._check(args=[debt_id], invoker_id="borrower")
            assert check["debt"]["current_owed"] == 150

            # Repay full amount with interest
            repay = contract._repay(args=[debt_id, 150], invoker_id="borrower")
            assert repay["success"] is True
            assert repay["status"] == "paid"

        # Final balances: borrower paid 150, lender received 150
        assert ledger.get_scrip("borrower") == 0
        assert ledger.get_scrip("lender") == 250

    def test_partial_repayment_cycle(self) -> None:
        """Multiple partial repayments eventually pay off debt."""
        ledger = Ledger()
        ledger.create_principal("debtor", starting_scrip=100)
        ledger.create_principal("creditor", starting_scrip=50)

        contract = GenesisDebtContract(ledger=ledger)

        # Issue 60 scrip debt (due in 1 day, no interest)
        issue = contract._issue(
            args=["creditor", 60, 0.0, 86400],
            invoker_id="debtor"
        )
        debt_id = issue["debt_id"]
        contract._accept(args=[debt_id], invoker_id="creditor")

        # First payment: 20
        result1 = contract._repay(args=[debt_id, 20], invoker_id="debtor")
        assert result1["remaining"] == 40
        assert result1["success"] is True

        # Second payment: 20
        result2 = contract._repay(args=[debt_id, 20], invoker_id="debtor")
        assert result2["remaining"] == 20
        assert result2["success"] is True

        # Final payment: 20
        result3 = contract._repay(args=[debt_id, 20], invoker_id="debtor")
        assert result3["remaining"] == 0
        assert result3["status"] == "paid"


class TestDebtCollection:
    """Test creditor collection after due time."""

    def test_forced_collection_after_due(self) -> None:
        """Creditor can collect after due time."""
        ledger = Ledger()
        ledger.create_principal("debtor", starting_scrip=100)
        ledger.create_principal("creditor", starting_scrip=50)

        contract = GenesisDebtContract(ledger=ledger)
        now = make_now()

        with patch.object(contract, "_now", return_value=now):
            # Issue debt due in 1 hour
            issue = contract._issue(
                args=["creditor", 40, 0.0, 3600],  # due in 1 hour
                invoker_id="debtor"
            )
            debt_id = issue["debt_id"]
            contract._accept(args=[debt_id], invoker_id="creditor")

            # Cannot collect before due
            collect = contract._collect(args=[debt_id], invoker_id="creditor")
            assert collect["success"] is False

        # Advance past due time
        with patch.object(contract, "_now", return_value=now + timedelta(hours=2)):
            # Now collection works
            collect = contract._collect(args=[debt_id], invoker_id="creditor")
            assert collect["success"] is True
            assert collect["collected"] == 40
            assert ledger.get_scrip("debtor") == 60
            assert ledger.get_scrip("creditor") == 90

    def test_default_on_zero_balance(self) -> None:
        """Default when debtor has no scrip."""
        ledger = Ledger()
        ledger.create_principal("broke", starting_scrip=0)
        ledger.create_principal("creditor", starting_scrip=100)

        contract = GenesisDebtContract(ledger=ledger)
        now = make_now()

        with patch.object(contract, "_now", return_value=now):
            # Issue debt (broke somehow got credit without scrip - risky lending!)
            issue = contract._issue(
                args=["creditor", 50, 0.0, 3600],
                invoker_id="broke"
            )
            debt_id = issue["debt_id"]
            contract._accept(args=[debt_id], invoker_id="creditor")

        # Advance past due
        with patch.object(contract, "_now", return_value=now + timedelta(hours=2)):
            # Collection fails - debtor is broke
            collect = contract._collect(args=[debt_id], invoker_id="creditor")
            assert collect["success"] is False
            assert collect["status"] == "defaulted"


class TestDebtTrading:
    """Test debt transfer between creditors."""

    def test_debt_sale_to_new_creditor(self) -> None:
        """Creditor can sell debt rights to another principal."""
        ledger = Ledger()
        ledger.create_principal("debtor", starting_scrip=100)
        ledger.create_principal("original_creditor", starting_scrip=50)
        ledger.create_principal("debt_buyer", starting_scrip=50)

        contract = GenesisDebtContract(ledger=ledger)

        # Issue and accept debt
        issue = contract._issue(
            args=["original_creditor", 30, 0.0, 86400],
            invoker_id="debtor"
        )
        debt_id = issue["debt_id"]
        contract._accept(args=[debt_id], invoker_id="original_creditor")

        # Original creditor sells debt to debt_buyer
        transfer = contract._transfer_creditor(
            args=[debt_id, "debt_buyer"],
            invoker_id="original_creditor"
        )
        assert transfer["success"] is True
        assert transfer["new_creditor"] == "debt_buyer"

        # When debtor repays, payment goes to new creditor
        repay = contract._repay(args=[debt_id, 30], invoker_id="debtor")
        assert repay["success"] is True

        # Verify: debt_buyer received payment, not original_creditor
        assert ledger.get_scrip("debt_buyer") == 80  # 50 + 30
        assert ledger.get_scrip("original_creditor") == 50  # unchanged

    def test_only_creditor_can_transfer(self) -> None:
        """Only current creditor can transfer debt rights."""
        ledger = Ledger()
        ledger.create_principal("debtor", starting_scrip=100)
        ledger.create_principal("creditor", starting_scrip=50)
        ledger.create_principal("attacker", starting_scrip=50)

        contract = GenesisDebtContract(ledger=ledger)

        issue = contract._issue(
            args=["creditor", 30, 0.0, 86400],
            invoker_id="debtor"
        )
        debt_id = issue["debt_id"]
        contract._accept(args=[debt_id], invoker_id="creditor")

        # Attacker tries to steal debt rights
        transfer = contract._transfer_creditor(
            args=[debt_id, "attacker"],
            invoker_id="attacker"
        )
        assert transfer["success"] is False
        assert "only the creditor" in transfer["error"].lower()


class TestDebtContractWorldIntegration:
    """Integration tests for debt contract in World context."""

    def test_debt_contract_created_in_world(self) -> None:
        """Debt contract is created as part of genesis artifacts."""
        from src.world.world import World

        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            log_file = f.name

        config = {
            'world': {},
            'costs': {'actions': {}, 'default': 1},
            'logging': {'output_file': log_file},
            'principals': [{'id': 'alice', 'starting_scrip': 100}],
            'rate_limiting': {'enabled': True, 'window_seconds': 60.0, 'resources': {'llm_tokens': {'max_per_window': 1000}}}
        }

        world = World(config)

        assert "genesis_debt_contract" in world.genesis_artifacts
        debt_contract = world.genesis_artifacts["genesis_debt_contract"]
        assert isinstance(debt_contract, GenesisDebtContract)

    def test_debt_lifecycle_via_world_actions(self) -> None:
        """Complete debt lifecycle through World invoke actions."""
        from src.world.world import World
        from src.world.actions import InvokeArtifactIntent

        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            log_file = f.name

        config = {
            'world': {},
            'costs': {'actions': {}, 'default': 1},
            'logging': {'output_file': log_file},
            'principals': [
                {'id': 'borrower', 'starting_scrip': 100},
                {'id': 'lender', 'starting_scrip': 200}
            ],
            'rate_limiting': {'enabled': True, 'window_seconds': 60.0, 'resources': {'llm_tokens': {'max_per_window': 1000}}}
        }

        world = World(config)
        world.advance_tick()

        # 1. Borrower issues debt request to lender (due in 1 hour)
        issue = InvokeArtifactIntent(
            "borrower", "genesis_debt_contract", "issue",
            ["lender", 50, 0.0, 3600]  # creditor, principal, rate_per_day, due_in_seconds
        )
        result = world.execute_action(issue)
        assert result.success, result.message
        debt_id = result.data.get("debt_id") if result.data else None
        assert debt_id is not None

        # 2. Lender accepts
        accept = InvokeArtifactIntent(
            "lender", "genesis_debt_contract", "accept",
            [debt_id]
        )
        result = world.execute_action(accept)
        assert result.success, result.message

        # 3. Check debt status
        check = InvokeArtifactIntent(
            "borrower", "genesis_debt_contract", "check",
            [debt_id]
        )
        result = world.execute_action(check)
        assert result.success
        assert result.data["debt"]["status"] == "active"

        # 4. Borrower repays
        repay = InvokeArtifactIntent(
            "borrower", "genesis_debt_contract", "repay",
            [debt_id, 50]
        )
        result = world.execute_action(repay)
        assert result.success, result.message
        assert result.data["status"] == "paid"

        # Verify final balances
        assert world.ledger.get_scrip("borrower") == 49  # 100 - 50 - 1 method fee
        assert world.ledger.get_scrip("lender") == 250  # 200 + 50

    def test_debt_contract_uses_real_time(self) -> None:
        """Plan #167: Debt contract uses real time, not ticks."""
        from src.world.world import World

        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            log_file = f.name

        config = {
            'world': {},
            'costs': {'actions': {}, 'default': 1},
            'logging': {'output_file': log_file},
            'principals': [
                {'id': 'debtor', 'starting_scrip': 100},
                {'id': 'creditor', 'starting_scrip': 100}
            ],
            'rate_limiting': {'enabled': True, 'window_seconds': 60.0, 'resources': {'llm_tokens': {'max_per_window': 1000}}}
        }

        world = World(config)

        # Get debt contract
        debt_contract = world.genesis_artifacts["genesis_debt_contract"]
        assert isinstance(debt_contract, GenesisDebtContract)

        # Verify it has time-based method
        assert hasattr(debt_contract, "_now")
        now = debt_contract._now()
        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc

        # Verify set_tick is a no-op (for backwards compatibility)
        # This should not raise, just do nothing
        debt_contract.set_tick(100)


class TestMultipleDebts:
    """Test scenarios with multiple concurrent debts."""

    def test_multiple_debts_from_same_debtor(self) -> None:
        """Debtor can have multiple debts to different creditors."""
        ledger = Ledger()
        ledger.create_principal("debtor", starting_scrip=200)
        ledger.create_principal("creditor_a", starting_scrip=100)
        ledger.create_principal("creditor_b", starting_scrip=100)

        contract = GenesisDebtContract(ledger=ledger)

        # Debt to creditor A
        issue_a = contract._issue(
            args=["creditor_a", 30, 0.0, 86400],
            invoker_id="debtor"
        )
        debt_a = issue_a["debt_id"]
        contract._accept(args=[debt_a], invoker_id="creditor_a")

        # Debt to creditor B
        issue_b = contract._issue(
            args=["creditor_b", 50, 0.0, 86400],
            invoker_id="debtor"
        )
        debt_b = issue_b["debt_id"]
        contract._accept(args=[debt_b], invoker_id="creditor_b")

        # List all debts for debtor
        list_result = contract._list_debts(args=["debtor"], invoker_id="anyone")
        assert list_result["count"] == 2

        # Repay each separately
        contract._repay(args=[debt_a, 30], invoker_id="debtor")
        contract._repay(args=[debt_b, 50], invoker_id="debtor")

        # Verify final state
        assert ledger.get_scrip("debtor") == 120
        assert ledger.get_scrip("creditor_a") == 130
        assert ledger.get_scrip("creditor_b") == 150

    def test_creditor_with_multiple_debtors(self) -> None:
        """Creditor can have loans to multiple debtors."""
        ledger = Ledger()
        ledger.create_principal("debtor_a", starting_scrip=100)
        ledger.create_principal("debtor_b", starting_scrip=100)
        ledger.create_principal("bank", starting_scrip=500)

        contract = GenesisDebtContract(ledger=ledger)

        # Debtor A borrows from bank
        issue_a = contract._issue(
            args=["bank", 40, 0.0, 86400],
            invoker_id="debtor_a"
        )
        debt_a = issue_a["debt_id"]
        contract._accept(args=[debt_a], invoker_id="bank")

        # Debtor B borrows from bank
        issue_b = contract._issue(
            args=["bank", 60, 0.0, 86400],
            invoker_id="debtor_b"
        )
        debt_b = issue_b["debt_id"]
        contract._accept(args=[debt_b], invoker_id="bank")

        # Bank's view: 2 debts as creditor
        list_result = contract._list_debts(args=["bank"], invoker_id="bank")
        assert list_result["count"] == 2

        # Both repay
        contract._repay(args=[debt_a, 40], invoker_id="debtor_a")
        contract._repay(args=[debt_b, 60], invoker_id="debtor_b")

        # Bank received all payments
        assert ledger.get_scrip("bank") == 600  # 500 + 40 + 60
