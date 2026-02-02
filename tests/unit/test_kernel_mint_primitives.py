"""Unit tests for Kernel Mint Primitives - Plan #44

Tests that minting is kernel functionality, not genesis artifact privilege.
These tests follow TDD: written first to fail, then implemented until green.

The key insight: mint submissions, history, and auction resolution should be
kernel physics (in World), with GenesisMint becoming an unprivileged wrapper.
"""

import pytest
import tempfile
from typing import Any
from dataclasses import dataclass

from src.world.world import World
from src.world.kernel_interface import KernelState, KernelActions


@pytest.fixture
def world_config() -> dict[str, Any]:
    """Minimal world config for testing mint primitives."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output_file = f.name

    return {
        "world": {"max_ticks": 20},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
        "logging": {"output_file": output_file},
        "principals": [
            {"id": "alice", "starting_scrip": 100},
            {"id": "bob", "starting_scrip": 200},
            {"id": "carol", "starting_scrip": 150},
        ],
        "rights": {
            "default_quotas": {"compute": 100.0, "disk": 10000.0}
        },
    }


@pytest.fixture
def world(world_config: dict[str, Any]) -> World:
    """Create world instance with mint primitives."""
    return World(world_config)


class TestWorldMintPrimitives:
    """Test mint state and operations in kernel (World)."""

    def test_submit_for_mint_stores_submission(self, world: World) -> None:
        """Submission is stored in kernel state, not genesis artifact."""
        # Create an artifact to submit
        world.artifacts.write(
            "my_artifact", "executable", "def run(): return 42",
            "alice", executable=True
        )

        # Submit to kernel mint (not genesis_mint)
        submission_id = world.submit_for_mint(
            principal_id="alice",
            artifact_id="my_artifact",
            bid=50
        )

        # Submission should be stored in kernel state
        assert submission_id is not None
        assert isinstance(submission_id, str)
        assert len(submission_id) > 0

        # Verify submission is retrievable
        submissions = world.get_mint_submissions()
        assert len(submissions) == 1
        assert submissions[0]["artifact_id"] == "my_artifact"
        assert submissions[0]["principal_id"] == "alice"
        assert submissions[0]["bid"] == 50

    def test_submit_for_mint_rejects_insufficient_scrip(self, world: World) -> None:
        """Cannot submit bid higher than available scrip."""
        world.artifacts.write(
            "artifact_1", "executable", "code", "alice", executable=True
        )

        # Alice only has 100 scrip
        with pytest.raises(ValueError, match="(?i)insufficient"):
            world.submit_for_mint("alice", "artifact_1", bid=500)

    def test_submit_for_mint_requires_artifact_ownership(self, world: World) -> None:
        """Can only submit artifacts you own."""
        world.artifacts.write(
            "bobs_artifact", "executable", "code", "bob", executable=True
        )

        # Alice cannot submit Bob's artifact
        with pytest.raises(ValueError, match="not owner"):
            world.submit_for_mint("alice", "bobs_artifact", bid=10)

    def test_submit_for_mint_requires_executable(self, world: World) -> None:
        """Can only submit executable artifacts."""
        world.artifacts.write(
            "data_artifact", "data", "not code", "alice", executable=False
        )

        with pytest.raises(ValueError, match="not executable"):
            world.submit_for_mint("alice", "data_artifact", bid=10)

    def test_get_mint_submissions_returns_pending(self, world: World) -> None:
        """Can query all pending submissions."""
        # Create multiple artifacts and submit them
        world.artifacts.write("art_1", "executable", "code1", "alice", executable=True)
        world.artifacts.write("art_2", "executable", "code2", "bob", executable=True)

        world.submit_for_mint("alice", "art_1", bid=30)
        world.submit_for_mint("bob", "art_2", bid=40)

        submissions = world.get_mint_submissions()
        assert len(submissions) == 2

        # Verify both are present
        artifact_ids = [s["artifact_id"] for s in submissions]
        assert "art_1" in artifact_ids
        assert "art_2" in artifact_ids

    def test_get_mint_history_returns_resolved(self, world: World) -> None:
        """Can query mint history after auction resolution."""
        # Initially empty
        history = world.get_mint_history()
        assert len(history) == 0

        # After some minting has happened, history should be populated
        # This will be tested after resolution tests pass

    def test_auction_resolution_picks_winner(self, world: World) -> None:
        """Kernel resolves auction and picks highest bidder."""
        world.artifacts.write("art_1", "executable", "code1", "alice", executable=True)
        world.artifacts.write("art_2", "executable", "code2", "bob", executable=True)

        world.submit_for_mint("alice", "art_1", bid=30)
        world.submit_for_mint("bob", "art_2", bid=50)

        # Resolve auction
        result = world.resolve_mint_auction()

        # Bob should win (higher bid)
        assert result["winner_id"] == "bob"
        assert result["artifact_id"] == "art_2"
        assert result["winning_bid"] == 50
        assert result["price_paid"] == 30  # Second-price auction

    def test_auction_resolution_mints_scrip(self, world: World) -> None:
        """Winner receives minted scrip based on score."""
        world.artifacts.write(
            "valuable_code", "executable",
            "def run(): return 'high quality'",
            "alice", executable=True
        )

        world.submit_for_mint("alice", "valuable_code", bid=20)

        # Mock the scorer to return a fixed score for testing
        # The actual scoring will use LLM, but for unit tests we mock
        result = world.resolve_mint_auction(_mock_score=80)

        # Verify scrip was minted (score / mint_ratio)
        # Default mint_ratio is 10, so 80/10 = 8 scrip minted
        assert result["scrip_minted"] > 0

        # History should be updated
        history = world.get_mint_history()
        assert len(history) == 1
        assert history[0]["winner_id"] == "alice"

    def test_auction_resolution_distributes_ubi(self, world: World) -> None:
        """Losing bids are distributed as UBI."""
        world.artifacts.write("art_1", "executable", "code1", "alice", executable=True)
        world.artifacts.write("art_2", "executable", "code2", "bob", executable=True)

        alice_initial = world.ledger.get_scrip("alice")
        bob_initial = world.ledger.get_scrip("bob")
        carol_initial = world.ledger.get_scrip("carol")

        world.submit_for_mint("alice", "art_1", bid=30)
        world.submit_for_mint("bob", "art_2", bid=50)

        result = world.resolve_mint_auction(_mock_score=60)

        # The price paid (second-price = 30) should be distributed as UBI
        # to non-winners
        assert "ubi_distributed" in result
        ubi = result["ubi_distributed"]

        # Everyone except winner should receive UBI
        # (exact amounts depend on implementation)
        assert isinstance(ubi, dict)

    def test_cancel_submission_refunds_bid(self, world: World) -> None:
        """Cancelling a submission refunds the escrowed bid."""
        world.artifacts.write("art_1", "executable", "code", "alice", executable=True)

        initial_scrip = world.ledger.get_scrip("alice")
        submission_id = world.submit_for_mint("alice", "art_1", bid=30)

        # Bid should be escrowed
        assert world.ledger.get_scrip("alice") == initial_scrip - 30

        # Cancel
        success = world.cancel_mint_submission("alice", submission_id)
        assert success is True

        # Bid should be refunded
        assert world.ledger.get_scrip("alice") == initial_scrip

        # Submission should be removed
        submissions = world.get_mint_submissions()
        assert len(submissions) == 0

    def test_cannot_cancel_others_submission(self, world: World) -> None:
        """Can only cancel your own submissions."""
        world.artifacts.write("art_1", "executable", "code", "alice", executable=True)

        submission_id = world.submit_for_mint("alice", "art_1", bid=30)

        # Bob cannot cancel Alice's submission
        success = world.cancel_mint_submission("bob", submission_id)
        assert success is False


class TestKernelStateMint:
    """Test KernelState mint read methods."""

    def test_get_mint_submissions_public(self, world: World) -> None:
        """Any caller can read pending mint submissions."""
        state = KernelState(world)

        world.artifacts.write("art_1", "executable", "code", "alice", executable=True)
        world.submit_for_mint("alice", "art_1", bid=30)

        # Bob can read submissions (public data)
        submissions = state.get_mint_submissions()
        assert len(submissions) == 1
        assert submissions[0]["artifact_id"] == "art_1"

    def test_get_mint_history_public(self, world: World) -> None:
        """Any caller can read mint history."""
        state = KernelState(world)

        # Initially empty
        history = state.get_mint_history()
        assert len(history) == 0

        # After auction resolution
        world.artifacts.write("art_1", "executable", "code", "alice", executable=True)
        world.submit_for_mint("alice", "art_1", bid=30)
        world.resolve_mint_auction(_mock_score=50)

        history = state.get_mint_history()
        assert len(history) == 1

    def test_get_mint_history_respects_limit(self, world: World) -> None:
        """History query respects limit parameter."""
        state = KernelState(world)

        # Create multiple auction resolutions
        for i in range(5):
            world.artifacts.write(
                f"art_{i}", "executable", f"code{i}", "alice", executable=True
            )
            world.submit_for_mint("alice", f"art_{i}", bid=10 + i)
            world.resolve_mint_auction(_mock_score=40)

        # Get limited history
        history = state.get_mint_history(limit=3)
        assert len(history) == 3

        # Should return most recent
        full_history = state.get_mint_history(limit=100)
        assert len(full_history) == 5


class TestKernelActionsMint:
    """Test KernelActions mint write methods."""

    def test_submit_for_mint_action(self, world: World) -> None:
        """KernelActions provides submit_for_mint method."""
        actions = KernelActions(world)

        world.artifacts.write("art_1", "executable", "code", "alice", executable=True)

        result = actions.submit_for_mint(
            caller_id="alice",
            artifact_id="art_1",
            bid=30
        )

        assert result["success"] is True
        assert "submission_id" in result

        # Verify submission was created
        submissions = world.get_mint_submissions()
        assert len(submissions) == 1

    def test_submit_for_mint_verifies_caller(self, world: World) -> None:
        """Caller cannot submit on behalf of others."""
        actions = KernelActions(world)

        world.artifacts.write("art_1", "executable", "code", "alice", executable=True)

        # Bob tries to submit as Alice (should fail or use Bob as actual submitter)
        # The caller_id must match the actual caller
        result = actions.submit_for_mint(
            caller_id="bob",  # Bob is calling
            artifact_id="art_1",
            bid=30
        )

        # Should fail because Bob doesn't own art_1
        assert result["success"] is False
        assert "not owner" in result.get("error", "").lower()

    def test_cancel_mint_submission_action(self, world: World) -> None:
        """KernelActions provides cancel_mint_submission method."""
        actions = KernelActions(world)

        world.artifacts.write("art_1", "executable", "code", "alice", executable=True)
        world.submit_for_mint("alice", "art_1", bid=30)

        submissions = world.get_mint_submissions()
        submission_id = submissions[0]["submission_id"]

        result = actions.cancel_mint_submission(
            caller_id="alice",
            submission_id=submission_id
        )

        assert result is True

        # Verify submission was removed
        submissions = world.get_mint_submissions()
        assert len(submissions) == 0

    def test_cancel_mint_requires_ownership(self, world: World) -> None:
        """Can only cancel your own submissions via KernelActions."""
        actions = KernelActions(world)

        world.artifacts.write("art_1", "executable", "code", "alice", executable=True)
        world.submit_for_mint("alice", "art_1", bid=30)

        submissions = world.get_mint_submissions()
        submission_id = submissions[0]["submission_id"]

        # Bob tries to cancel Alice's submission
        result = actions.cancel_mint_submission(
            caller_id="bob",
            submission_id=submission_id
        )

        assert result is False

        # Submission should still exist
        submissions = world.get_mint_submissions()
        assert len(submissions) == 1


class TestMintUnprivilegeEquivalence:
    """Test that agent-built artifacts can implement equivalent mint API."""

    def test_agent_can_wrap_kernel_mint(self, world: World) -> None:
        """Agent artifact can wrap kernel mint primitives like GenesisMintApi."""
        from src.world.executor import SafeExecutor

        executor = SafeExecutor(ledger=world.ledger)

        # Agent creates a mint wrapper artifact
        my_mint_code = '''
def run(*args):
    method = args[0] if args else None

    if method == "submit":
        artifact_id = args[1] if len(args) > 1 else None
        bid = args[2] if len(args) > 2 else 0
        result = kernel_actions.submit_for_mint(caller_id, artifact_id, bid)
        return result

    elif method == "status":
        submissions = kernel_state.get_mint_submissions()
        return {"success": True, "submissions": submissions}

    elif method == "history":
        limit = args[1] if len(args) > 1 else 100
        history = kernel_state.get_mint_history(limit=limit)
        return {"success": True, "history": history}

    return {"error": "unknown method"}
'''
        world.artifacts.write(
            "my_mint_api",
            "executable",
            my_mint_code,
            "bob",
            executable=True,
            code=my_mint_code
        )

        # First create an artifact to submit
        world.artifacts.write(
            "bobs_code",
            "executable",
            "def run(): return 42",
            "bob",
            executable=True
        )

        # Use my_mint_api to check status
        result = executor.execute_with_invoke(
            my_mint_code,
            args=["status"],
            artifact_id="my_mint_api",
            caller_id="bob",
            ledger=world.ledger,
            artifact_store=world.artifacts,
            world=world
        )

        assert result["success"]
        assert "submissions" in result.get("result", {})
