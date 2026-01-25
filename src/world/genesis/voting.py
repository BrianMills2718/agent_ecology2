"""Genesis Voting - Multi-party consensus artifact

Enables agents to create proposals and vote on them.
Provides a convenience layer for common coordination patterns.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ...config import get_validated_config
from ...config_schema import GenesisConfig
from .base import GenesisArtifact


@dataclass
class Proposal:
    """A voting proposal."""

    id: str
    creator: str
    title: str
    description: str
    options: list[str]
    quorum: int  # Minimum votes required
    threshold: float  # Fraction needed to pass (0.0 - 1.0)
    deadline: float  # Unix timestamp when voting closes
    votes: dict[str, str] = field(default_factory=dict)  # voter_id -> choice
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if the proposal deadline has passed."""
        return time.time() > self.deadline

    def get_vote_counts(self) -> dict[str, int]:
        """Count votes for each option."""
        counts: dict[str, int] = {opt: 0 for opt in self.options}
        for choice in self.votes.values():
            if choice in counts:
                counts[choice] += 1
        return counts

    def get_status(self) -> str:
        """Determine proposal status: open, passed, rejected, expired."""
        vote_counts = self.get_vote_counts()
        total_votes = sum(vote_counts.values())

        # Check if expired
        if self.is_expired():
            if total_votes < self.quorum:
                return "expired"
            # Check if any option passed threshold
            for option, count in vote_counts.items():
                if total_votes > 0 and count / total_votes >= self.threshold:
                    return "passed"
            return "rejected"

        # Still open
        return "open"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        vote_counts = self.get_vote_counts()
        total_votes = sum(vote_counts.values())
        return {
            "proposal_id": self.id,
            "creator": self.creator,
            "title": self.title,
            "description": self.description,
            "options": self.options,
            "quorum": self.quorum,
            "threshold": self.threshold,
            "deadline": self.deadline,
            "created_at": self.created_at,
            "status": self.get_status(),
            "votes": vote_counts,
            "total_votes": total_votes,
            "quorum_reached": total_votes >= self.quorum,
        }


class GenesisVoting(GenesisArtifact):
    """Genesis artifact for multi-party voting and consensus.

    Enables agents to create proposals and vote on them.
    One vote per principal enforced.

    Methods:
    - create_proposal: Create a new proposal with configurable rules
    - vote: Cast a vote on a proposal
    - get_result: Get voting results for a proposal
    - list_proposals: List proposals with optional status filter
    """

    proposals: dict[str, Proposal]

    def __init__(self, genesis_config: GenesisConfig | None = None) -> None:
        """Initialize the voting artifact.

        Args:
            genesis_config: Optional genesis config (uses global if not provided)
        """
        cfg = genesis_config or get_validated_config().genesis
        voting_cfg = cfg.voting

        super().__init__(
            artifact_id=voting_cfg.id,
            description=voting_cfg.description
        )
        self.proposals = {}

        # Register methods with costs/descriptions from config
        self.register_method(
            name="create_proposal",
            handler=self._create_proposal,
            cost=voting_cfg.methods.create_proposal.cost,
            description=voting_cfg.methods.create_proposal.description
        )
        self.register_method(
            name="vote",
            handler=self._vote,
            cost=voting_cfg.methods.vote.cost,
            description=voting_cfg.methods.vote.description
        )
        self.register_method(
            name="get_result",
            handler=self._get_result,
            cost=voting_cfg.methods.get_result.cost,
            description=voting_cfg.methods.get_result.description
        )
        self.register_method(
            name="list_proposals",
            handler=self._list_proposals,
            cost=voting_cfg.methods.list_proposals.cost,
            description=voting_cfg.methods.list_proposals.description
        )

    def _create_proposal(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Create a new proposal.

        Args format: [config] where config is a dict with:
        - title: Proposal title (required)
        - description: Proposal description (optional, default "")
        - options: List of voting options (optional, default ["approve", "reject"])
        - quorum: Minimum votes required (optional, default 1)
        - threshold: Fraction needed to pass, 0.0-1.0 (optional, default 0.5)
        - deadline_seconds: Seconds until deadline (optional, default 3600)

        Returns:
            {"proposal_id": str, "status": "open"} on success
            {"success": False, "error": str} on failure
        """
        if not args or not isinstance(args[0], dict):
            return {
                "success": False,
                "error": "create_proposal requires [{title, description?, options?, quorum?, threshold?, deadline_seconds?}]"
            }

        config = args[0]

        # Validate required fields
        if "title" not in config:
            return {
                "success": False,
                "error": "Proposal title is required"
            }

        # Extract config with defaults
        title = str(config["title"])
        description = str(config.get("description", ""))
        options = config.get("options", ["approve", "reject"])
        quorum = int(config.get("quorum", 1))
        threshold = float(config.get("threshold", 0.5))
        deadline_seconds = float(config.get("deadline_seconds", 3600))

        # Validate options
        if not isinstance(options, list) or len(options) < 2:
            return {
                "success": False,
                "error": "Options must be a list with at least 2 choices"
            }

        # Validate threshold
        if not 0.0 <= threshold <= 1.0:
            return {
                "success": False,
                "error": "Threshold must be between 0.0 and 1.0"
            }

        # Validate quorum
        if quorum < 1:
            return {
                "success": False,
                "error": "Quorum must be at least 1"
            }

        # Create proposal
        proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
        deadline = time.time() + deadline_seconds

        proposal = Proposal(
            id=proposal_id,
            creator=invoker_id,
            title=title,
            description=description,
            options=options,
            quorum=quorum,
            threshold=threshold,
            deadline=deadline,
        )
        self.proposals[proposal_id] = proposal

        return {
            "success": True,
            "proposal_id": proposal_id,
            "status": "open",
            "deadline": deadline,
        }

    def _vote(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Cast a vote on a proposal.

        Args format: [config] where config is a dict with:
        - proposal_id: ID of the proposal to vote on (required)
        - choice: The voting choice (required, must be in proposal options)

        Returns:
            {"success": True, "votes_cast": int, "quorum_reached": bool} on success
            {"success": False, "error": str} on failure
        """
        if not args or not isinstance(args[0], dict):
            return {
                "success": False,
                "error": "vote requires [{proposal_id, choice}]"
            }

        config = args[0]

        # Validate required fields
        if "proposal_id" not in config or "choice" not in config:
            return {
                "success": False,
                "error": "Both proposal_id and choice are required"
            }

        proposal_id = str(config["proposal_id"])
        choice = str(config["choice"])

        # Get proposal
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return {
                "success": False,
                "error": f"Proposal not found: {proposal_id}"
            }

        # Check if expired
        if proposal.is_expired():
            return {
                "success": False,
                "error": "Proposal has expired"
            }

        # Check if already voted
        if invoker_id in proposal.votes:
            return {
                "success": False,
                "error": "Already voted on this proposal"
            }

        # Check if valid choice
        if choice not in proposal.options:
            return {
                "success": False,
                "error": f"Invalid choice. Options: {proposal.options}"
            }

        # Cast vote
        proposal.votes[invoker_id] = choice
        total_votes = len(proposal.votes)

        return {
            "success": True,
            "votes_cast": total_votes,
            "quorum_reached": total_votes >= proposal.quorum,
        }

    def _get_result(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get voting results for a proposal.

        Args format: [proposal_id]

        Returns:
            Proposal details including status and vote counts on success
            {"success": False, "error": str} on failure
        """
        if not args or len(args) < 1:
            return {
                "success": False,
                "error": "get_result requires [proposal_id]"
            }

        proposal_id = str(args[0])

        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return {
                "success": False,
                "error": f"Proposal not found: {proposal_id}"
            }

        result = proposal.to_dict()
        result["success"] = True
        return result

    def _list_proposals(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List proposals with optional status filter.

        Args format: [filter?] where filter is a dict with:
        - status: Filter by status (optional: "open", "passed", "rejected", "expired")
        - creator: Filter by creator (optional)
        - limit: Maximum results (optional, default 100)

        Returns:
            {"success": True, "proposals": list, "count": int}
        """
        filter_dict: dict[str, Any] = {}
        if args and isinstance(args[0], dict):
            filter_dict = args[0]

        status_filter = filter_dict.get("status")
        creator_filter = filter_dict.get("creator")
        limit = int(filter_dict.get("limit", 100))

        results = []
        for proposal in self.proposals.values():
            # Apply status filter
            if status_filter and proposal.get_status() != status_filter:
                continue

            # Apply creator filter
            if creator_filter and proposal.creator != creator_filter:
                continue

            results.append(proposal.to_dict())

            if len(results) >= limit:
                break

        return {
            "success": True,
            "proposals": results,
            "count": len(results),
        }

    def get_interface(self) -> dict[str, Any]:
        """Get detailed interface schema for the voting artifact (Plan #114)."""
        return {
            "description": self.description,
            "dataType": "service",
            "tools": [
                {
                    "name": "create_proposal",
                    "description": self.methods["create_proposal"].description,
                    "cost": self.methods["create_proposal"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Proposal title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Proposal description"
                            },
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of voting options (default: [approve, reject])"
                            },
                            "quorum": {
                                "type": "integer",
                                "description": "Minimum votes required (default: 1)",
                                "minimum": 1
                            },
                            "threshold": {
                                "type": "number",
                                "description": "Fraction needed to pass, 0.0-1.0 (default: 0.5)",
                                "minimum": 0.0,
                                "maximum": 1.0
                            },
                            "deadline_seconds": {
                                "type": "number",
                                "description": "Seconds until deadline (default: 3600)",
                                "minimum": 0
                            }
                        },
                        "required": ["title"]
                    }
                },
                {
                    "name": "vote",
                    "description": self.methods["vote"].description,
                    "cost": self.methods["vote"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "proposal_id": {
                                "type": "string",
                                "description": "ID of the proposal to vote on"
                            },
                            "choice": {
                                "type": "string",
                                "description": "The voting choice (must be in proposal options)"
                            }
                        },
                        "required": ["proposal_id", "choice"]
                    }
                },
                {
                    "name": "get_result",
                    "description": self.methods["get_result"].description,
                    "cost": self.methods["get_result"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "proposal_id": {
                                "type": "string",
                                "description": "ID of the proposal"
                            }
                        },
                        "required": ["proposal_id"]
                    }
                },
                {
                    "name": "list_proposals",
                    "description": self.methods["list_proposals"].description,
                    "cost": self.methods["list_proposals"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["open", "passed", "rejected", "expired"],
                                "description": "Filter by status"
                            },
                            "creator": {
                                "type": "string",
                                "description": "Filter by creator"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default: 100)",
                                "minimum": 1
                            }
                        }
                    }
                }
            ]
        }
