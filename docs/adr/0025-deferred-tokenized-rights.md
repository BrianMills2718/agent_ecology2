# ADR-0025: Deferred Tokenized Rights

**Status:** Accepted
**Date:** 2026-01-31
**Related:** Plan #166 (Resource Rights Model)

## Context

Plan #166 implemented rights-as-artifacts (tokenized rights) in Phases 3 and 5:
- `RightData` schema for dollar_budget, rate_capacity, disk_quota
- Creation, update, query functions
- Split/merge for composability
- Kernel interface methods for consumption

However, Phase 4 (kernel enforcement) was never completed. The `consume_from_*_right()` methods exist but are never called in production. All actual resource enforcement uses the ledger/quota system:
- `ledger.spend_resource("llm_budget", cost)`
- `world.get_available_capacity(agent_id, "disk")`

Additionally, the implementation lacks critical invariants for token soundness:
- `artifact.type` is mutable (allows forging type="right" artifacts)
- `artifact.content` is mutable via write/edit (allows inflating amounts)
- No `holder_id` field (ownership conflated with `created_by`)
- No atomic settlement (race conditions possible)

## Decision

**Defer tokenized rights.** Delete `src/world/rights.py` and related code. Continue using ledger/quota system for resource enforcement.

**Important clarification:** This removes *unused dead code*, not a rejected design. The rights-as-artifacts design is sound but incomplete. It is being quarantined because incomplete token systems are worse than no token system - they create false expectations of soundness.

## Naming Clarification

Two things share the word "rights" but are distinct:

| Concept | Location | Status | What it does |
|---------|----------|--------|--------------|
| **Registry/ledger quotas** | `genesis/rights_registry.py` | Active, kept | Authoritative enforcement via kernel quota primitives |
| **Tokenized rights** | `src/world/rights.py` (deleted) | Deferred | Market-like transferable instruments |

The registry manages how much budget/disk/rate an agent has via the ledger. Tokenized rights would have been transferable artifacts representing claims on those resources. The registry is unaffected by this deferral.

## Rationale

1. **Dead code** - The consume functions are never called. This creates cognitive overhead without benefit.

2. **Missing invariants** - Implementing token-sound rights requires:
   - Type immutability (kernel-enforced)
   - Block write/edit for right artifacts
   - Holder semantics distinct from provenance
   - Atomic settlement (locking in ArtifactStore)

   The atomicity requirement alone is a significant architectural change.

3. **Not needed yet** - No near-term use case for transferable budgets. The ledger system handles current needs.

4. **Reversible** - Design is preserved in Plan #166. Code is preserved in git history via annotated tag.

## Resumption Gate

All four invariants below are **pass/fail criteria** that must be met before tokenized rights can be wired into enforcement. Do not partially implement.

### 1. Type Immutability
Artifact type must not change after creation. Without this, any agent can forge a `type="right"` artifact.
```python
# In ArtifactStore.write():
if existing and existing.type != type:
    raise ValueError("Cannot change artifact type after creation")
```

### 2. No Direct Write/Edit for Right Balances
Right amounts must only be modified through kernel primitives, not agent write/edit actions. Without this, agents can inflate their own balances.
```python
# In action_executor._execute_write():
if existing and existing.type == "right":
    return ActionResult(success=False, message="Use kernel primitives for right artifacts")
```

### 3. Explicit Holder Model
The holder (who can spend/transfer) must be distinct from provenance (who created it). Without this, ownership transfer doesn't work correctly.
```python
@dataclass
class RightData:
    right_type: RightType
    resource: str
    amount: float
    holder_id: str  # Who can spend/transfer (distinct from created_by)
    # ...
```

### 4. Atomic Settlement
Check-debit-log must not interleave across concurrent calls. Add locking to ArtifactStore or implement compare-and-swap for right mutations.

## Design Decisions for Future Implementation

These questions were resolved during the deferral analysis. Record them here to prevent re-derivation:

**Q: Tokenized rights or tokenized budgets only?**
A: Start with tokenized budgets (scrip, LLM spend, disk quota). Arbitrary rights over artifacts are a separate, more complex concern that can build on top.

**Q: Can a holder be an artifact, or only a principal?**
A: Holder should be a principal (entity with standing/balance). Artifacts don't have standing. This aligns with the existing kernel model where `transfer_scrip` operates between principals.

**Q: What is the relationship between contracts and tokens?**
A: Contracts decide *permission* (yes/no to act). Tokens decide *capacity* (how much you can spend/consume). A contract might check that you hold a token, but the token itself is just a quantity claim. This maps cleanly to: contracts = access control (Plan #234), tokens = resource accounting.

## Restore Recipe

To recover the tokenized rights code:

```bash
# 1. Checkout from the annotated tag (stable across rebases)
git show token-rights-deferred-v1:src/world/rights.py > src/world/rights.py
git show token-rights-deferred-v1:tests/unit/test_rights.py > tests/unit/test_rights.py

# 2. Re-add kernel_interface.py methods (view for reference)
git show token-rights-deferred-v1:src/world/kernel_interface.py

# 3. Verify tests pass in isolation
pytest tests/unit/test_rights.py -v

# 4. BEFORE wiring into enforcement, implement all 4 resumption gate invariants
```

Tag: `token-rights-deferred-v1` (annotated, points to `8072654`)

Fallback commits (if tag is lost):
- `8072654` - [Plan #166] Add split/merge functions for rights trading (Phase 5)
- `8ca6695` - [Plan #166] Add rights module for rights-as-artifacts model (Phase 3)

PR references (stable across rebases):
- PR #683 - Phase 5 (split/merge)
- PR #678 - Phase 3 (rights module)

## Consequences

### Positive
- Removes ~800 lines of dead code
- Reduces cognitive overhead
- Clearer system: ledger/quotas for enforcement, no parallel "rights" system

### Negative
- Transferable budgets not available (markets, delegation, firms)
- Must re-implement if needed later

### Neutral
- `genesis/rights_registry.py` (quota management) is unaffected
- Design preserved for future implementation

## Alternatives Considered

### Alternative 1: Finish the implementation
Rejected because atomicity is hard and no near-term need.

### Alternative 2: Leave dead code in place
Rejected because dead code is worse than missing code - it creates false expectations of soundness that don't exist.

## Related

- Plan #166: Resource Rights Model (design reference)
- Plan #238: Defer Tokenized Rights (implementation of this ADR)
- Plan #235: Kernel-Protected Artifacts (provides invariant #1 and #2 when implemented)
- ADR-0019/ADR-0024: Permission architecture (context for access control)
