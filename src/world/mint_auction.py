"""Mint auction logic extracted from World (TD-001).

This module handles the mint auction system:
- Submit artifacts for mint consideration
- Track pending submissions and escrowed bids
- Resolve auctions (second-price, LLM scoring, UBI distribution)

Plan #44 - Kernel Mint Primitives
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, TypedDict, TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .ledger import Ledger
    from .artifacts import ArtifactStore
    from .logger import EventLogger


logger = logging.getLogger(__name__)


class KernelMintSubmission(TypedDict):
    """A mint submission stored in kernel state (Plan #44)."""
    submission_id: str
    principal_id: str
    artifact_id: str
    bid: int
    submitted_at: int  # Event number when submitted


class KernelMintResult(TypedDict, total=False):
    """Result of a mint auction resolution (Plan #44)."""
    winner_id: str | None
    artifact_id: str | None
    winning_bid: int
    price_paid: int  # Second-price auction
    score: int | None
    score_reason: str | None  # LLM's explanation for the score
    scrip_minted: int
    ubi_distributed: dict[str, int]
    error: str | None
    resolved_at: int  # Event number when resolved


class MintAuction:
    """Manages mint auctions - artifact scoring and scrip minting.

    Extracted from World class to improve modularity (TD-001).

    Dependencies:
        ledger: For scrip operations (credit, deduct, distribute_ubi)
        artifacts: For artifact validation
        logger: For event logging
        get_event_number: Callback to get current event number
    """

    def __init__(
        self,
        ledger: Ledger,
        artifacts: ArtifactStore,
        logger: EventLogger,
        get_event_number: Callable[[], int],
        *,
        first_auction_delay_seconds: float = 30.0,
        bidding_window_seconds: float = 60.0,
        period_seconds: float = 120.0,
        mint_ratio: int = 10,
    ) -> None:
        """Initialize MintAuction.

        Args:
            ledger: Ledger for scrip operations
            artifacts: ArtifactStore for artifact validation
            logger: EventLogger for logging events
            get_event_number: Callable that returns current event number
            first_auction_delay_seconds: Delay before first auction starts
            bidding_window_seconds: Duration of bidding phase
            period_seconds: Seconds between auction starts
            mint_ratio: Divisor for score-to-scrip (score / ratio = scrip)
        """
        self._ledger = ledger
        self._artifacts = artifacts
        self._logger = logger
        self._get_event_number = get_event_number

        # Internal state
        self._submissions: dict[str, KernelMintSubmission] = {}
        self._held_bids: dict[str, int] = {}  # principal_id -> escrowed bid amount
        self._history: list[KernelMintResult] = []

        # Cost tracking callbacks (Plan #153)
        self._is_budget_exhausted: Callable[[], bool] | None = None
        self._track_api_cost: Callable[[float], None] | None = None

        # Time-based auction state (Plan #254: moved from GenesisMint)
        self._start_time = time.time()
        self._auction_start_time: float | None = None
        # TD-012: Read from config via world.py
        self._first_auction_delay_seconds = first_auction_delay_seconds
        self._bidding_window_seconds = bidding_window_seconds
        self._period_seconds = period_seconds
        self._mint_ratio = mint_ratio

    def set_cost_callbacks(
        self,
        is_budget_exhausted: Callable[[], bool] | None = None,
        track_api_cost: Callable[[float], None] | None = None,
    ) -> None:
        """Set budget check and cost tracking callbacks for scorer LLM calls.

        Args:
            is_budget_exhausted: Callback returning True if budget is exhausted
            track_api_cost: Callback to track API cost in dollars
        """
        self._is_budget_exhausted = is_budget_exhausted
        self._track_api_cost = track_api_cost

    @property
    def event_number(self) -> int:
        """Current event number for logging."""
        return self._get_event_number()

    def mint_scrip(self, principal_id: str, amount: int) -> None:
        """Mint new scrip for a principal.

        Scrip is the economic currency - minting adds purchasing power.

        Args:
            principal_id: Who receives the minted scrip
            amount: Amount to mint
        """
        self._ledger.credit_scrip(principal_id, amount)
        self._logger.log("mint", {
            "event_number": self.event_number,
            "principal_id": principal_id,
            "amount": amount,
            "scrip_after": self._ledger.get_scrip(principal_id)
        })

    def submit(self, principal_id: str, artifact_id: str, bid: int) -> str:
        """Submit artifact for mint consideration. Returns submission_id.

        This is a kernel primitive - minting is physics, not genesis privilege.
        The actual auction resolution happens via resolve().

        Args:
            principal_id: Who is submitting
            artifact_id: Artifact to submit for minting
            bid: Amount of scrip to bid

        Returns:
            submission_id: Unique ID for this submission

        Raises:
            ValueError: If validation fails (insufficient scrip, not owner, etc.)
        """
        # Validate artifact exists and is owned by principal
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            raise ValueError(f"Artifact {artifact_id} not found")
        # ADR-0028/Plan #311: Check authorization via artifact state, not created_by
        writer = (artifact.state or {}).get("writer")
        principal = (artifact.state or {}).get("principal")
        if principal_id not in (writer, principal):
            raise ValueError(f"Principal {principal_id} is not authorized for {artifact_id}")
        if not artifact.executable:
            raise ValueError(f"Artifact {artifact_id} is not executable")

        # Validate bid amount
        if bid <= 0:
            raise ValueError("Bid must be positive")

        # Check principal has sufficient scrip
        available_scrip = self._ledger.get_scrip(principal_id)
        if available_scrip < bid:
            raise ValueError(f"Insufficient scrip: have {available_scrip}, need {bid}")

        # Escrow the bid
        self._ledger.deduct_scrip(principal_id, bid)
        current_held = self._held_bids.get(principal_id, 0)
        self._held_bids[principal_id] = current_held + bid

        # Create submission
        submission_id = f"mint_sub_{uuid.uuid4().hex[:8]}"
        self._submissions[submission_id] = {
            "submission_id": submission_id,
            "principal_id": principal_id,
            "artifact_id": artifact_id,
            "bid": bid,
            "submitted_at": self.event_number,
        }

        self._logger.log("mint_submission", {
            "event_number": self.event_number,
            "submission_id": submission_id,
            "principal_id": principal_id,
            "artifact_id": artifact_id,
            "bid": bid,
        })

        return submission_id

    def get_submissions(self) -> list[KernelMintSubmission]:
        """Get all pending mint submissions.

        Returns:
            List of pending submissions (public data)
        """
        return list(self._submissions.values())

    def get_history(self, limit: int = 100) -> list[KernelMintResult]:
        """Get mint history (most recent first).

        Args:
            limit: Maximum number of results

        Returns:
            List of mint results, newest first
        """
        return list(reversed(self._history[-limit:]))

    def cancel(self, principal_id: str, submission_id: str) -> bool:
        """Cancel a mint submission and refund the bid.

        Args:
            principal_id: Who is cancelling (must own the submission)
            submission_id: Which submission to cancel

        Returns:
            True if cancelled, False if not allowed
        """
        if submission_id not in self._submissions:
            return False

        submission = self._submissions[submission_id]

        # Can only cancel your own submission
        if submission["principal_id"] != principal_id:
            return False

        # Refund the bid
        bid_amount = submission["bid"]
        self._ledger.credit_scrip(principal_id, bid_amount)

        # Update held bids
        current_held = self._held_bids.get(principal_id, 0)
        self._held_bids[principal_id] = max(0, current_held - bid_amount)

        # Remove submission
        del self._submissions[submission_id]

        self._logger.log("mint_cancellation", {
            "event_number": self.event_number,
            "submission_id": submission_id,
            "principal_id": principal_id,
            "refunded": bid_amount,
        })

        return True

    def update(self) -> KernelMintResult | None:
        """Update auction state based on current time (Plan #254 - time-based).

        Call this periodically to:
        - Start bidding windows when first_auction_delay_seconds elapses
        - Resolve auctions when bidding_window_seconds ends

        Returns KernelMintResult if an auction was resolved, None otherwise.
        """
        now = time.time()
        elapsed = now - self._start_time

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
                result = self.resolve()
                # Schedule next auction at the end of this period
                self._auction_start_time = self._auction_start_time + self._period_seconds
                return result
            else:
                # We're past the period - start a new auction
                # This handles cases where update() wasn't called for a while
                self._auction_start_time = now
                return None

        return None

    def resolve(self, _mock_score: int | None = None) -> KernelMintResult:
        """Resolve the current mint auction.

        Called periodically or manually for testing.
        Picks winner (highest bid), runs second-price auction,
        scores artifact, mints scrip, distributes UBI.

        Args:
            _mock_score: For testing - use this score instead of LLM scoring

        Returns:
            KernelMintResult with auction outcome
        """
        if not self._submissions:
            result: KernelMintResult = {
                "winner_id": None,
                "artifact_id": None,
                "winning_bid": 0,
                "price_paid": 0,
                "score": None,
                "scrip_minted": 0,
                "ubi_distributed": {},
                "error": "No submissions",
                "resolved_at": self.event_number,
            }
            self._history.append(result)
            return result

        # Sort by bid amount (descending)
        submissions = list(self._submissions.values())
        sorted_subs = sorted(submissions, key=lambda s: s["bid"], reverse=True)

        winner = sorted_subs[0]
        winner_id = winner["principal_id"]
        artifact_id = winner["artifact_id"]
        winning_bid = winner["bid"]

        # Second-price: pay the second-highest bid (or minimum if only one)
        minimum_bid = 1  # Could come from config
        if len(sorted_subs) > 1:
            price_paid = sorted_subs[1]["bid"]
        else:
            price_paid = minimum_bid

        # Refund losing bidders
        for sub in sorted_subs[1:]:
            self._ledger.credit_scrip(sub["principal_id"], sub["bid"])

        # Winner pays second price (refund difference)
        refund_to_winner = winning_bid - price_paid
        if refund_to_winner > 0:
            self._ledger.credit_scrip(winner_id, refund_to_winner)

        # Clear held bids
        self._held_bids.clear()

        # Distribute UBI from price paid
        ubi_distribution = self._ledger.distribute_ubi(price_paid, exclude=winner_id)

        # Score the artifact
        score: int | None = None
        score_reason: str | None = None
        scrip_minted = 0
        error: str | None = None

        if _mock_score is not None:
            # Testing mode - use provided score
            score = _mock_score
            score_reason = "Mock score for testing"
            scrip_minted = score // self._mint_ratio
            if scrip_minted > 0:
                self.mint_scrip(winner_id, scrip_minted)
        else:
            # Production mode - use LLM scorer
            artifact = self._artifacts.get(artifact_id)
            if artifact:
                try:
                    from .mint_scorer import get_scorer
                    scorer = get_scorer()
                    score_result = scorer.score_artifact(
                        artifact_id=artifact_id,
                        artifact_type=artifact.type,
                        content=artifact.content,
                        is_budget_exhausted=self._is_budget_exhausted,
                    )

                    # Track scorer's LLM cost (Plan #153)
                    if self._track_api_cost is not None and hasattr(scorer, 'llm'):
                        if "cost" not in scorer.llm.last_usage:
                            logger.warning(
                                "Mint scorer LLM usage missing 'cost' field, defaulting to 0.0"
                            )
                        scorer_cost = scorer.llm.last_usage.get("cost", 0.0)
                        if scorer_cost > 0:
                            self._track_api_cost(scorer_cost)

                    if score_result["success"]:
                        score = score_result["score"]
                        score_reason = score_result.get("reason")
                        scrip_minted = score // self._mint_ratio
                        if scrip_minted > 0:
                            self.mint_scrip(winner_id, scrip_minted)
                    else:
                        error = score_result.get("error", "Scoring failed")
                except Exception as e:
                    error = f"Scoring error: {str(e)}"
            else:
                error = f"Artifact {artifact_id} not found"

        result = KernelMintResult(
            winner_id=winner_id,
            artifact_id=artifact_id,
            winning_bid=winning_bid,
            price_paid=price_paid,
            score=score,
            score_reason=score_reason,
            scrip_minted=scrip_minted,
            ubi_distributed=ubi_distribution,
            error=error,
            resolved_at=self.event_number,
        )
        self._history.append(result)

        # Clear submissions for next auction
        self._submissions.clear()

        self._logger.log("mint_auction_resolved", {
            "event_number": self.event_number,
            "winner_id": winner_id,
            "artifact_id": artifact_id,
            "winning_bid": winning_bid,
            "price_paid": price_paid,
            "score": score,
            "score_reason": score_reason,
            "scrip_minted": scrip_minted,
            "error": error,
        })

        return result


__all__ = [
    "MintAuction",
    "KernelMintSubmission",
    "KernelMintResult",
]
