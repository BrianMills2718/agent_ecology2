"""Tests for Mint Auction System.

Plan #83: Tests updated for time-based execution (no ticks).

Tests the auction-based mint with:
- Bidding during bidding window
- Second-price (Vickrey) auction
- UBI distribution
- Time-based phase transitions
"""

import time
import pytest
from src.world.ledger import Ledger
from src.world.artifacts import ArtifactStore
from src.world.genesis import GenesisMint, create_genesis_artifacts


class TestMintAuctionPhases:
    """Test auction phase transitions (Plan #83 - time-based)."""

    def test_phase_waiting_before_first_auction(self):
        """Phase is WAITING before first_auction_delay_seconds."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        # Create mint with current start time (just started)
        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            ledger=ledger,
            start_time=time.time(),  # Just started
        )

        # Call update (won't start auction yet since not enough time passed)
        mint.update()
        status = mint._status([], "agent_1")
        assert status["phase"] == "WAITING"
        assert "next_auction_in_seconds" in status

    def test_phase_bidding_after_first_auction_delay(self):
        """Phase is BIDDING after first_auction_delay_seconds (Plan #83)."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        # Create mint with simulated past start time (past first_auction_delay)
        # Default first_auction_delay_seconds is 30, so start 31s ago
        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            ledger=ledger,
            start_time=time.time() - 31,
        )

        # Call update to trigger auction start
        mint.update()
        status = mint._status([], "agent_1")
        assert status["phase"] == "BIDDING"

    def test_phase_closed_after_bidding_window(self):
        """Phase is CLOSED after bidding window ends (Plan #83)."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        # Create mint that started long enough ago to be past bidding window
        # first_auction_delay=30s, bidding_window=30s, so need >60s elapsed
        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            ledger=ledger,
            start_time=time.time() - 31,  # Past first auction delay
        )

        # Start auction
        mint.update()

        # Manually set auction_start_time to simulate bidding window ended
        # bidding_window_seconds is 30 by default
        mint._auction_start_time = time.time() - 35  # 35s ago = past bidding window

        status = mint._status([], "agent_1")
        assert status["phase"] == "CLOSED"


class TestMintBidding:
    """Test bid submission."""

    def test_bid_success_during_bidding(self):
        """Can submit bid during bidding window."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        store = ArtifactStore()
        store.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                   created_by="agent_1", executable=True)

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

        mint.update()  # Start bidding
        result = mint._bid(["my_tool", 20], "agent_1")
        assert result["success"] is True
        assert result["amount"] == 20

    def test_bid_accepted_before_bidding(self):
        """Bid accepted before bidding window (Plan #5: anytime bidding)."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        store = ArtifactStore()
        store.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                   created_by="agent_1", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
            start_time=time.time(),  # Just started - still in WAITING
        )

        mint.update()  # Phase is WAITING
        result = mint._bid(["my_tool", 20], "agent_1")
        # Plan #5: Bids now accepted at any time
        assert result["success"] is True
        assert result["amount"] == 20

    def test_bid_holds_scrip(self):
        """Bidding holds scrip in escrow."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        store = ArtifactStore()
        store.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                   created_by="agent_1", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
            start_time=time.time() - 31,
        )

        mint.update()
        mint._bid(["my_tool", 30], "agent_1")

        # Scrip should be held (deducted from balance)
        assert ledger.get_scrip("agent_1") == 70

    def test_bid_insufficient_funds(self):
        """Bid rejected if insufficient scrip."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=10)
        store = ArtifactStore()
        store.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                   created_by="agent_1", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
            start_time=time.time() - 31,
        )

        mint.update()
        result = mint._bid(["my_tool", 50], "agent_1")
        assert result["success"] is False
        assert "Insufficient" in result["error"]


class TestAuctionResolution:
    """Test auction resolution mechanics (Plan #83 - time-based)."""

    def test_single_bidder_wins(self):
        """Single bidder wins and pays minimum bid."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        store = ArtifactStore()
        store.write("my_tool", "code", "def run(args, ctx): return {'result': 1}",
                   created_by="agent_1", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
            start_time=time.time() - 31,
        )

        mint.update()  # Start auction
        mint._bid(["my_tool", 30], "agent_1")

        # Simulate time passing past bidding window (30s default)
        mint._auction_start_time = time.time() - 35
        result = mint.update()  # Resolve

        assert result is not None
        assert result["winner_id"] == "agent_1"
        assert result["price_paid"] == 1  # Minimum bid (no second bidder)

    def test_second_price_auction(self):
        """Winner pays second-highest bid."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        ledger.create_principal("agent_2", starting_scrip=100)
        store = ArtifactStore()
        store.write("tool_1", "code", "def run(args, ctx): return {'result': 1}",
                   created_by="agent_1", executable=True)
        store.write("tool_2", "code", "def run(args, ctx): return {'result': 2}",
                   created_by="agent_2", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
            start_time=time.time() - 31,
        )

        mint.update()  # Start auction
        mint._bid(["tool_1", 50], "agent_1")  # Higher bid
        mint._bid(["tool_2", 30], "agent_2")  # Lower bid

        # Simulate time passing past bidding window
        mint._auction_start_time = time.time() - 35
        result = mint.update()  # Resolve

        assert result["winner_id"] == "agent_1"
        assert result["price_paid"] == 30  # Second-price

    def test_loser_gets_refund(self):
        """Losing bidder gets full refund."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        ledger.create_principal("agent_2", starting_scrip=100)
        store = ArtifactStore()
        store.write("tool_1", "code", "def run(args, ctx): return {'result': 1}",
                   created_by="agent_1", executable=True)
        store.write("tool_2", "code", "def run(args, ctx): return {'result': 2}",
                   created_by="agent_2", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
            start_time=time.time() - 31,
        )

        mint.update()  # Start auction
        mint._bid(["tool_1", 50], "agent_1")
        mint._bid(["tool_2", 30], "agent_2")

        # After bidding, both have scrip held
        assert ledger.get_scrip("agent_1") == 50
        assert ledger.get_scrip("agent_2") == 70

        # Simulate time passing and resolve
        mint._auction_start_time = time.time() - 35
        mint.update()

        # Loser (agent_2) gets full refund
        # Plus UBI share: 30 / 2 = 15
        assert ledger.get_scrip("agent_2") == 100 + 15

    def test_no_bids_auction_passes(self):
        """Auction with no bids passes without error."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            ledger=ledger,
            start_time=time.time() - 31,
        )

        mint.update()  # Start auction
        # No bids

        # Simulate time passing and resolve
        mint._auction_start_time = time.time() - 35
        result = mint.update()

        assert result is not None
        assert result["winner_id"] is None
        assert result["error"] == "No bids received"


class TestUBIDistribution:
    """Test UBI distribution mechanics."""

    def test_ubi_distributed_to_all_agents(self):
        """Winning bid is distributed as UBI."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        ledger.create_principal("agent_2", starting_scrip=100)
        ledger.create_principal("agent_3", starting_scrip=100)
        store = ArtifactStore()
        store.write("tool_1", "code", "def run(args, ctx): return {'result': 1}",
                   created_by="agent_1", executable=True)

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
            start_time=time.time() - 31,
        )

        mint.update()  # Start auction
        mint._bid(["tool_1", 30], "agent_1")  # Only bidder

        # Simulate time passing and resolve
        mint._auction_start_time = time.time() - 35
        result = mint.update()

        # Price paid is minimum_bid (1) with single bidder
        # UBI: 1 / 3 = 0 per agent (integer division)
        assert result["ubi_distributed"] is not None

    def test_scrip_conservation(self):
        """Total scrip is conserved (minus minting)."""
        ledger = Ledger()
        ledger.create_principal("agent_1", starting_scrip=100)
        ledger.create_principal("agent_2", starting_scrip=100)
        store = ArtifactStore()
        store.write("tool_1", "code", "def run(args, ctx): return {'result': 1}",
                   created_by="agent_1", executable=True)
        store.write("tool_2", "code", "def run(args, ctx): return {'result': 2}",
                   created_by="agent_2", executable=True)

        minted = [0]

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)
            minted[0] += amount

        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        mint = GenesisMint(
            mint_callback=mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=store,
            ledger=ledger,
            start_time=time.time() - 31,
        )

        initial_total = ledger.get_scrip("agent_1") + ledger.get_scrip("agent_2")

        mint.update()  # Start auction
        mint._bid(["tool_1", 50], "agent_1")
        mint._bid(["tool_2", 30], "agent_2")

        # Simulate time passing and resolve
        mint._auction_start_time = time.time() - 35
        mint.update()

        final_total = ledger.get_scrip("agent_1") + ledger.get_scrip("agent_2")

        # Final = Initial + minted (from mint scoring)
        assert final_total == initial_total + minted[0]
