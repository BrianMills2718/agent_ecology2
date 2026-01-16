"""Unit tests for the Ledger class."""

from pathlib import Path

import pytest

from src.world.ledger import Ledger


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

    def test_initial_balances_zero_values(self, ledger: Ledger) -> None:
        """Verify agents can be created with 0 starting scrip and compute.

        This is used when spawning principals that start with nothing.
        """
        ledger.create_principal("spawned_agent", starting_scrip=0, starting_compute=0)

        assert ledger.get_scrip("spawned_agent") == 0
        assert ledger.get_compute("spawned_agent") == 0
        # Verify the agent exists in the ledger
        assert "spawned_agent" in ledger.get_all_balances()

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

    def test_transfer_scrip_to_nonexistent_recipient_creates_wallet(
        self, ledger_with_agents: Ledger
    ) -> None:
        """Transfer to non-existent recipient auto-creates their wallet (artifact wallets)."""
        result = ledger_with_agents.transfer_scrip("agent_a", "new_contract", 30)

        assert result is True  # Now succeeds - enables artifact wallets
        assert ledger_with_agents.get_scrip("agent_a") == 70
        assert ledger_with_agents.get_scrip("new_contract") == 30


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
    """Tests for minting new scrip (mint rewards)."""

    def test_mint_scrip(self, ledger_with_agents: Ledger) -> None:
        """Test minting new scrip (mint rewards)."""
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


class TestRateTrackerIntegration:
    """Tests for Ledger + RateTracker integration."""

    def test_rate_tracker_disabled_by_default(self) -> None:
        """Rate tracker not used when disabled."""
        ledger = Ledger()
        assert ledger.use_rate_tracker is False
        assert ledger.rate_tracker is None
        # Legacy mode: check_resource_capacity always returns True
        assert ledger.check_resource_capacity("agent1", "llm_calls") is True

    def test_rate_tracker_enabled_from_config(self) -> None:
        """Rate tracker initialized from config."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 60.0,
                "resources": {
                    "llm_calls": {"max_per_window": 100}
                }
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])
        assert ledger.use_rate_tracker is True
        assert ledger.rate_tracker is not None

    def test_rate_tracker_disabled_from_config(self) -> None:
        """Rate tracker not initialized when disabled in config."""
        config = {
            "rate_limiting": {
                "enabled": False,
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])
        assert ledger.use_rate_tracker is False
        assert ledger.rate_tracker is None

    def test_rate_tracker_empty_config(self) -> None:
        """Rate tracker disabled when config section missing."""
        config: dict[str, object] = {}
        ledger = Ledger.from_config(config, ["agent1"])
        assert ledger.use_rate_tracker is False
        assert ledger.rate_tracker is None

    def test_check_capacity_uses_rate_tracker(self) -> None:
        """check_resource_capacity delegates to RateTracker."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "resources": {"llm_calls": {"max_per_window": 10}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Should have capacity initially
        assert ledger.check_resource_capacity("agent1", "llm_calls", 5) is True

        # Consume all capacity
        ledger.consume_resource("agent1", "llm_calls", 10)

        # Should not have capacity anymore
        assert ledger.check_resource_capacity("agent1", "llm_calls", 1) is False

    def test_consume_resource_uses_rate_tracker(self) -> None:
        """consume_resource delegates to RateTracker."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "resources": {"llm_calls": {"max_per_window": 10}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # First consumption should succeed
        assert ledger.consume_resource("agent1", "llm_calls", 5) is True

        # Should have 5 remaining
        assert ledger.get_resource_remaining("agent1", "llm_calls") == 5

        # Consuming 6 should fail
        assert ledger.consume_resource("agent1", "llm_calls", 6) is False

        # Consuming 5 should succeed
        assert ledger.consume_resource("agent1", "llm_calls", 5) is True

        # No capacity remaining
        assert ledger.get_resource_remaining("agent1", "llm_calls") == 0

    def test_get_resource_remaining_uses_rate_tracker(self) -> None:
        """get_resource_remaining delegates to RateTracker."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "resources": {"llm_calls": {"max_per_window": 100}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Initially should have full capacity
        assert ledger.get_resource_remaining("agent1", "llm_calls") == 100

        # Consume some
        ledger.consume_resource("agent1", "llm_calls", 30)

        # Should have 70 remaining
        assert ledger.get_resource_remaining("agent1", "llm_calls") == 70

    def test_legacy_mode_check_capacity_always_true(self) -> None:
        """Legacy mode: check_resource_capacity always returns True."""
        ledger = Ledger()
        # Even with high amount, should return True (legacy mode)
        assert ledger.check_resource_capacity("agent1", "any_resource", 999999) is True

    def test_legacy_mode_consume_always_true(self) -> None:
        """Legacy mode: consume_resource always returns True."""
        ledger = Ledger()
        # Should always succeed in legacy mode
        assert ledger.consume_resource("agent1", "any_resource", 999999) is True

    def test_legacy_mode_remaining_is_infinite(self) -> None:
        """Legacy mode: get_resource_remaining returns infinity."""
        ledger = Ledger()
        assert ledger.get_resource_remaining("agent1", "any_resource") == float("inf")

    def test_legacy_reset_compute_still_works(self) -> None:
        """Legacy tick-based mode unchanged when disabled."""
        ledger = Ledger()
        ledger.create_principal("agent1", starting_scrip=100, starting_compute=500)

        # Spend some compute
        ledger.spend_compute("agent1", 200)
        assert ledger.get_compute("agent1") == 300

        # Reset should work
        ledger.reset_compute("agent1", 1000)
        assert ledger.get_compute("agent1") == 1000

    def test_reset_compute_with_rate_tracker_enabled(self) -> None:
        """reset_compute sets tick balance but get_compute returns RateTracker capacity.

        When rate_limiting is enabled, get_compute is mode-aware and returns
        the RateTracker remaining capacity, not the tick-based balance.
        """
        config = {
            "rate_limiting": {
                "enabled": True,
                "resources": {"llm_tokens": {"max_per_window": 1000}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])
        ledger.create_principal("agent1", starting_scrip=100, starting_compute=500)

        # get_compute returns RateTracker capacity, not tick-based balance
        assert ledger.get_compute("agent1") == 1000  # Full RateTracker capacity

        # Reset compute sets the tick-based balance (legacy API)
        ledger.reset_compute("agent1", 2000)
        # But get_compute still returns RateTracker capacity
        assert ledger.get_compute("agent1") == 1000

        # Consuming via RateTracker reduces capacity
        ledger.spend_compute("agent1", 100)
        assert ledger.get_compute("agent1") == 900

    @pytest.mark.asyncio
    async def test_wait_for_resource_immediate_success(self) -> None:
        """wait_for_resource returns immediately when capacity available."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 60.0,
                "resources": {"test": {"max_per_window": 10}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Should succeed immediately
        result = await ledger.wait_for_resource("agent1", "test", 5, timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_resource_timeout(self) -> None:
        """wait_for_resource times out when capacity not available."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 60.0,  # Long window
                "resources": {"test": {"max_per_window": 1}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Consume all capacity
        ledger.consume_resource("agent1", "test", 1)

        # Wait should timeout quickly
        result = await ledger.wait_for_resource("agent1", "test", 1, timeout=0.1)
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_resource_succeeds_after_window_expires(self) -> None:
        """wait_for_resource blocks until capacity available."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 0.1,  # Short window for test
                "resources": {"test": {"max_per_window": 1}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Consume all capacity
        ledger.consume_resource("agent1", "test", 1)

        # Wait should succeed after window expires
        result = await ledger.wait_for_resource("agent1", "test", 1, timeout=0.5)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_resource_legacy_mode_immediate(self) -> None:
        """wait_for_resource returns immediately in legacy mode."""
        ledger = Ledger()

        # Should succeed immediately in legacy mode
        result = await ledger.wait_for_resource("agent1", "any_resource", 999999)
        assert result is True

    def test_unconfigured_resource_has_infinite_capacity(self) -> None:
        """Resources not configured in rate_limiting have infinite capacity."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "resources": {"llm_calls": {"max_per_window": 10}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Unconfigured resource should have infinite capacity
        assert ledger.get_resource_remaining("agent1", "unconfigured") == float("inf")
        assert ledger.check_resource_capacity("agent1", "unconfigured", 999999) is True
        assert ledger.consume_resource("agent1", "unconfigured", 999999) is True

    def test_reset_compute_warns_when_rate_tracker_enabled(self) -> None:
        """reset_compute emits deprecation warning when rate limiting enabled."""
        import warnings

        config = {
            "rate_limiting": {
                "enabled": True,
                "resources": {"llm_tokens": {"max_per_window": 500}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])
        ledger.create_principal("agent1", starting_scrip=100, starting_compute=500)

        # Should emit a deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ledger.reset_compute("agent1", 1000)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "rate limiting enabled" in str(w[0].message)

        # get_compute returns RateTracker capacity (500), not tick balance (1000)
        assert ledger.get_compute("agent1") == 500

    def test_reset_compute_no_warning_when_rate_tracker_disabled(self) -> None:
        """reset_compute does NOT warn when rate limiting is disabled (legacy mode)."""
        import warnings

        ledger = Ledger()
        ledger.create_principal("agent1", starting_scrip=100, starting_compute=500)

        # Should NOT emit a deprecation warning in legacy mode
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ledger.reset_compute("agent1", 1000)
            # Filter for DeprecationWarnings only
            dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(dep_warnings) == 0

        assert ledger.get_compute("agent1") == 1000


class TestCpuSecondsResourceType:
    """Tests for cpu_seconds as a valid resource type (Plan #53 Phase 0)."""

    @pytest.mark.plans([53])
    def test_cpu_seconds_resource_type(self) -> None:
        """Ledger accepts cpu_seconds as a valid resource type.

        Plan #53 Phase 0 requires cpu_seconds to be tracked by the ledger
        via the rate tracker rolling window mechanism.
        """
        config = {
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 60.0,
                "resources": {
                    "cpu_seconds": {"max_per_window": 5.0}  # 5 CPU-seconds per minute
                }
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Initially should have full capacity
        assert ledger.check_resource_capacity("agent1", "cpu_seconds", 1.0) is True
        assert ledger.get_resource_remaining("agent1", "cpu_seconds") == 5.0

        # Consume some cpu_seconds
        result = ledger.consume_resource("agent1", "cpu_seconds", 2.5)
        assert result is True

        # Should have 2.5 remaining
        assert ledger.get_resource_remaining("agent1", "cpu_seconds") == 2.5

        # Should be able to consume more (up to 2.5)
        assert ledger.check_resource_capacity("agent1", "cpu_seconds", 2.0) is True
        assert ledger.check_resource_capacity("agent1", "cpu_seconds", 3.0) is False

    @pytest.mark.plans([53])
    def test_cpu_seconds_with_fractional_amounts(self) -> None:
        """cpu_seconds supports fractional amounts for accurate CPU tracking."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "resources": {
                    "cpu_seconds": {"max_per_window": 1.0}
                }
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Consume a tiny amount (simulating a fast execution)
        result = ledger.consume_resource("agent1", "cpu_seconds", 0.001)
        assert result is True
        assert ledger.get_resource_remaining("agent1", "cpu_seconds") == pytest.approx(0.999, rel=1e-6)

    @pytest.mark.plans([53])
    def test_cpu_seconds_exhaustion_blocks_further_consumption(self) -> None:
        """When cpu_seconds exhausted, further consumption is blocked."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "resources": {
                    "cpu_seconds": {"max_per_window": 1.0}
                }
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Exhaust the cpu_seconds
        ledger.consume_resource("agent1", "cpu_seconds", 1.0)
        assert ledger.get_resource_remaining("agent1", "cpu_seconds") == 0.0

        # Should not be able to consume more
        result = ledger.consume_resource("agent1", "cpu_seconds", 0.001)
        assert result is False


class TestMemoryBytesResourceType:
    """Tests for memory_bytes as a valid resource type (Plan #53 Phase 4)."""

    @pytest.mark.plans([53])
    def test_memory_bytes_resource_type(self) -> None:
        """Ledger accepts memory_bytes as a valid resource type.

        Plan #53 Phase 4 requires memory_bytes to be tracked by the ledger
        via the rate tracker rolling window mechanism.
        """
        config = {
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 60.0,
                "resources": {
                    "memory_bytes": {"max_per_window": 104857600}  # 100MB
                }
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Initially should have full capacity
        assert ledger.check_resource_capacity("agent1", "memory_bytes", 1048576) is True
        assert ledger.get_resource_remaining("agent1", "memory_bytes") == 104857600

        # Consume some memory_bytes
        result = ledger.consume_resource("agent1", "memory_bytes", 52428800)  # 50MB
        assert result is True

        # Should have 50MB remaining
        assert ledger.get_resource_remaining("agent1", "memory_bytes") == 52428800

        # Should be able to consume more (up to 50MB)
        assert ledger.check_resource_capacity("agent1", "memory_bytes", 30000000) is True
        assert ledger.check_resource_capacity("agent1", "memory_bytes", 60000000) is False

    @pytest.mark.plans([53])
    def test_memory_bytes_exhaustion_blocks_further_consumption(self) -> None:
        """When memory_bytes exhausted, further consumption is blocked."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "resources": {
                    "memory_bytes": {"max_per_window": 10485760}  # 10MB
                }
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Exhaust the memory_bytes
        ledger.consume_resource("agent1", "memory_bytes", 10485760)
        assert ledger.get_resource_remaining("agent1", "memory_bytes") == 0.0

        # Should not be able to consume more
        result = ledger.consume_resource("agent1", "memory_bytes", 1)
        assert result is False


class TestAsyncScripOperations:
    """Tests for async thread-safe scrip operations."""

    @pytest.mark.asyncio
    async def test_transfer_scrip_async_success(self) -> None:
        """Async transfer scrip succeeds with sufficient funds."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=100)
        ledger.create_principal("agent_b", starting_scrip=50)

        result = await ledger.transfer_scrip_async("agent_a", "agent_b", 30)

        assert result is True
        assert ledger.get_scrip("agent_a") == 70
        assert ledger.get_scrip("agent_b") == 80

    @pytest.mark.asyncio
    async def test_transfer_scrip_async_insufficient_funds(self) -> None:
        """Async transfer fails with insufficient funds."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=100)
        ledger.create_principal("agent_b", starting_scrip=50)

        result = await ledger.transfer_scrip_async("agent_a", "agent_b", 150)

        assert result is False
        assert ledger.get_scrip("agent_a") == 100
        assert ledger.get_scrip("agent_b") == 50

    @pytest.mark.asyncio
    async def test_transfer_scrip_async_zero_amount(self) -> None:
        """Async transfer fails with zero amount."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=100)
        ledger.create_principal("agent_b", starting_scrip=50)

        result = await ledger.transfer_scrip_async("agent_a", "agent_b", 0)

        assert result is False
        assert ledger.get_scrip("agent_a") == 100
        assert ledger.get_scrip("agent_b") == 50

    @pytest.mark.asyncio
    async def test_transfer_scrip_async_negative_amount(self) -> None:
        """Async transfer fails with negative amount."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=100)
        ledger.create_principal("agent_b", starting_scrip=50)

        result = await ledger.transfer_scrip_async("agent_a", "agent_b", -10)

        assert result is False
        assert ledger.get_scrip("agent_a") == 100
        assert ledger.get_scrip("agent_b") == 50

    @pytest.mark.asyncio
    async def test_deduct_scrip_async_success(self) -> None:
        """Async deduct scrip succeeds with sufficient funds."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=100)

        result = await ledger.deduct_scrip_async("agent_a", 30)

        assert result is True
        assert ledger.get_scrip("agent_a") == 70

    @pytest.mark.asyncio
    async def test_deduct_scrip_async_insufficient_funds(self) -> None:
        """Async deduct fails with insufficient funds."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=100)

        result = await ledger.deduct_scrip_async("agent_a", 150)

        assert result is False
        assert ledger.get_scrip("agent_a") == 100

    @pytest.mark.asyncio
    async def test_credit_scrip_async(self) -> None:
        """Async credit scrip adds to balance."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=100)

        await ledger.credit_scrip_async("agent_a", 50)

        assert ledger.get_scrip("agent_a") == 150

    @pytest.mark.asyncio
    async def test_credit_scrip_async_creates_principal(self) -> None:
        """Async credit scrip creates principal if not exists."""
        ledger = Ledger()

        await ledger.credit_scrip_async("new_agent", 100)

        assert ledger.get_scrip("new_agent") == 100


class TestAsyncResourceOperations:
    """Tests for async thread-safe resource operations."""

    @pytest.mark.asyncio
    async def test_spend_resource_async_success(self) -> None:
        """Async spend resource succeeds with sufficient balance."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=0)
        ledger.set_resource("agent_a", "llm_tokens", 500.0)

        result = await ledger.spend_resource_async("agent_a", "llm_tokens", 100.0)

        assert result is True
        assert ledger.get_resource("agent_a", "llm_tokens") == 400.0

    @pytest.mark.asyncio
    async def test_spend_resource_async_insufficient(self) -> None:
        """Async spend resource fails with insufficient balance."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=0)
        ledger.set_resource("agent_a", "llm_tokens", 100.0)

        result = await ledger.spend_resource_async("agent_a", "llm_tokens", 200.0)

        assert result is False
        assert ledger.get_resource("agent_a", "llm_tokens") == 100.0

    @pytest.mark.asyncio
    async def test_credit_resource_async(self) -> None:
        """Async credit resource adds to balance."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=0)
        ledger.set_resource("agent_a", "llm_tokens", 100.0)

        await ledger.credit_resource_async("agent_a", "llm_tokens", 50.0)

        assert ledger.get_resource("agent_a", "llm_tokens") == 150.0

    @pytest.mark.asyncio
    async def test_transfer_resource_async_success(self) -> None:
        """Async transfer resource succeeds with sufficient balance."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=0)
        ledger.create_principal("agent_b", starting_scrip=0)
        ledger.set_resource("agent_a", "llm_tokens", 500.0)
        ledger.set_resource("agent_b", "llm_tokens", 100.0)

        result = await ledger.transfer_resource_async(
            "agent_a", "agent_b", "llm_tokens", 200.0
        )

        assert result is True
        assert ledger.get_resource("agent_a", "llm_tokens") == 300.0
        assert ledger.get_resource("agent_b", "llm_tokens") == 300.0

    @pytest.mark.asyncio
    async def test_transfer_resource_async_insufficient(self) -> None:
        """Async transfer resource fails with insufficient balance."""
        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=0)
        ledger.create_principal("agent_b", starting_scrip=0)
        ledger.set_resource("agent_a", "llm_tokens", 100.0)
        ledger.set_resource("agent_b", "llm_tokens", 50.0)

        result = await ledger.transfer_resource_async(
            "agent_a", "agent_b", "llm_tokens", 200.0
        )

        assert result is False
        assert ledger.get_resource("agent_a", "llm_tokens") == 100.0
        assert ledger.get_resource("agent_b", "llm_tokens") == 50.0

    @pytest.mark.asyncio
    async def test_consume_resource_async_with_rate_tracker(self) -> None:
        """Async consume resource uses rate tracker when enabled."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "resources": {"llm_calls": {"max_per_window": 10}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # First consumption should succeed
        result = await ledger.consume_resource_async("agent1", "llm_calls", 5)
        assert result is True

        # Should have 5 remaining
        assert ledger.get_resource_remaining("agent1", "llm_calls") == 5

    @pytest.mark.asyncio
    async def test_consume_resource_async_legacy_mode(self) -> None:
        """Async consume resource always succeeds in legacy mode."""
        ledger = Ledger()

        result = await ledger.consume_resource_async("agent1", "any_resource", 999999)
        assert result is True


class TestConcurrentAccess:
    """Tests for concurrent access scenarios - race condition prevention."""

    @pytest.mark.asyncio
    async def test_concurrent_scrip_transfers_preserve_total(self) -> None:
        """Concurrent transfers preserve total scrip in system."""
        import asyncio

        ledger = Ledger()
        # Two agents with 1000 scrip each = 2000 total
        ledger.create_principal("agent_a", starting_scrip=1000)
        ledger.create_principal("agent_b", starting_scrip=1000)

        async def transfer_a_to_b() -> int:
            """Transfer 1 scrip from A to B, count successes."""
            successes = 0
            for _ in range(100):
                if await ledger.transfer_scrip_async("agent_a", "agent_b", 1):
                    successes += 1
            return successes

        async def transfer_b_to_a() -> int:
            """Transfer 1 scrip from B to A, count successes."""
            successes = 0
            for _ in range(100):
                if await ledger.transfer_scrip_async("agent_b", "agent_a", 1):
                    successes += 1
            return successes

        # Run transfers concurrently
        results = await asyncio.gather(transfer_a_to_b(), transfer_b_to_a())

        # Total scrip must remain 2000
        total = ledger.get_scrip("agent_a") + ledger.get_scrip("agent_b")
        assert total == 2000, f"Total scrip changed from 2000 to {total}"

    @pytest.mark.asyncio
    async def test_concurrent_deduct_prevents_overdraft(self) -> None:
        """Concurrent deducts cannot overdraft an account."""
        import asyncio

        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=100)

        async def deduct_50() -> bool:
            """Try to deduct 50 scrip."""
            return await ledger.deduct_scrip_async("agent_a", 50)

        # Try to deduct 50 three times concurrently (only 2 should succeed)
        results = await asyncio.gather(
            deduct_50(), deduct_50(), deduct_50()
        )

        # At most 2 should succeed (100 / 50 = 2)
        successes = sum(1 for r in results if r)
        assert successes <= 2, f"More than 2 deductions succeeded: {successes}"

        # Balance must be non-negative
        balance = ledger.get_scrip("agent_a")
        assert balance >= 0, f"Balance went negative: {balance}"

    @pytest.mark.asyncio
    async def test_concurrent_resource_spend_prevents_overdraft(self) -> None:
        """Concurrent resource spends cannot overdraft."""
        import asyncio

        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=0)
        ledger.set_resource("agent_a", "llm_tokens", 100.0)

        async def spend_50() -> bool:
            """Try to spend 50 tokens."""
            return await ledger.spend_resource_async("agent_a", "llm_tokens", 50.0)

        # Try to spend 50 three times concurrently (only 2 should succeed)
        results = await asyncio.gather(
            spend_50(), spend_50(), spend_50()
        )

        # At most 2 should succeed (100 / 50 = 2)
        successes = sum(1 for r in results if r)
        assert successes <= 2, f"More than 2 spends succeeded: {successes}"

        # Balance must be non-negative
        balance = ledger.get_resource("agent_a", "llm_tokens")
        assert balance >= 0, f"Balance went negative: {balance}"

    @pytest.mark.asyncio
    async def test_concurrent_resource_transfers_preserve_total(self) -> None:
        """Concurrent resource transfers preserve total in system."""
        import asyncio

        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=0)
        ledger.create_principal("agent_b", starting_scrip=0)
        ledger.set_resource("agent_a", "llm_tokens", 1000.0)
        ledger.set_resource("agent_b", "llm_tokens", 1000.0)

        async def transfer_a_to_b() -> int:
            """Transfer 1 token from A to B, count successes."""
            successes = 0
            for _ in range(100):
                if await ledger.transfer_resource_async(
                    "agent_a", "agent_b", "llm_tokens", 1.0
                ):
                    successes += 1
            return successes

        async def transfer_b_to_a() -> int:
            """Transfer 1 token from B to A, count successes."""
            successes = 0
            for _ in range(100):
                if await ledger.transfer_resource_async(
                    "agent_b", "agent_a", "llm_tokens", 1.0
                ):
                    successes += 1
            return successes

        # Run transfers concurrently
        await asyncio.gather(transfer_a_to_b(), transfer_b_to_a())

        # Total tokens must remain 2000
        total = (
            ledger.get_resource("agent_a", "llm_tokens")
            + ledger.get_resource("agent_b", "llm_tokens")
        )
        assert total == 2000.0, f"Total tokens changed from 2000 to {total}"

    @pytest.mark.asyncio
    async def test_high_contention_scrip_operations(self) -> None:
        """Many concurrent scrip operations maintain consistency."""
        import asyncio

        ledger = Ledger()
        ledger.create_principal("agent_a", starting_scrip=10000)
        ledger.create_principal("agent_b", starting_scrip=10000)

        async def random_operation(agent: str, other: str) -> None:
            """Perform random credit, deduct, or transfer."""
            import random
            for _ in range(50):
                op = random.randint(0, 2)
                if op == 0:
                    await ledger.credit_scrip_async(agent, 1)
                elif op == 1:
                    await ledger.deduct_scrip_async(agent, 1)
                else:
                    await ledger.transfer_scrip_async(agent, other, 1)

        # Run 10 concurrent tasks
        tasks = [
            random_operation("agent_a", "agent_b"),
            random_operation("agent_a", "agent_b"),
            random_operation("agent_a", "agent_b"),
            random_operation("agent_a", "agent_b"),
            random_operation("agent_a", "agent_b"),
            random_operation("agent_b", "agent_a"),
            random_operation("agent_b", "agent_a"),
            random_operation("agent_b", "agent_a"),
            random_operation("agent_b", "agent_a"),
            random_operation("agent_b", "agent_a"),
        ]
        await asyncio.gather(*tasks)

        # Balances must be non-negative
        assert ledger.get_scrip("agent_a") >= 0
        assert ledger.get_scrip("agent_b") >= 0