# Gap 10: Memory Persistence

**Status:** 📋 Planned
**Priority:** Low
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Two memory systems with different persistence:

| System | Storage | Checkpoint Behavior |
|--------|---------|---------------------|
| `AgentMemory` | Qdrant (external) | Persists independently |
| `ArtifactMemory` | Artifact store | Persists with checkpoint |

Qdrant state can become inconsistent with simulation state on restore.

**Target:** Memory consistent with simulation checkpoints.

---

## Recommendation: Adopt ArtifactMemory

`ArtifactMemory` already exists and:
1. Persists with checkpoints automatically
2. Enables memory trading (transfer artifact)
3. No external dependencies

---

## Plan

### Phase 1: Default to ArtifactMemory

1. Set `memory.backend: artifact` as default in config
2. `AgentMemory` (Qdrant) available as opt-in for semantic search

### Phase 2: Enhance ArtifactMemory Search

1. Add simple keyword matching
2. Consider TF-IDF for better relevance
3. Keep dependency-free

### Phase 3: Migration

1. Agent initialization creates memory artifact
2. Link via `agent.memory_artifact_id`
3. Document in handbook

---

## Required Tests

```
tests/unit/test_artifact_memory.py::test_persists_with_checkpoint
tests/unit/test_artifact_memory.py::test_cleared_on_rollback
tests/unit/test_artifact_memory.py::test_search_returns_relevant
```

---

## Verification

- [ ] Memory persists across checkpoint save/restore
- [ ] Restored simulation has consistent memories
- [ ] Tests pass
- [ ] Docs updated
