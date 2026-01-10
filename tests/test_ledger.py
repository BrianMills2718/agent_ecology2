"""Unit tests for the Ledger class."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from world.ledger import Ledger

import pytest


@pytest.fixture
def ledger() -> Ledger:
    """Create a fresh Ledger instance for each test."""
    return Ledger()


@pytest.fixture
def ledger_with_agents(ledger: Ledger) -> Ledger:
    """Create a Ledger with two agents initialized."""
    ledger.create_principal("agent_a", starting_scrip=100, starting_compute=500)
    ledger.create_principal("agent_b", starting_scrip=50, starting_compute=300)
    return ledger


class TestInitialBalances:
    """Tests for agent initialization with correct balances."""

    def test_initial_balances(self, ledger: Ledger) -> None:
        """Verify agents start with correct scrip and compute."""
        ledger.create_principal("agent_1", starting_scrip=100, starting_compute=500)

        assert ledger.get_scrip("agent_1") == 100
        assert ledger.get_compute("agent_1") == 500

    def test_initial_balances_default_compute(self, ledger: Ledger) -> None:
        """Verify agents can be created with default compute of 0."""
        ledger.create_principal("agent_1", starting_scrip=100)

        assert ledger.get_scrip("agent_1") == 100
        assert ledger.get_compute("agent_1") == 0

    def test_initial_balances_multiple_agents(
        self, ledger_with_agents: Ledger
    ) -> None:
        """Verify multiple agents have independent balances."""
        assert ledger_with_agents.get_scrip("agent_a") == 100
        assert ledger_with_agents.get_compute("agent_a") == 500
        assert ledger_with_agents.get_scrip("agent_b") == 50
        assert ledger_with_agents.get_compute("agent_b") == 300


class TestGetScrip:
    """Tests for get_scrip method."""

    def test_get_scrip(self, ledger_with_agents: Ledger) -> None:
        """Test get_scrip returns correct value."""
        assert ledger_with_agents.get_scrip("agent_a") == 100
        assert ledger_with_agents.get_scrip("agent_b") == 50

    def test_get_scrip_unknown_agent(self, ledger: Ledger) -> None:
        """Test get_scrip returns 0 for unknown agent."""
        assert ledger.get_scrip("unknown_agent") == 0


class TestGetCompute:
    """Tests for get_compute method."""

    def test_get_compute(self, ledger_with_agents: Ledger) -> None:
        """Test get_compute returns correct value."""
        assert ledger_with_agents.get_compute("agent_a") == 500
        assert ledger_with_agents.get_compute("agent_b") == 300

    def test_get_compute_unknown_agent(self, ledger: Ledger) -> None:
        """Test get_compute returns 0 for unknown agent."""
        assert ledger.get_compute("unknown_agent") == 0


class TestTransferScrip:
    """Tests for scrip transfer between agents."""

    def test_transfer_scrip_success(self, ledger_with_agents: Ledger) -> None:
        """Transfer scrip between agents successfully."""
        result = ledger_with_agents.transfer_scrip("agent_a", "agent_b", 30)

        assert result is True
        assert ledger_with_agents.get_scrip("agent_a") == 70
        assert ledger_with_agents.get_scrip("agent_b") == 80

    def test_transfer_scrip_insufficient(self, ledger_with_agents: Ledger) -> None:
        """Transfer fails with insufficient funds."""
        result = ledger_with_agents.transfer_scrip("agent_a", "agent_b", 150)

        assert result is False
        # Balances should remain unchanged
        assert ledger_with_agents.get_scrip("agent_a") == 100
        assert ledger_with_agents.get_scrip("agent_b") == 50

    def test_transfer_scrip_zero_amount(self, ledger_with_agents: Ledger) -> None:
        """Transfer fails with zero amount."""
        result = ledger_with_agents.transfer_scrip("agent_a", "agent_b", 0)

        assert result is False
        assert ledger_with_agents.get_scrip("agent_a") == 100
        assert ledger_with_agents.get_scrip("agent_b") == 50

    def test_transfer_scrip_negative_amount(self, ledger_with_agents: Ledger) -> None:
        """Transfer fails with negative amount."""
        result = ledger_with_agents.transfer_scrip("agent_a", "agent_b", -10)

        assert result is False
        assert ledger_with_agents.get_scrip("agent_a") == 100
        assert ledger_with_agents.get_scrip("agent_b") == 50

    def test_transfer_scrip_to_nonexistent_recipient(
        self, ledger_with_agents: Ledger
    ) -> None:
        """Transfer fails when recipient doesn't exist."""
        result = ledger_with_agents.transfer_scrip("agent_a", "nonexistent", 30)

        assert result is False
        assert ledger_with_agents.get_scrip("agent_a") == 100


class TestDeductActionCost:
    """Tests for deducting action costs (scrip)."""

    def test_deduct_action_cost_success(self, ledger_with_agents: Ledger) -> None:
        """Deduct action cost from scrip successfully."""
        result = ledger_with_agents.deduct_scrip("agent_a", 25)

        assert result is True
        assert ledger_with_agents.get_scrip("agent_a") == 75

    def test_deduct_action_cost_insufficient(self, ledger_with_agents: Ledger) -> None:
        """Fails when not enough scrip for action cost."""
        result = ledger_with_agents.deduct_scrip("agent_a", 150)

        assert result is False
        assert ledger_with_agents.get_scrip("agent_a") == 100

    def test_deduct_action_cost_exact_balance(self, ledger_with_agents: Ledger) -> None:
        """Deduct exact balance succeeds."""
        result = ledger_with_agents.deduct_scrip("agent_a", 100)

        assert result is True
        assert ledger_with_agents.get_scrip("agent_a") == 0


class TestDeductThinkingCost:
    """Tests for deducting thinking (LLM token) costs from compute."""

    def test_deduct_thinking_cost(self, ledger_with_agents: Ledger) -> None:
        """Deduct compute for LLM tokens successfully."""
        # Using rates: 1.0 per 1K input, 2.0 per 1K output
        # 1000 input tokens = 1.0, 500 output tokens = 1.0, total = 2
        success, cost = ledger_with_agents.deduct_thinking_cost(
            "agent_a",
            input_tokens=1000,
            output_tokens=500,
            rate_input=1.0,
            rate_output=2.0,
        )

        assert success is True
        assert cost == 2
        assert ledger_with_agents.get_compute("agent_a") == 498

    def test_deduct_thinking_cost_rounds_up(self, ledger_with_agents: Ledger) -> None:
        """Thinking cost rounds up to nearest integer."""
        # 100 input tokens at 1.0 rate = 0.1, should round up to 1
        success, cost = ledger_with_agents.deduct_thinking_cost(
            "agent_a",
            input_tokens=100,
            output_tokens=0,
            rate_input=1.0,
            rate_output=1.0,
        )

        assert success is True
        assert cost == 1
        assert ledger_with_agents.get_compute("agent_a") == 499

    def test_deduct_thinking_cost_insufficient(
        self, ledger_with_agents: Ledger
    ) -> None:
        """Fails when not enough compute for thinking."""
        # Request more compute than available (500)
        # 100000 input tokens at 10.0 rate = 1000 compute units
        success, cost = ledger_with_agents.deduct_thinking_cost(
            "agent_a",
            input_tokens=100000,
            output_tokens=0,
            rate_input=10.0,
            rate_output=1.0,
        )

        assert success is False
        assert cost == 1000
        # Compute should remain unchanged
        assert ledger_with_agents.get_compute("agent_a") == 500


class TestResetCompute:
    """Tests for resetting compute each tick."""

    def test_reset_compute(self, ledger_with_agents: Ledger) -> None:
        """Verify compute resets each tick."""
        # First spend some compute
        ledger_with_agents.spend_compute("agent_a", 200)
        assert ledger_with_agents.get_compute("agent_a") == 300

        # Reset compute to quota
        ledger_with_agents.reset_compute("agent_a", 1000)

        assert ledger_with_agents.get_compute("agent_a") == 1000

    def test_reset_compute_to_lower_value(self, ledger_with_agents: Ledger) -> None:
        """Reset compute can set to lower value than current."""
        assert ledger_with_agents.get_compute("agent_a") == 500

        ledger_with_agents.reset_compute("agent_a", 100)

        assert ledger_with_agents.get_compute("agent_a") == 100


class TestMintScrip:
    """Tests for minting new scrip (oracle rewards)."""

    def test_mint_scrip(self, ledger_with_agents: Ledger) -> None:
        """Test minting new scrip (oracle rewards)."""
        initial_scrip = ledger_with_agents.get_scrip("agent_a")

        ledger_with_agents.credit_scrip("agent_a", 50)

        assert ledger_with_agents.get_scrip("agent_a") == initial_scrip + 50

    def test_mint_scrip_to_new_agent(self, ledger: Ledger) -> None:
        """Test minting scrip to a new agent creates them."""
        ledger.credit_scrip("new_agent", 100)

        assert ledger.get_scrip("new_agent") == 100

    def test_mint_scrip_multiple_times(self, ledger_with_agents: Ledger) -> None:
        """Test minting scrip accumulates correctly."""
        ledger_with_agents.credit_scrip("agent_a", 25)
        ledger_with_agents.credit_scrip("agent_a", 25)
        ledger_with_agents.credit_scrip("agent_a", 50)

        assert ledger_with_agents.get_scrip("agent_a") == 200  # 100 + 25 + 25 + 50


class TestCanAfford:
    """Tests for checking affordability."""

    def test_can_afford_scrip(self, ledger_with_agents: Ledger) -> None:
        """Test can_afford_scrip returns correct value."""
        assert ledger_with_agents.can_afford_scrip("agent_a", 50) is True
        assert ledger_with_agents.can_afford_scrip("agent_a", 100) is True
        assert ledger_with_agents.can_afford_scrip("agent_a", 101) is False

    def test_can_spend_compute(self, ledger_with_agents: Ledger) -> None:
        """Test can_spend_compute returns correct value."""
        assert ledger_with_agents.can_spend_compute("agent_a", 250) is True
        assert ledger_with_agents.can_spend_compute("agent_a", 500) is True
        assert ledger_with_agents.can_spend_compute("agent_a", 501) is False


class TestGetAllBalances:
    """Tests for reporting methods."""

    def test_get_all_balances(self, ledger_with_agents: Ledger) -> None:
        """Test get_all_balances returns complete snapshot."""
        balances = ledger_with_agents.get_all_balances()

        assert "agent_a" in balances
        assert "agent_b" in balances
        assert balances["agent_a"]["scrip"] == 100
        assert balances["agent_a"]["compute"] == 500
        assert balances["agent_b"]["scrip"] == 50
        assert balances["agent_b"]["compute"] == 300

    def test_get_all_scrip(self, ledger_with_agents: Ledger) -> None:
        """Test get_all_scrip returns scrip snapshot."""
        scrip = ledger_with_agents.get_all_scrip()

        assert scrip == {"agent_a": 100, "agent_b": 50}

    def test_get_all_compute(self, ledger_with_agents: Ledger) -> None:
        """Test get_all_compute returns compute snapshot."""
        compute = ledger_with_agents.get_all_compute()

        assert compute == {"agent_a": 500, "agent_b": 300}
