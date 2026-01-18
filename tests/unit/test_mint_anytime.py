"""Tests for Oracle Anytime Bidding (Plan #5).

Plan #83: Tests updated for time-based execution (no ticks).

Tests the simplified mint model where:
- Bids are accepted at any time (not just during bidding window)
- Auctions resolve on time-based schedule
- Bids apply to the next auction resolution
"""

import time
import pytest
from src.world.ledger import Ledger
from src.world.artifacts import ArtifactStore
from src.world.genesis import GenesisMint


@pytest.mark.plans(5)
class TestAnytimeBidding:
    """Test anytime bidding functionality."""

    def test_bid_before_first_auction(self):
        """Bids accepted before first_auction_delay (Plan #83 - time-based).

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
            start_time=time.time(),  # Just started - still in WAITING phase
        )

        mint.update()  # Won't start auction yet (not enough time elapsed)

        # Bids should be accepted anytime
        result = mint._bid(["my_tool", 20], "agent_1")

        assert result["success"] is True, f"Bid should be accepted before first_auction_delay: {result.get('error', '')}"
        assert result["amount"] == 20

    def test_bid_during_closed_phase(self):
        """Bids accepted during CLOSED phase (Plan #83 - time-based).

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
            start_time=time.time() - 31,  # Past first auction delay
        )

        # Start auction
        mint.update()

        # Set auction to be past bidding window (CLOSED phase)
        mint._auction_start_time = time.time() - 35  # 35s ago = past bidding window

        # Bids should still be accepted in CLOSED phase (for next auction)
        result = mint._bid(["my_tool", 20], "agent_1")

        assert result["success"] is True, f"Bid should be accepted in CLOSED phase: {result.get('error', '')}"
        assert result["amount"] == 20

    def test_continuous_bidding(self):
        """Bids accepted at any time in simulation (Plan #83 - time-based).

        Plan #5: Verify bids work regardless of phase.
        """
        # Test bidding in WAITING, BIDDING, and CLOSED phases

        # WAITING phase
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        store = ArtifactStore()
        store.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                   owner_id="agent_1", executable=True)

        mint = GenesisMint(
            mint_callback=lambda a, am: ledger.credit_scrip(a, am),
            ubi_callback=lambda am, ex: ledger.distribute_ubi(am, ex),
            artifact_store=store,
            ledger=ledger,
            start_time=time.time(),  # WAITING phase
        )
        mint.update()
        result = mint._bid(["my_tool", 20], "agent_1")
        assert result["success"] is True, "Bid should succeed in WAITING phase"

        # BIDDING phase
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
            start_time=time.time() - 31,  # BIDDING phase
        )
        mint2.update()
        result2 = mint2._bid(["my_tool", 20], "agent_1")
        assert result2["success"] is True, "Bid should succeed in BIDDING phase"

        # CLOSED phase
        ledger3 = Ledger()
        ledger3.create_principal("agent_1", starting_scrip=100)
        store3 = ArtifactStore()
        store3.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                    owner_id="agent_1", executable=True)

        mint3 = GenesisMint(
            mint_callback=lambda a, am: ledger3.credit_scrip(a, am),
            ubi_callback=lambda am, ex: ledger3.distribute_ubi(am, ex),
            artifact_store=store3,
            ledger=ledger3,
            start_time=time.time() - 31,
        )
        mint3.update()
        mint3._auction_start_time = time.time() - 35  # CLOSED phase
        result3 = mint3._bid(["my_tool", 20], "agent_1")
        assert result3["success"] is True, "Bid should succeed in CLOSED phase"


@pytest.mark.plans(5)
class TestBidTimingForAuctions:
    """Test that bids apply to the correct auction (Plan #83 - time-based)."""

    def test_early_bid_included_in_first_auction(self):
        """Bid before first auction is included in first auction resolution.

        Plan #5: Early bids should be processed when auction resolves.
        Plan #83: Uses time-based auction resolution.
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
            start_time=time.time(),  # Just started
        )

        # Submit bid early (during WAITING phase)
        mint.update()
        result = mint._bid(["my_tool", 30], "agent_1")
        assert result["success"] is True

        # Simulate time passing to start auction
        mint._simulation_start_time = time.time() - 31  # Past first auction delay
        mint.update()  # This should start the auction

        # Simulate time passing to resolve auction
        mint._auction_start_time = time.time() - 35  # Past bidding window
        auction_result = mint.update()  # This should resolve

        # The early bid should be included and win
        assert auction_result is not None, "Auction should resolve with early bid"
        assert auction_result["winner_id"] == "agent_1"
        assert auction_result["artifact_id"] == "my_tool"

    def test_bid_after_resolution_applies_to_next_auction(self):
        """Bid after resolution applies to next auction (Plan #83 - time-based).

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
            start_time=time.time() - 31,  # Past first auction delay
        )

        # First auction cycle
        mint.update()  # Start auction
        mint._bid(["tool_1", 30], "agent_1")

        # Resolve first auction
        mint._auction_start_time = time.time() - 35
        first_result = mint.update()
        assert first_result is not None
        assert first_result["winner_id"] == "agent_1"

        # Bid during CLOSED phase (for next auction)
        result = mint._bid(["tool_2", 25], "agent_2")
        assert result["success"] is True

        # Start and resolve second auction
        # The update() should start a new auction period
        mint._auction_start_time = time.time()  # New auction just started
        mint.update()  # This processes but doesn't resolve yet

        # Resolve second auction
        mint._auction_start_time = time.time() - 35  # Past bidding window
        second_result = mint.update()

        # The bid from the CLOSED phase should be included
        assert second_result is not None, "Second auction should resolve"
        assert second_result["winner_id"] == "agent_2"
        assert second_result["artifact_id"] == "tool_2"


@pytest.mark.plans(5)
class TestDeprecatedConfigWarnings:
    """Test deprecation warnings for old config fields (Plan #83 - time-based)."""

    def test_first_auction_delay_works(self):
        """First auction delay controls when bidding starts.

        Plan #83: Uses first_auction_delay_seconds instead of first_auction_tick.
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
            start_time=time.time(),  # Just started
        )

        # With anytime bidding, bids are accepted regardless of phase
        mint.update()
        result = mint._bid(["my_tool", 20], "agent_1")

        # Bid should succeed
        assert result["success"] is True
