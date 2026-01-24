# Gap 162: Contract Artifact Lookup

**Status:** 📋 Deferred
**Priority:** Low
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** Contract permission checks receive limited context:
- `caller` (ID string)
- `target_created_by` (who created the artifact being accessed)
- `method`, `args` (for invoke actions)
- `ledger` (read-only balance checks)

Contracts cannot look up metadata about the caller (creator, contract, custom fields).

**Target:** Contracts can query read-only artifact metadata to implement flexible trust patterns:
- Same creator ("trust sibling tools")
- Same contract ("trust fellow members")
- Vouched ("trust anyone Alice trusts")
- Reputation-based ("trust if reputation > N")
- Custom metadata checks

**Why Low:** Current primitives are sufficient for building coordination structures. This is an ergonomic optimization that reduces friction for certain trust patterns. No agent has yet needed this capability. Defer until a real use case emerges.

---

## Context

### Trust Patterns and What They Need

| Pattern | Example | Required Information |
|---------|---------|---------------------|
| Same creator | "Trust my sibling tools" | Caller's `created_by` |
| Same contract | "Trust fellow members" | Caller's `access_contract_id` |
| Explicit list | "Trust these 5 IDs" | Just caller ID (already have) |
| Vouched | "Trust anyone Alice trusts" | Read Alice's trust list artifact |
| Token-based | "Trust membership holders" | Caller's resources (have via ledger) |
| Reputation | "Trust if reputation > N" | Read caller's reputation artifact |

### Current Workarounds

1. **Hardcode IDs** - Contract lists trusted IDs explicitly (doesn't scale)
2. **Use resources as tokens** - Grant "membership" resource, check via ledger (works but adds friction)
3. **Freeware** - Trust everyone (too permissive)

### Security Consideration

If contracts can look up caller's `access_contract_id`, a malicious artifact could claim to use a trusted contract. The `caller_created_by` pattern is safer because creators can't be faked.

---

## Proposed Design (When Implemented)

### Option A: Add `caller_created_by` to context (Minimal)

```python
# In executor.py, when building context:
context = {
    "target_created_by": artifact.created_by,
    "caller_created_by": caller_artifact.created_by if caller_artifact else None,
}
```

Enables "same creator" pattern only. Safe and simple.

### Option B: Read-only artifact lookup (General)

```python
def check_permission(caller, action, target, context, ledger, artifacts):
    caller_info = artifacts.get(caller)  # Returns read-only artifact metadata
    # Contract can now check any artifact property
```

More powerful but larger surface area. Need to decide what fields are exposed.

### Recommendation

Start with Option A when a use case emerges. Expand to Option B if multiple patterns are needed.

---

## Files Affected (When Implemented)

- `src/world/executor.py` (modify) - Add to context or provide artifact lookup
- `src/world/contracts.py` (modify) - Update ExecutableContract signature
- `tests/unit/test_contracts.py` (modify) - Test new capability
- `docs/architecture/current/contracts.md` (modify) - Document new capability

---

## Deferred Because

1. No agent has requested this capability yet
2. Current workarounds exist (hardcoded lists, resource tokens)
3. Philosophy: "Observe, don't prevent" - wait for emergent need
4. Small change when needed (~20 lines for Option A)

---

## Trigger to Revisit

Implement when:
- An agent attempts to create a "firm" pattern and struggles with friction
- Multiple agents independently try to solve the same trust problem
- A plan requires cross-tool coordination that current primitives make awkward

---

## Notes

Discussion origin: Review of agent architecture and coordination primitives. Question was whether contracts can reduce friction for trusted interactions. Conclusion: Current system CAN build coordination structures; this is an ergonomic improvement that can wait for demonstrated need.
