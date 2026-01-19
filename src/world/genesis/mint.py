"""Genesis Mint - Auction-based external minting

Implements periodic auctions where agents bid scrip to submit artifacts
for LLM scoring. Winning bid is redistributed as UBI to all agents.

Plan #83: All timing is now time-based (seconds), not tick-based.
Auctions run on wall-clock time.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from ...config import get_validated_config
from ...config_schema import GenesisConfig
from ..artifacts import ArtifactStore
from .base import GenesisArtifact
from .types import AuctionResult, BidInfo


class GenesisMint(GenesisArtifact):
    """
    Genesis artifact for auction-based external minting.

    Implements periodic auctions where agents bid scrip to submit artifacts
    for LLM scoring. Winning bid is redistributed as UBI to all agents.

    Auction phases (Plan #83 - time-based):
    - WAITING: Before first_auction_delay_seconds elapsed
    - BIDDING: Accepting bids (bidding_window_seconds)
    - CLOSED: After bidding window, before next auction period starts

    All configuration is in config.yaml under genesis.mint.auction.
    All timing values are in seconds (float).

    Plan #44: GenesisMint now delegates to kernel primitives for bid storage
    and auction resolution. Timing (phases, windows) stays here as policy.
    """

    # World reference for kernel delegation (Plan #44)
    _world: Any

    # Legacy callbacks (deprecated - use kernel primitives)
    mint_callback: Callable[[str, int], None] | None
    ubi_callback: Callable[[int, str | None], dict[str, int]] | None
    artifact_store: ArtifactStore | None
    ledger: Any  # Ledger reference for bid escrow

    # Auction timing state (Plan #83 - time-based)
    _simulation_start_time: float  # When simulation started (time.time())
    _auction_start_time: float | None  # When current auction period started
    _auction_history: list[AuctionResult]  # Local history for status display

    # Legacy bid state (deprecated - kernel stores bids now)
    _bids: dict[str, BidInfo]  # agent_id -> bid info
    _held_bids: dict[str, int]  # agent_id -> held amount (escrow)

    # Track submission IDs for bid updates (Plan #44)
    _submission_ids: dict[str, str]  # agent_id -> kernel submission_id

    # Config (Plan #83 - time-based)
    _mint_ratio: int
    _period_seconds: float
    _bidding_window_seconds: float
    _first_auction_delay_seconds: float
    _slots_per_auction: int
    _minimum_bid: int
    _tie_breaking: str
    _show_bid_count: bool
    _allow_bid_updates: bool
    _refund_on_scoring_failure: bool

    _scorer: Any  # MintScorer, lazy-loaded

    def __init__(
        self,
        mint_callback: Callable[[str, int], None] | None = None,
        ubi_callback: Callable[[int, str | None], dict[str, int]] | None = None,
        artifact_store: ArtifactStore | None = None,
        ledger: Any = None,
        genesis_config: GenesisConfig | None = None,
        start_time: float | None = None
    ) -> None:
        """
        Args:
            mint_callback: DEPRECATED - kernel handles minting now
            ubi_callback: DEPRECATED - kernel handles UBI now
            artifact_store: ArtifactStore to look up submitted artifacts
            ledger: Ledger for bid escrow
            genesis_config: Optional genesis config (uses global if not provided)
            start_time: Simulation start time (defaults to time.time())
        """
        import random
        self._random = random

        # Get config
        cfg = genesis_config or get_validated_config().genesis
        mint_cfg = cfg.mint

        super().__init__(
            artifact_id=mint_cfg.id,
            description=mint_cfg.description
        )

        # World reference set via set_world() after creation (Plan #44)
        self._world = None

        # Legacy callbacks (deprecated)
        self.mint_callback = mint_callback
        self.ubi_callback = ubi_callback
        self.artifact_store = artifact_store
        self.ledger = ledger

        # Auction timing state (Plan #83 - time-based)
        self._simulation_start_time = start_time if start_time is not None else time.time()
        self._auction_start_time = None
        self._auction_history = []

        # Legacy bid state (for backward compat during transition)
        self._bids = {}
        self._held_bids = {}

        # Kernel submission tracking (Plan #44)
        self._submission_ids = {}

        # Config (Plan #83 - time-based)
        self._mint_ratio = mint_cfg.mint_ratio
        self._period_seconds = mint_cfg.auction.period_seconds
        self._bidding_window_seconds = mint_cfg.auction.bidding_window_seconds
        self._first_auction_delay_seconds = mint_cfg.auction.first_auction_delay_seconds
        self._slots_per_auction = mint_cfg.auction.slots_per_auction
        self._minimum_bid = mint_cfg.auction.minimum_bid
        self._tie_breaking = mint_cfg.auction.tie_breaking
        self._show_bid_count = mint_cfg.auction.show_bid_count
        self._allow_bid_updates = mint_cfg.auction.allow_bid_updates
        self._refund_on_scoring_failure = mint_cfg.auction.refund_on_scoring_failure

        self._scorer = None

        # Register methods
        self.register_method(
            name="status",
            handler=self._status,
            cost=mint_cfg.methods.status.cost,
            description=mint_cfg.methods.status.description
        )

        self.register_method(
            name="bid",
            handler=self._bid,
            cost=mint_cfg.methods.bid.cost,
            description=mint_cfg.methods.bid.description
        )

        self.register_method(
            name="check",
            handler=self._check,
            cost=mint_cfg.methods.check.cost,
            description=mint_cfg.methods.check.description
        )

    def set_world(self, world: Any) -> None:
        """Set world reference for kernel delegation (Plan #44).

        Called by World after genesis artifact creation to enable
        kernel primitive access without circular imports.
        """
        self._world = world

    def _get_elapsed_seconds(self) -> float:
        """Get seconds elapsed since simulation start."""
        return time.time() - self._simulation_start_time

    def _get_phase(self) -> str:
        """Get current auction phase (Plan #83 - time-based).

        Returns:
            "WAITING" - Before first_auction_delay_seconds elapsed
            "BIDDING" - Accepting bids (within bidding_window_seconds)
            "CLOSED" - After bidding window, waiting for next period
        """
        elapsed = self._get_elapsed_seconds()

        # Before first auction delay - waiting
        if elapsed < self._first_auction_delay_seconds:
            return "WAITING"

        # No auction started yet (should start now)
        if self._auction_start_time is None:
            return "WAITING"

        # Calculate time since this auction period started
        time_since_auction_start = time.time() - self._auction_start_time

        # Negative means we're waiting for next auction (start time is in future)
        if time_since_auction_start < 0:
            return "CLOSED"

        # Within bidding window
        if time_since_auction_start < self._bidding_window_seconds:
            return "BIDDING"

        return "CLOSED"

    def _status(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Return auction status (Plan #83 - time-based)."""
        phase = self._get_phase()
        elapsed = self._get_elapsed_seconds()
        now = time.time()

        result: dict[str, Any] = {
            "success": True,
            "mint": "genesis_mint",
            "type": "auction",
            "phase": phase,
            "elapsed_seconds": round(elapsed, 1),
            "period_seconds": self._period_seconds,
            "bidding_window_seconds": self._bidding_window_seconds,
            "first_auction_delay_seconds": self._first_auction_delay_seconds,
            "minimum_bid": self._minimum_bid,
            "slots_per_auction": self._slots_per_auction,
            "auctions_completed": len(self._auction_history),
        }

        if phase == "WAITING":
            # Time until first auction starts
            wait_remaining = self._first_auction_delay_seconds - elapsed
            result["next_auction_in_seconds"] = round(max(0, wait_remaining), 1)
        elif phase == "BIDDING":
            if self._auction_start_time is not None:
                time_in_bidding = now - self._auction_start_time
                time_remaining = self._bidding_window_seconds - time_in_bidding
                result["bidding_ends_in_seconds"] = round(max(0, time_remaining), 1)
            if self._show_bid_count:
                result["bid_count"] = len(self._bids)
            # Show agent's own bid if they have one
            if invoker_id in self._bids:
                result["your_bid"] = {
                    "artifact_id": self._bids[invoker_id]["artifact_id"],
                    "amount": self._bids[invoker_id]["amount"],
                }
        elif phase == "CLOSED":
            if self._auction_start_time is not None:
                # Time until next auction period starts
                time_since_start = now - self._auction_start_time
                next_auction_in = self._period_seconds - time_since_start
                result["next_auction_in_seconds"] = round(max(0, next_auction_in), 1)

        if self._auction_history:
            last = self._auction_history[-1]
            result["last_auction"] = {
                "winner": last["winner_id"],
                "artifact": last["artifact_id"],
                "price_paid": last["price_paid"],
                "score": last["score"],
                "scrip_minted": last["scrip_minted"],
            }

        return result

    def _bid(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Submit a sealed bid during bidding window.

        Plan #44: Now delegates to kernel primitives for bid storage.
        Plan #83: Timing is now time-based, not tick-based.
        """
        if len(args) < 2:
            return {"success": False, "error": "bid requires [artifact_id, amount]"}

        artifact_id: str = str(args[0])
        try:
            amount: int = int(args[1])
        except (TypeError, ValueError):
            return {"success": False, "error": "bid amount must be an integer"}

        # Plan #5: Accept bids anytime (no phase check)
        # Bids apply to the next auction resolution

        # Validate amount (policy)
        if amount < self._minimum_bid:
            return {"success": False, "error": f"Bid must be at least {self._minimum_bid} scrip"}

        # Check if bid update is allowed (policy)
        has_existing_bid = invoker_id in self._submission_ids
        if has_existing_bid and not self._allow_bid_updates:
            return {"success": False, "error": "Bid updates not allowed. You already have a bid."}

        # Use kernel primitives if world is set (Plan #44)
        if self._world is not None:
            # If updating, cancel old submission first
            if has_existing_bid:
                old_submission_id = self._submission_ids[invoker_id]
                self._world.cancel_mint_submission(invoker_id, old_submission_id)
                del self._submission_ids[invoker_id]

            # Submit via kernel
            try:
                submission_id = self._world.submit_for_mint(
                    principal_id=invoker_id,
                    artifact_id=artifact_id,
                    bid=amount
                )
                self._submission_ids[invoker_id] = submission_id

                # Keep local _bids for backward compat with _check() and _status()
                self._bids[invoker_id] = {
                    "agent_id": invoker_id,
                    "artifact_id": artifact_id,
                    "amount": amount,
                    "submitted_at": time.time(),  # Plan #83: Use timestamp
                }

                return {
                    "success": True,
                    "message": f"Bid of {amount} scrip recorded for {artifact_id}",
                    "artifact_id": artifact_id,
                    "amount": amount,
                    "submission_id": submission_id,
                }
            except ValueError as e:
                return {"success": False, "error": str(e)}

        # Legacy path (no world reference - deprecated)
        # Check if artifact exists and is executable
        if self.artifact_store:
            artifact = self.artifact_store.get(artifact_id)
            if not artifact:
                return {"success": False, "error": f"Artifact {artifact_id} not found"}
            if not artifact.executable:
                return {
                    "success": False,
                    "error": f"Mint only accepts executable artifacts. '{artifact_id}' is not executable."
                }

        # Check if agent can afford the bid
        if self.ledger:
            current_held = self._held_bids.get(invoker_id, 0)
            additional_needed = amount - current_held
            if additional_needed > 0:
                available = self.ledger.get_scrip(invoker_id)
                if available < additional_needed:
                    return {
                        "success": False,
                        "error": f"Insufficient scrip. Need {additional_needed} more (have {available})"
                    }
                # Hold the additional amount
                self.ledger.deduct_scrip(invoker_id, additional_needed)
                self._held_bids[invoker_id] = amount
            elif additional_needed < 0:
                # Refund the difference if lowering bid
                refund = -additional_needed
                self.ledger.credit_scrip(invoker_id, refund)
                self._held_bids[invoker_id] = amount

        # Record bid (legacy) - Plan #83: use timestamp
        self._bids[invoker_id] = {
            "agent_id": invoker_id,
            "artifact_id": artifact_id,
            "amount": amount,
            "submitted_at": time.time(),
        }

        return {
            "success": True,
            "message": f"Bid of {amount} scrip recorded for {artifact_id}",
            "artifact_id": artifact_id,
            "amount": amount,
        }

    def _check(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check bid or auction result status (Plan #83 - time-based)."""
        # If agent has active bid, show it
        if invoker_id in self._bids:
            bid = self._bids[invoker_id]
            return {
                "success": True,
                "has_active_bid": True,
                "bid": {
                    "artifact_id": bid["artifact_id"],
                    "amount": bid["amount"],
                    "submitted_at": bid.get("submitted_at"),  # Plan #83: timestamp
                },
                "phase": self._get_phase(),
            }

        # Check if agent won any recent auctions
        won_auctions = [
            a for a in self._auction_history
            if a["winner_id"] == invoker_id
        ]
        if won_auctions:
            return {
                "success": True,
                "has_active_bid": False,
                "auctions_won": len(won_auctions),
                "last_win": won_auctions[-1],
            }

        return {
            "success": True,
            "has_active_bid": False,
            "message": "No active bid and no auction wins",
        }

    @property
    def submissions(self) -> dict[str, dict[str, Any]]:
        """Expose current bids and recent results for world state summary.

        Returns dict mapping artifact_id -> submission info with:
        - status: "pending" (active bid) or "scored" (from last auction)
        - submitter: agent who submitted
        - score: score if scored, None otherwise
        """
        result: dict[str, dict[str, Any]] = {}

        # Active bids show as "pending"
        for agent_id, bid in self._bids.items():
            result[bid["artifact_id"]] = {
                "status": "pending",
                "submitter": agent_id,
                "score": None,
            }

        # Most recent auction result (if any and had a winner)
        if self._auction_history:
            last = self._auction_history[-1]
            if last["artifact_id"] and last["winner_id"]:
                result[last["artifact_id"]] = {
                    "status": "scored",
                    "submitter": last["winner_id"],
                    "score": last["score"],
                    "score_reason": last.get("score_reason"),
                }

        return result

    def update(self) -> AuctionResult | None:
        """Update auction state based on current time (Plan #83 - time-based).

        Call this periodically to:
        - Start bidding windows when first_auction_delay_seconds elapses
        - Resolve auctions when bidding_window_seconds ends

        Returns AuctionResult if an auction was resolved, None otherwise.
        """
        now = time.time()
        elapsed = self._get_elapsed_seconds()

        # Not yet time for first auction
        if elapsed < self._first_auction_delay_seconds:
            return None

        # Check if we should start a new bidding window
        if self._auction_start_time is None:
            # Start first auction
            self._auction_start_time = now
            return None

        # Calculate time since this auction period started
        time_since_auction_start = now - self._auction_start_time

        # Check if bidding window just ended (need to resolve)
        if time_since_auction_start >= self._bidding_window_seconds:
            # Check if we haven't already resolved this auction
            # by seeing if we're past the bidding window but before next period
            if time_since_auction_start < self._period_seconds:
                # Resolve the auction
                result = self._resolve_auction()
                # Schedule next auction at the end of this period
                self._auction_start_time = self._auction_start_time + self._period_seconds
                return result
            else:
                # We're past the period - start a new auction
                # This handles cases where update() wasn't called for a while
                self._auction_start_time = now
                return None

        return None

    def _resolve_auction(self) -> AuctionResult:
        """Resolve the current auction and distribute rewards.

        Plan #44: Now delegates to kernel for auction resolution.
        Kernel handles scoring, minting, and UBI distribution.
        """
        # Use kernel primitives if world is set (Plan #44)
        if self._world is not None:
            # Kernel already has the bids from _bid() calls
            kernel_result = self._world.resolve_mint_auction()

            # Convert kernel result to AuctionResult format
            result: AuctionResult = {
                "winner_id": kernel_result.get("winner_id"),
                "artifact_id": kernel_result.get("artifact_id"),
                "winning_bid": kernel_result.get("winning_bid", 0),
                "price_paid": kernel_result.get("price_paid", 0),
                "score": kernel_result.get("score"),
                "score_reason": kernel_result.get("score_reason"),
                "scrip_minted": kernel_result.get("scrip_minted", 0),
                "ubi_distributed": kernel_result.get("ubi_distributed", {}),
                "error": kernel_result.get("error"),
            }
            self._auction_history.append(result)

            # Clear local state
            self._bids.clear()
            self._submission_ids.clear()

            return result

        # Legacy path (no world reference - deprecated)
        if not self._bids:
            # No bids - auction passes
            empty_result: AuctionResult = {
                "winner_id": None,
                "artifact_id": None,
                "winning_bid": 0,
                "price_paid": 0,
                "score": None,
                "scrip_minted": 0,
                "ubi_distributed": {},
                "error": "No bids received",
            }
            self._auction_history.append(empty_result)
            return empty_result

        # Sort bids by amount (descending)
        sorted_bids = sorted(
            self._bids.values(),
            key=lambda b: b["amount"],
            reverse=True
        )

        # Handle ties
        top_amount = sorted_bids[0]["amount"]
        top_bidders = [b for b in sorted_bids if b["amount"] == top_amount]

        if len(top_bidders) > 1:
            if self._tie_breaking == "random":
                winner_bid = self._random.choice(top_bidders)
            else:  # first_bid - Plan #83: use submitted_at timestamp
                winner_bid = min(top_bidders, key=lambda b: b["submitted_at"])
        else:
            winner_bid = sorted_bids[0]

        # Determine second-price
        if len(sorted_bids) > 1:
            # Find highest bid that isn't the winner's
            second_price = self._minimum_bid
            for b in sorted_bids:
                if b["agent_id"] != winner_bid["agent_id"]:
                    second_price = b["amount"]
                    break
        else:
            second_price = self._minimum_bid

        winner_id = winner_bid["agent_id"]
        artifact_id = winner_bid["artifact_id"]
        winning_bid = winner_bid["amount"]

        # Refund losing bidders
        for agent_id, held in self._held_bids.items():
            if agent_id != winner_id and self.ledger:
                self.ledger.credit_scrip(agent_id, held)

        # Winner pays second price (refund difference)
        if self.ledger:
            refund = winning_bid - second_price
            if refund > 0:
                self.ledger.credit_scrip(winner_id, refund)

        # Clear held bids
        self._held_bids.clear()

        # Distribute UBI from the price paid (legacy - uses callback)
        ubi_distribution: dict[str, int] = {}
        if self.ubi_callback is not None:
            ubi_distribution = self.ubi_callback(second_price, None)

        # Score the artifact
        score: int | None = None
        scrip_minted = 0
        error: str | None = None

        if self.artifact_store:
            artifact = self.artifact_store.get(artifact_id)
            if artifact:
                # Lazy-load scorer
                if self._scorer is None:
                    from ..mint_scorer import get_scorer
                    self._scorer = get_scorer()

                try:
                    score_result = self._scorer.score_artifact(
                        artifact_id=artifact_id,
                        artifact_type=artifact.type,
                        content=artifact.content
                    )
                    if score_result["success"]:
                        score = score_result["score"]
                        scrip_minted = score // self._mint_ratio
                        if scrip_minted > 0 and self.mint_callback is not None:
                            self.mint_callback(winner_id, scrip_minted)
                    else:
                        error = score_result.get("error", "Scoring failed")
                        if self._refund_on_scoring_failure and self.ledger:
                            self.ledger.credit_scrip(winner_id, second_price)
                except Exception as e:  # exception-ok: scoring can fail in many ways
                    error = f"Scoring error: {str(e)}"
                    if self._refund_on_scoring_failure and self.ledger:
                        self.ledger.credit_scrip(winner_id, second_price)
            else:
                error = f"Artifact {artifact_id} not found"

        result = AuctionResult(
            winner_id=winner_id,
            artifact_id=artifact_id,
            winning_bid=winning_bid,
            price_paid=second_price,
            score=score,
            scrip_minted=scrip_minted,
            ubi_distributed=ubi_distribution,
            error=error,
        )
        self._auction_history.append(result)

        # Clear bids for next auction
        self._bids.clear()

        return result

    def mock_score(self, artifact_id: str, score: int) -> bool:
        """Mock scoring - for testing without LLM."""
        # This is a simplified mock for backward compat in tests
        # In auction mode, scoring happens automatically during resolution
        return True
