# Plan 164: Artifact Dependency Tracking

**Status:** Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Problem Statement

Agents and operators have no easy way to understand artifact relationships:

1. **What does artifact X call?** - Understanding behavior without reading code
2. **What calls artifact X?** - Finding usage examples, assessing adoption

Currently, invocation relationships are logged in event_log but not easily queryable. Static dependencies (what an artifact's code COULD invoke) aren't tracked at all.

---

## Use Cases

### For Agents

- **Understand behavior**: "What does `trading_bot` actually invoke?" → `[genesis_ledger, genesis_escrow, price_oracle]`
- **Learn by example**: "What artifacts use `genesis_web_search`?" → Find proven patterns
- **Assess trust**: Widely-used artifacts may be more reliable

### For Operators

- **Visualize structure**: See how artifacts are connected
- **Impact analysis**: What breaks if I change artifact X?
- **Debug permission chains**: Why did this invocation fail?

---

## Solution

### Phase 1: Static Outbound Dependencies

When an artifact with code is written, automatically extract `invoke()` targets:

```python
# On write_artifact:
if artifact.can_execute:
    deps = extract_invoke_targets(artifact.content)
    artifact.metadata["invokes"] = deps  # e.g., ["genesis_ledger", "genesis_escrow"]
```

**Extraction approach**: Simple regex or AST parse for `invoke("artifact_id",` patterns.

**Storage**: In artifact metadata (already exists, just add field).

**Query**: Via `genesis_store.get()` or direct artifact read - no new methods needed.

### Phase 2: Runtime Inbound Dependencies

Query event_log for "what has invoked artifact X":

```python
genesis_event_log.get_invokers(artifact_id) -> list[str]
# Returns: ["alice", "trading_bot", "market_maker"]
```

**Data source**: Event log already records invocations.

**New method**: Add query method to genesis_event_log.

### Phase 3: Kernel Permission Chain Query (Optional)

For debugging permission failures:

```python
world.get_permission_chain(artifact_id, action) -> list[str]
# Returns: ["genesis_contract_freeware"] or deeper chain
```

**Kernel-level**: Not privileging any artifact.

---

## Design Principles

1. **Zero friction**: Normal invoke/write unchanged
2. **Automatic**: Static deps extracted on write, no agent action needed
3. **Optional query**: Agents use if helpful, ignore if not
4. **No new required fields**: Purely additive metadata

---

## Implementation

### Files to Modify

- `src/world/artifacts.py` - Extract deps on write, store in metadata
- `src/world/genesis/event_log.py` - Add `get_invokers()` query method
- `src/world/world.py` - Add `get_permission_chain()` (Phase 3)

### Extraction Logic

```python
import re

def extract_invoke_targets(code: str) -> list[str]:
    """Extract artifact IDs from invoke() calls in code."""
    # Match: invoke("artifact_id", ...) or invoke('artifact_id', ...)
    pattern = r'invoke\s*\(\s*["\']([^"\']+)["\']'
    return list(set(re.findall(pattern, code)))
```

**Limitation**: Misses dynamic targets like `invoke(variable, ...)`. This is acceptable - we capture the common case.

---

## Success Criteria

1. Writing executable artifact auto-populates `metadata.invokes`
2. `genesis_store.get(artifact_id)` includes invokes list
3. `genesis_event_log.get_invokers(artifact_id)` returns callers
4. No changes required to existing agent code

---

## Open Questions

1. Should we track invocation frequency? (X called Y 47 times)
2. Should we distinguish successful vs failed invocations?
3. Should `invokes` be updated if artifact code is edited?

---

## Notes

Emerged from architecture review discussion about observability and understanding artifact relationships without reading code.
