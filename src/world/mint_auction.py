"""Mint auction logic extracted from World (TD-001).

This module handles the mint auction system:
- Submit artifacts for mint consideration
- Track pending submissions and escrowed bids
- Resolve auctions (second-price, LLM scoring, UBI distribution)

Plan #44 - Kernel Mint Primitives
"""

from __future__ import annotations

import uuid
from typing import Any, TypedDict, TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .ledger import Ledger
    from .artifacts import ArtifactStore
    from .logger import EventLogger


class KernelMintSubmission(TypedDict):
    """A mint submission stored in kernel state (Plan #44)."""
    submission_id: str
    principal_id: str
    artifact_id: str
    bid: int
    tick_submitted: int


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
    tick_resolved: int


class MintAuction:
    """Manages mint auctions - artifact scoring and scrip minting.

    Extracted from World class to improve modularity (TD-001).

    Dependencies:
        ledger: For scrip operations (credit, deduct, distribute_ubi)
        artifacts: For artifact validation
        logger: For event logging
        get_tick: Callback to get current simulation tick
    """

    def __init__(
        self,
        ledger: Ledger,
        artifacts: ArtifactStore,
        logger: EventLogger,
        get_tick: Callable[[], int],
    ) -> None:
        """Initialize MintAuction.

        Args:
            ledger: Ledger for scrip operations
            artifacts: ArtifactStore for artifact validation
            logger: EventLogger for logging events
            get_tick: Callable that returns current tick
        """
        self._ledger = ledger
        self._artifacts = artifacts
        self._logger = logger
        self._get_tick = get_tick

        # Internal state
        self._submissions: dict[str, KernelMintSubmission] = {}
        self._held_bids: dict[str, int] = {}  # principal_id -> escrowed bid amount
        self._history: list[KernelMintResult] = []

        # Cost tracking callbacks (Plan #153)
        self._is_budget_exhausted: Callable[[], bool] | None = None
        self._track_api_cost: Callable[[float], None] | None = None

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
    def tick(self) -> int:
        """Current simulation tick."""
        return self._get_tick()

    def mint_scrip(self, principal_id: str, amount: int) -> None:
        """Mint new scrip for a principal.

        Scrip is the economic currency - minting adds purchasing power.

        Args:
            principal_id: Who receives the minted scrip
            amount: Amount to mint
        """
        self._ledger.credit_scrip(principal_id, amount)
        self._logger.log("mint", {
            "tick": self.tick,
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
        if artifact.created_by != principal_id:
            raise ValueError(f"Principal {principal_id} is not owner of {artifact_id}")
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
            "tick_submitted": self.tick,
        }

        self._logger.log("mint_submission", {
            "tick": self.tick,
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
            "tick": self.tick,
            "submission_id": submission_id,
            "principal_id": principal_id,
            "refunded": bid_amount,
        })

        return True

    def resolve(self, _mock_score: int | None = None) -> KernelMintResult:
        """Resolve the current mint auction.

        Called by tick advancement or manually for testing.
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
                "tick_resolved": self.tick,
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
            mint_ratio = 10  # Default, could come from config
            scrip_minted = score // mint_ratio
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
                        scorer_cost = scorer.llm.last_usage.get("cost", 0.0)
                        if scorer_cost > 0:
                            self._track_api_cost(scorer_cost)

                    if score_result["success"]:
                        score = score_result["score"]
                        score_reason = score_result.get("reason")
                        mint_ratio = 10  # Could come from config
                        scrip_minted = score // mint_ratio
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
            tick_resolved=self.tick,
        )
        self._history.append(result)

        # Clear submissions for next auction
        self._submissions.clear()

        self._logger.log("mint_auction_resolved", {
            "tick": self.tick,
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
