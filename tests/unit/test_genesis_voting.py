"""Unit tests for Plan #183: Genesis Voting artifact."""

import time

import pytest

from src.world.genesis.voting import GenesisVoting, Proposal


class TestProposal:
    """Tests for the Proposal dataclass."""

    def test_proposal_defaults(self) -> None:
        """Proposal has correct default values."""
        proposal = Proposal(
            id="prop_001",
            creator="alice",
            title="Test proposal",
            description="A test",
            options=["yes", "no"],
            quorum=2,
            threshold=0.5,
            deadline=time.time() + 3600,
        )
        assert proposal.votes == {}
        assert proposal.created_at > 0

    def test_is_expired_false(self) -> None:
        """Proposal is not expired when deadline is in future."""
        proposal = Proposal(
            id="prop_001",
            creator="alice",
            title="Test",
            description="",
            options=["yes", "no"],
            quorum=1,
            threshold=0.5,
            deadline=time.time() + 3600,  # 1 hour from now
        )
        assert proposal.is_expired() is False

    def test_is_expired_true(self) -> None:
        """Proposal is expired when deadline is in past."""
        proposal = Proposal(
            id="prop_001",
            creator="alice",
            title="Test",
            description="",
            options=["yes", "no"],
            quorum=1,
            threshold=0.5,
            deadline=time.time() - 1,  # 1 second ago
        )
        assert proposal.is_expired() is True

    def test_get_vote_counts(self) -> None:
        """Vote counts are calculated correctly."""
        proposal = Proposal(
            id="prop_001",
            creator="alice",
            title="Test",
            description="",
            options=["yes", "no", "abstain"],
            quorum=3,
            threshold=0.5,
            deadline=time.time() + 3600,
        )
        proposal.votes["alice"] = "yes"
        proposal.votes["bob"] = "yes"
        proposal.votes["charlie"] = "no"

        counts = proposal.get_vote_counts()
        assert counts == {"yes": 2, "no": 1, "abstain": 0}

    def test_get_status_open(self) -> None:
        """Status is 'open' when not expired and no decision reached."""
        proposal = Proposal(
            id="prop_001",
            creator="alice",
            title="Test",
            description="",
            options=["yes", "no"],
            quorum=3,
            threshold=0.5,
            deadline=time.time() + 3600,
        )
        proposal.votes["alice"] = "yes"
        assert proposal.get_status() == "open"

    def test_get_status_expired_no_quorum(self) -> None:
        """Status is 'expired' when deadline passed without quorum."""
        proposal = Proposal(
            id="prop_001",
            creator="alice",
            title="Test",
            description="",
            options=["yes", "no"],
            quorum=3,
            threshold=0.5,
            deadline=time.time() - 1,  # Expired
        )
        proposal.votes["alice"] = "yes"  # Only 1 vote, quorum is 3
        assert proposal.get_status() == "expired"

    def test_get_status_passed(self) -> None:
        """Status is 'passed' when threshold reached after expiry."""
        proposal = Proposal(
            id="prop_001",
            creator="alice",
            title="Test",
            description="",
            options=["yes", "no"],
            quorum=2,
            threshold=0.5,
            deadline=time.time() - 1,  # Expired
        )
        proposal.votes["alice"] = "yes"
        proposal.votes["bob"] = "yes"  # 2/2 = 100% > 50%
        assert proposal.get_status() == "passed"

    def test_get_status_rejected(self) -> None:
        """Status is 'rejected' when quorum met but threshold not reached."""
        proposal = Proposal(
            id="prop_001",
            creator="alice",
            title="Test",
            description="",
            options=["yes", "no"],
            quorum=2,
            threshold=0.7,  # Need 70%
            deadline=time.time() - 1,  # Expired
        )
        proposal.votes["alice"] = "yes"
        proposal.votes["bob"] = "no"  # 50% < 70%
        assert proposal.get_status() == "rejected"


class TestGenesisVoting:
    """Tests for the GenesisVoting artifact."""

    @pytest.fixture
    def voting(self) -> GenesisVoting:
        """Create a GenesisVoting instance."""
        return GenesisVoting()

    def test_create_proposal_success(self, voting: GenesisVoting) -> None:
        """Create proposal with valid config succeeds."""
        result = voting._create_proposal(
            [{"title": "Test proposal", "description": "A test"}],
            "alice"
        )
        assert result["success"] is True
        assert "proposal_id" in result
        assert result["status"] == "open"
        assert result["proposal_id"].startswith("prop_")

    def test_create_proposal_with_options(self, voting: GenesisVoting) -> None:
        """Create proposal with custom options."""
        result = voting._create_proposal(
            [{
                "title": "Choose option",
                "options": ["a", "b", "c"],
                "quorum": 5,
                "threshold": 0.6,
            }],
            "alice"
        )
        assert result["success"] is True
        proposal = voting.proposals[result["proposal_id"]]
        assert proposal.options == ["a", "b", "c"]
        assert proposal.quorum == 5
        assert proposal.threshold == 0.6

    def test_create_proposal_missing_title(self, voting: GenesisVoting) -> None:
        """Create proposal without title fails."""
        result = voting._create_proposal([{"description": "No title"}], "alice")
        assert result["success"] is False
        assert "title is required" in result["error"]

    def test_create_proposal_invalid_options(self, voting: GenesisVoting) -> None:
        """Create proposal with single option fails."""
        result = voting._create_proposal(
            [{"title": "Test", "options": ["only_one"]}],
            "alice"
        )
        assert result["success"] is False
        assert "at least 2 choices" in result["error"]

    def test_create_proposal_invalid_threshold(self, voting: GenesisVoting) -> None:
        """Create proposal with threshold > 1.0 fails."""
        result = voting._create_proposal(
            [{"title": "Test", "threshold": 1.5}],
            "alice"
        )
        assert result["success"] is False
        assert "between 0.0 and 1.0" in result["error"]

    def test_vote_success(self, voting: GenesisVoting) -> None:
        """Voting on open proposal succeeds."""
        create_result = voting._create_proposal(
            [{"title": "Test"}],
            "alice"
        )
        proposal_id = create_result["proposal_id"]

        vote_result = voting._vote(
            [{"proposal_id": proposal_id, "choice": "approve"}],
            "bob"
        )
        assert vote_result["success"] is True
        assert vote_result["votes_cast"] == 1
        assert voting.proposals[proposal_id].votes["bob"] == "approve"

    def test_vote_invalid_choice(self, voting: GenesisVoting) -> None:
        """Voting with invalid choice fails."""
        create_result = voting._create_proposal(
            [{"title": "Test", "options": ["yes", "no"]}],
            "alice"
        )
        proposal_id = create_result["proposal_id"]

        vote_result = voting._vote(
            [{"proposal_id": proposal_id, "choice": "maybe"}],
            "bob"
        )
        assert vote_result["success"] is False
        assert "Invalid choice" in vote_result["error"]

    def test_vote_double_vote_prevented(self, voting: GenesisVoting) -> None:
        """Same principal cannot vote twice."""
        create_result = voting._create_proposal(
            [{"title": "Test"}],
            "alice"
        )
        proposal_id = create_result["proposal_id"]

        # First vote
        voting._vote([{"proposal_id": proposal_id, "choice": "approve"}], "bob")

        # Second vote
        second_result = voting._vote(
            [{"proposal_id": proposal_id, "choice": "reject"}],
            "bob"
        )
        assert second_result["success"] is False
        assert "Already voted" in second_result["error"]

    def test_vote_on_expired_proposal(self, voting: GenesisVoting) -> None:
        """Voting on expired proposal fails."""
        create_result = voting._create_proposal(
            [{"title": "Test", "deadline_seconds": 0}],  # Immediately expires
            "alice"
        )
        proposal_id = create_result["proposal_id"]

        # Wait a tiny bit to ensure expiry
        import time
        time.sleep(0.01)

        vote_result = voting._vote(
            [{"proposal_id": proposal_id, "choice": "approve"}],
            "bob"
        )
        assert vote_result["success"] is False
        assert "expired" in vote_result["error"]

    def test_vote_nonexistent_proposal(self, voting: GenesisVoting) -> None:
        """Voting on nonexistent proposal fails."""
        vote_result = voting._vote(
            [{"proposal_id": "prop_nonexistent", "choice": "approve"}],
            "bob"
        )
        assert vote_result["success"] is False
        assert "not found" in vote_result["error"]

    def test_get_result_success(self, voting: GenesisVoting) -> None:
        """Get result returns proposal details."""
        create_result = voting._create_proposal(
            [{"title": "Test", "description": "Details"}],
            "alice"
        )
        proposal_id = create_result["proposal_id"]

        voting._vote([{"proposal_id": proposal_id, "choice": "approve"}], "bob")

        result = voting._get_result([proposal_id], "anyone")
        assert result["success"] is True
        assert result["proposal_id"] == proposal_id
        assert result["title"] == "Test"
        assert result["description"] == "Details"
        assert result["votes"]["approve"] == 1
        assert result["total_votes"] == 1

    def test_get_result_nonexistent(self, voting: GenesisVoting) -> None:
        """Get result for nonexistent proposal fails."""
        result = voting._get_result(["prop_nonexistent"], "anyone")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_list_proposals_all(self, voting: GenesisVoting) -> None:
        """List proposals returns all proposals."""
        voting._create_proposal([{"title": "Proposal 1"}], "alice")
        voting._create_proposal([{"title": "Proposal 2"}], "bob")

        result = voting._list_proposals([], "anyone")
        assert result["success"] is True
        assert result["count"] == 2

    def test_list_proposals_by_status(self, voting: GenesisVoting) -> None:
        """List proposals filters by status."""
        # Create an open proposal
        voting._create_proposal([{"title": "Open one"}], "alice")

        # Create an expired proposal
        voting._create_proposal(
            [{"title": "Expired one", "deadline_seconds": 0}],
            "bob"
        )
        import time
        time.sleep(0.01)  # Let it expire

        result = voting._list_proposals([{"status": "open"}], "anyone")
        assert result["success"] is True
        assert result["count"] == 1
        assert result["proposals"][0]["title"] == "Open one"

    def test_list_proposals_by_creator(self, voting: GenesisVoting) -> None:
        """List proposals filters by creator."""
        voting._create_proposal([{"title": "Alice's"}], "alice")
        voting._create_proposal([{"title": "Bob's"}], "bob")

        result = voting._list_proposals([{"creator": "alice"}], "anyone")
        assert result["success"] is True
        assert result["count"] == 1
        assert result["proposals"][0]["title"] == "Alice's"

    def test_list_proposals_with_limit(self, voting: GenesisVoting) -> None:
        """List proposals respects limit."""
        for i in range(5):
            voting._create_proposal([{"title": f"Proposal {i}"}], "alice")

        result = voting._list_proposals([{"limit": 3}], "anyone")
        assert result["success"] is True
        assert result["count"] == 3

    def test_quorum_reached_indicator(self, voting: GenesisVoting) -> None:
        """Quorum reached is correctly indicated."""
        create_result = voting._create_proposal(
            [{"title": "Test", "quorum": 2}],
            "alice"
        )
        proposal_id = create_result["proposal_id"]

        # First vote - quorum not reached
        result1 = voting._vote(
            [{"proposal_id": proposal_id, "choice": "approve"}],
            "bob"
        )
        assert result1["quorum_reached"] is False

        # Second vote - quorum reached
        result2 = voting._vote(
            [{"proposal_id": proposal_id, "choice": "approve"}],
            "charlie"
        )
        assert result2["quorum_reached"] is True

    def test_get_interface(self, voting: GenesisVoting) -> None:
        """Interface schema includes all methods."""
        interface = voting.get_interface()
        assert "tools" in interface
        tool_names = {t["name"] for t in interface["tools"]}
        assert tool_names == {"create_proposal", "vote", "get_result", "list_proposals"}


class TestVotingIntegration:
    """Integration tests for voting workflows."""

    @pytest.fixture
    def voting(self) -> GenesisVoting:
        """Create a GenesisVoting instance."""
        return GenesisVoting()

    def test_full_voting_workflow(self, voting: GenesisVoting) -> None:
        """Complete voting workflow from creation to result."""
        # Create proposal
        create_result = voting._create_proposal(
            [{
                "title": "Upgrade infrastructure",
                "description": "Proposal to refactor genesis_store",
                "options": ["approve", "reject", "abstain"],
                "quorum": 3,
                "threshold": 0.5,
            }],
            "alice"
        )
        proposal_id = create_result["proposal_id"]
        assert create_result["success"] is True

        # Cast votes
        voting._vote([{"proposal_id": proposal_id, "choice": "approve"}], "alice")
        voting._vote([{"proposal_id": proposal_id, "choice": "approve"}], "bob")
        voting._vote([{"proposal_id": proposal_id, "choice": "reject"}], "charlie")

        # Check result while still open
        result = voting._get_result([proposal_id], "anyone")
        assert result["status"] == "open"
        assert result["votes"]["approve"] == 2
        assert result["votes"]["reject"] == 1
        assert result["quorum_reached"] is True

    def test_proposal_passes_on_expiry(self, voting: GenesisVoting) -> None:
        """Proposal passes when threshold met after deadline."""
        create_result = voting._create_proposal(
            [{
                "title": "Quick vote",
                "quorum": 2,
                "threshold": 0.5,
                "deadline_seconds": 0.01,
            }],
            "alice"
        )
        proposal_id = create_result["proposal_id"]

        # Vote before expiry
        voting._vote([{"proposal_id": proposal_id, "choice": "approve"}], "alice")
        voting._vote([{"proposal_id": proposal_id, "choice": "approve"}], "bob")

        # Wait for expiry
        import time
        time.sleep(0.02)

        result = voting._get_result([proposal_id], "anyone")
        assert result["status"] == "passed"
