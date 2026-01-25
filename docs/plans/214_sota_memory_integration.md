# Plan #214: SOTA Memory Integration

**Status:** 🚧 In Progress
**Priority:** High
**Complexity:** Medium
**Blocks:** Effective agent learning and strategic behavior

## Problem

Genesis agents have SOTA memory infrastructure (genesis_embedder, genesis_memory with semantic search) but don't use it. Current "RAG" is just recency + tier boosting with query ignored.

## Discovery

The infrastructure **already exists** (Plan #146):
- `genesis_embedder` - LiteLLM embeddings (1 scrip/call)
- `genesis_memory` - Semantic search with cosine similarity
- Full cost model integration

But agents don't use it because:
1. `ArtifactMemory.search()` ignores the query (no semantic search)
2. `Agent._search_longterm_memory_artifact()` uses keyword fallback
3. Genesis agents don't have `longterm_memory_artifact_id` configured
4. Memory artifacts created at init are wrong type (`{agent_id}_memory` not `memory_store`)

## Solution

Wire up genesis agents to use the existing semantic memory infrastructure.

### Phase 1: Auto-Create Longterm Memory Artifacts

**File:** `src/simulation/runner.py`

Create `memory_store` type artifacts for genesis agents at simulation start.

### Phase 2: Add World Reference to Agents

**File:** `src/agents/agent.py`

Add `_world` field and `set_world()` method for semantic memory access.

### Phase 3: Enable Semantic Search

**File:** `src/agents/agent.py`

Modify `_search_longterm_memory_artifact()` to invoke `genesis_memory.search`.

### Phase 4: Add Memory Storage Trait

**File:** `src/agents/_components/traits/semantic_memory.yaml` (NEW)

Trait that guides agents to use semantic memory for long-term learning.

### Phase 5: Update Genesis Agent Configs

Add `semantic_memory` trait to alpha_3, beta_3, delta_3.

## Files Modified

| File | Change |
|------|--------|
| `src/simulation/runner.py` | Auto-create longterm memory, wire world reference |
| `src/agents/agent.py` | Add `_world` field, modify `_search_longterm_memory_artifact()` |
| `src/agents/_components/traits/semantic_memory.yaml` | NEW - trait for memory guidance |
| `src/agents/alpha_3/agent.yaml` | Add semantic_memory trait |
| `src/agents/beta_3/agent.yaml` | Add semantic_memory trait |
| `src/agents/delta_3/agent.yaml` | Add semantic_memory trait |

## What This Does NOT Change

- `genesis_memory.py` - Already complete
- `genesis_embedder.py` - Already complete
- `memory.py` - ArtifactMemory stays as-is (fallback)
- Architecture - Just wiring, no new primitives

## Verification

1. Run simulation: `make run DURATION=300 AGENTS=3`
2. Check logs for "genesis_memory.search" invocations
3. Verify agents store memories via "genesis_memory.add"

## Acceptance Criteria

- [ ] Genesis agents have longterm memory artifacts created at init
- [ ] Semantic search invoked during RAG context building
- [ ] Agents can store learnings via genesis_memory.add
- [ ] Fallback to keyword matching when genesis_memory unavailable
