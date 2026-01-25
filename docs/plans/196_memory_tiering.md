# Plan #196: Memory Tiering

**Status:** ✅ Complete
**Created:** 2025-01-25
**Completed:** 2026-01-25
**Scope:** Agent Cognitive Autonomy

## Problem

All RAG memories are treated equally. When context is limited, the system retrieves the top N by semantic similarity. But agents might have:

- **Critical memories**: "NEVER transfer to agent_X (scammer)"
- **Strategic memories**: "My long-term goal is to build infrastructure"
- **Tactical memories**: "Last tick I started building a calculator"
- **Optional memories**: "Agent_Y mentioned they like trading"

An agent should be able to mark certain memories as "always include" regardless of semantic similarity.

## Solution

Add memory tiers that affect retrieval priority and inclusion guarantees.

### Memory Tiers

| Tier | Name | Behavior |
|------|------|----------|
| 0 | **Pinned** | Always included, regardless of query relevance |
| 1 | **Critical** | Strong boost in retrieval, rarely dropped |
| 2 | **Important** | Moderate boost in retrieval |
| 3 | **Normal** | Standard RAG behavior (default) |
| 4 | **Low** | Only included if space permits |

### New Actions

```yaml
store_memory:
  content: string
  tier: "pinned" | "critical" | "important" | "normal" | "low"  # default: normal

# Update existing memory tier
set_memory_tier:
  memory_id: string
  tier: "pinned" | "critical" | "important" | "normal" | "low"

# Pin a memory (shorthand)
pin_memory:
  memory_id: string

# Unpin a memory
unpin_memory:
  memory_id: string
```

### Retrieval Changes

```python
def get_relevant_memories(self, agent_id: str, query: str, limit: int = 5) -> str:
    # 1. Always include pinned memories
    pinned = self._get_pinned_memories(agent_id)

    # 2. Retrieve remaining with tier boost
    remaining_limit = limit - len(pinned)
    if remaining_limit > 0:
        # Apply tier-based boost to similarity scores
        results = self._search_with_tier_boost(agent_id, query, remaining_limit)
    else:
        results = []

    # 3. Combine and format
    return self._format_memories(pinned + results)

def _search_with_tier_boost(self, agent_id: str, query: str, limit: int):
    # Retrieve more candidates than needed
    candidates = self._raw_search(agent_id, query, limit * 3)

    # Apply tier boost to scores
    for mem in candidates:
        tier = mem.get("tier", 3)  # Default: normal
        boost = {0: 1.0, 1: 0.3, 2: 0.15, 3: 0.0, 4: -0.1}[tier]
        mem["boosted_score"] = mem["score"] + boost

    # Re-sort by boosted score
    candidates.sort(key=lambda m: m["boosted_score"], reverse=True)
    return candidates[:limit]
```

### Memory Metadata Storage

Mem0 supports metadata on add and search operations:

```python
# Add memory with tier metadata
memory.add(
    content,
    user_id=agent_id,
    metadata={"tier": 0, "created_tick": 42}
)

# Search with metadata filter for pinned
pinned = memory.search(
    query="",
    user_id=agent_id,
    filters={"tier": 0}
)
```

## Files Affected

- src/agents/memory.py (modify)
- src/config_schema.py (modify)
- config/schema.yaml (modify)
- config/config.yaml (modify)
- tests/unit/test_memory_tiering.py (create)
- tests/unit/test_memory.py (modify)
- docs/architecture/current/agents.md (modify)

## Implementation

### Design Decision: No New Action Types

To preserve the narrow waist (6 verbs + query), memory tiering is implemented
internally in the memory module. Agents don't need new action types - they can:
1. Use auto-recorded memories (actions/observations) at default tier
2. Write tier info to their working_memory artifact
3. Use invoke_artifact on memory artifacts if direct control needed

### Files to Modify

1. **src/agents/memory.py**
   - Add tier support to `add()` method (optional tier parameter with metadata)
   - Add `get_pinned_memories()` method
   - Modify `get_relevant_memories()` for tier-aware retrieval
   - Modify `search()` to support tier boosting

2. **config/schema.yaml** & **config/config.yaml**
   - `memory.max_pinned`: 5 (limit pinned memories)
   - `memory.tier_boosts.pinned`: 1.0
   - `memory.tier_boosts.critical`: 0.3
   - `memory.tier_boosts.important`: 0.15
   - `memory.tier_boosts.normal`: 0.0
   - `memory.tier_boosts.low`: -0.1

### Tier Limits

To prevent agents from marking everything as pinned:
- Maximum pinned memories: 5
- Maximum critical memories: 10
- No limit on other tiers

Attempting to exceed limit either:
1. Rejects new memory at that tier
2. Demotes oldest memory at that tier

## Design Considerations

### Tier vs Tags

Alternative approach: Tags instead of tiers
```python
store_memory:
  content: "..."
  tags: ["critical", "security", "learned-lesson"]
```

Tiers are simpler for now. Tags could be added later as orthogonal feature.

### Memory Expiration

Consider: Should pinned memories ever expire?
- Option A: Pinned = permanent (until unpinned)
- Option B: Pinned memories decay after N ticks if not accessed
- Option C: Agent must explicitly manage

Recommend Option A for simplicity.

### Interaction with Context Budget (Plan #195)

If RAG memories have a token budget:
1. Pinned memories consume budget first
2. If pinned exceeds budget, oldest pinned truncated (or error)
3. Remaining budget for similarity-based retrieval

## Testing

```bash
pytest tests/unit/test_memory_tiering.py -v
```

### Test Cases

1. Store memory with tier, verify retrieval priority
2. Pin memory, verify always included
3. Unpin memory, verify normal retrieval
4. Tier boost affects ranking
5. Max pinned limit enforced
6. Tier persists across checkpoint/restore

## Acceptance Criteria

- [ ] Agent can store memories with tier
- [ ] Pinned memories always included
- [ ] Tier boosts affect retrieval ranking
- [ ] Max pinned limit enforced
- [ ] Agent can update memory tier
- [ ] Tier metadata persisted with memory
