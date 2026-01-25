# Plan #183: Genesis Voting Artifact

**Status:** ✅ Complete

**Verified:** 2026-01-25T05:30:00Z
**Verification Evidence:**
```yaml
completed_by: Implementation
timestamp: 2026-01-25T05:30:00Z
notes: |
  - Created GenesisVoting artifact with proposal/vote/result methods
  - Supports configurable quorum, threshold, and deadline
  - One vote per principal enforced
  - Status tracking: open, passed, rejected, expired
tests:
  unit: 28 tests in test_genesis_voting.py
  integration: Full test suite passes (2292 tests)
```

**Priority:** Low
**Complexity:** Low
**Blocks:** None (convenience feature)

## Problem

Consensus/voting patterns require building a contract from scratch. While this is possible with current primitives, it adds friction for a common coordination pattern.

## Solution

Provide `genesis_voting` as a convenience artifact for multi-party decisions.

### Interface

```python
genesis_voting.create_proposal([{
    "title": "Upgrade shared infrastructure",
    "description": "Proposal to refactor genesis_store",
    "options": ["approve", "reject", "abstain"],
    "quorum": 3,  # Minimum votes required
    "threshold": 0.5,  # Fraction needed to pass
    "deadline_seconds": 3600  # Optional timeout
}])
# Returns: {"proposal_id": "prop_001", "status": "open"}

genesis_voting.vote([{
    "proposal_id": "prop_001",
    "choice": "approve"
}])
# Returns: {"success": true, "votes_cast": 2, "quorum_reached": false}

genesis_voting.get_result(["prop_001"])
# Returns: {
#     "proposal_id": "prop_001",
#     "status": "passed",  # open, passed, rejected, expired
#     "votes": {"approve": 3, "reject": 1, "abstain": 0},
#     "quorum_reached": true
# }

genesis_voting.list_proposals([{"status": "open"}])
# Returns list of active proposals
```

### Features

1. **One vote per principal** - Enforced by contract
2. **Configurable quorum** - Minimum participation required
3. **Configurable threshold** - Fraction needed to pass
4. **Optional deadline** - Auto-expire proposals
5. **Vote privacy** - Option to hide votes until closed
6. **Weighted voting** - Optional: votes weighted by balance/stake

### Implementation

```python
class GenesisVoting(GenesisArtifact):
    def __init__(self, ...):
        self.proposals: dict[str, Proposal] = {}

    def _create_proposal(self, args, invoker_id):
        config = args[0]
        proposal_id = f"prop_{uuid4().hex[:8]}"
        self.proposals[proposal_id] = Proposal(
            creator=invoker_id,
            title=config["title"],
            options=config["options"],
            quorum=config.get("quorum", 1),
            threshold=config.get("threshold", 0.5),
            deadline=time.time() + config.get("deadline_seconds", float("inf")),
            votes={}
        )
        return {"proposal_id": proposal_id, "status": "open"}

    def _vote(self, args, invoker_id):
        proposal_id, choice = args[0]["proposal_id"], args[0]["choice"]
        proposal = self.proposals.get(proposal_id)

        if not proposal:
            return {"success": False, "error": "Proposal not found"}
        if invoker_id in proposal.votes:
            return {"success": False, "error": "Already voted"}
        if choice not in proposal.options:
            return {"success": False, "error": f"Invalid choice. Options: {proposal.options}"}
        if time.time() > proposal.deadline:
            return {"success": False, "error": "Proposal expired"}

        proposal.votes[invoker_id] = choice
        return {
            "success": True,
            "votes_cast": len(proposal.votes),
            "quorum_reached": len(proposal.votes) >= proposal.quorum
        }
```

### Storage

Proposals stored as sub-artifacts or in genesis_voting's own state. Queryable via genesis_store.

## Testing

- Create proposal, multiple agents vote, verify result
- Test quorum not reached
- Test threshold not met
- Test double-vote prevention
- Test deadline expiration

## Acceptance Criteria

1. Agents can create proposals with configurable rules
2. One vote per principal enforced
3. Results computed correctly (quorum, threshold)
4. Proposals queryable via genesis_store

## Future Enhancements

- Weighted voting by stake
- Delegation (vote on behalf of)
- Multi-round voting (runoff)
- On-chain style proposal execution (auto-invoke on pass)
