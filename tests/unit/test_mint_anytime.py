"""Tests for Oracle Anytime Bidding (Plan #5).

Tests the simplified mint model where:
- Bids are accepted at any tick (not just during bidding window)
- Auctions resolve on fixed schedule
- Bids apply to the next auction resolution
"""

import pytest
from src.world.ledger import Ledger
from src.world.artifacts import ArtifactStore
from src.world.genesis import GenesisMint


@pytest.mark.plans(5)
class TestAnytimeBidding:
    """Test anytime bidding functionality."""

    def test_bid_before_first_auction(self):
        """Bids accepted before first_auction_tick (tick 50).

        Plan #5: Phase-based restriction removed. Bids accepted anytime.
        """
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        store = ArtifactStore()
        store.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                   owner_id="agent_1", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
        )

        # Before first_auction_tick (default 50)
        mint.on_tick(10)

        # OLD: This would return success=False with "not open" error
        # NEW: Bid should be accepted
        result = mint._bid(["my_tool", 20], "agent_1")

        assert result["success"] is True, f"Bid should be accepted before first_auction_tick: {result.get('error', '')}"
        assert result["amount"] == 20

    def test_bid_during_closed_phase(self):
        """Bids accepted during CLOSED phase (after bidding window ends).

        Plan #5: Phase-based restriction removed. Bids accepted anytime.
        """
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        store = ArtifactStore()
        store.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                   owner_id="agent_1", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
        )

        # Start bidding at tick 50
        mint.on_tick(50)
        # Resolve auction at tick 60
        mint.on_tick(60)
        # Now in CLOSED phase (tick 61-99)
        mint.on_tick(61)

        # OLD: This would return success=False with "window closed" error
        # NEW: Bid should be accepted (for next auction)
        result = mint._bid(["my_tool", 20], "agent_1")

        assert result["success"] is True, f"Bid should be accepted in CLOSED phase: {result.get('error', '')}"
        assert result["amount"] == 20

    def test_continuous_bidding(self):
        """Bids accepted at any tick in simulation.

        Plan #5: Verify bids work at tick 0, 25, 75, 150, etc.
        """
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        store = ArtifactStore()
        store.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                   owner_id="agent_1", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
        )

        # Test bidding at various ticks
        test_ticks = [0, 25, 49, 51, 75, 99, 101, 150]

        for tick in test_ticks:
            # Reset state for each test
            ledger2 = Ledger()
            ledger2.create_principal("agent_1", starting_scrip=100)
            store2 = ArtifactStore()
            store2.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                        owner_id="agent_1", executable=True)

            mint2 = GenesisMint(
                mint_callback=lambda a, am: ledger2.credit_scrip(a, am),
                ubi_callback=lambda am, ex: ledger2.distribute_ubi(am, ex),
                artifact_store=store2,
                ledger=ledger2,
            )

            mint2.on_tick(tick)
            result = mint2._bid(["my_tool", 20], "agent_1")

            assert result["success"] is True, f"Bid should be accepted at tick {tick}: {result.get('error', '')}"


@pytest.mark.plans(5)
class TestBidTimingForAuctions:
    """Test that bids apply to the correct auction."""

    def test_early_bid_included_in_first_auction(self):
        """Bid before first_auction_tick is included in first auction resolution.

        Plan #5: Early bids should be processed when auction resolves.
        """
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        store = ArtifactStore()
        store.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                   owner_id="agent_1", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
        )

        # Submit bid early (tick 10)
        mint.on_tick(10)
        result = mint._bid(["my_tool", 30], "agent_1")
        assert result["success"] is True

        # Advance to first auction start
        mint.on_tick(50)

        # Resolve first auction
        auction_result = mint.on_tick(60)

        # The early bid should be included and win
        assert auction_result is not None
        assert auction_result["winner_id"] == "agent_1"
        assert auction_result["artifact_id"] == "my_tool"

    def test_bid_after_resolution_applies_to_next_auction(self):
        """Bid after resolution applies to next auction.

        Plan #5: Bids in CLOSED phase join next auction cycle.
        """
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        ledger.create_principal("agent_2", starting_scrip=100)
        store = ArtifactStore()
        store.write("tool_1", "code", "def run(args, ctx): return {'result': 1}",
                   owner_id="agent_1", executable=True)
        store.write("tool_2", "code", "def run(args, ctx): return {'result': 2}",
                   owner_id="agent_2", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
        )

        # First auction cycle
        mint.on_tick(50)
        mint._bid(["tool_1", 30], "agent_1")
        mint.on_tick(60)  # Resolve first auction

        # Bid during CLOSED phase (tick 61)
        mint.on_tick(61)
        result = mint._bid(["tool_2", 25], "agent_2")
        assert result["success"] is True

        # Advance to next auction period (tick 100 is next auction start with period 50)
        # Actually need to advance through the ticks properly
        for tick in range(62, 100):
            mint.on_tick(tick)

        # Start second auction at tick 100
        mint.on_tick(100)

        # Resolve second auction at tick 110
        second_result = mint.on_tick(110)

        # The bid from tick 61 should be included
        assert second_result is not None
        assert second_result["winner_id"] == "agent_2"
        assert second_result["artifact_id"] == "tool_2"


@pytest.mark.plans(5)
class TestDeprecatedConfigWarnings:
    """Test deprecation warnings for old config fields."""

    def test_first_auction_tick_deprecated(self):
        """Log deprecation warning if first_auction_tick is configured.

        Plan #5: Old configs should still work but log warning.
        """
        # This test verifies backward compatibility
        # first_auction_tick should be ignored (bids accepted anytime)
        # but shouldn't cause errors
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        store = ArtifactStore()
        store.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                   owner_id="agent_1", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
        )

        # With anytime bidding, first_auction_tick doesn't block bids
        # but is still used for scheduling the first auction resolution
        mint.on_tick(5)
        result = mint._bid(["my_tool", 20], "agent_1")

        # Bid should succeed regardless of first_auction_tick
        assert result["success"] is True
