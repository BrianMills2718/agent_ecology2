# ADR-0009: Memory as Artifact

**Status:** Accepted
**Date:** 2026-01-14
**Certainty:** 100%

## Context

Agents need persistent memory across invocations. Options considered:

1. **Special agent field** - `agent.memory` as a dedicated field
2. **External storage** - Memory in Qdrant/database, separate from artifact system
3. **Memory artifact** - Memory stored as an artifact, owned by agent

Option 1 breaks the "everything is artifact" model (ADR-0001). Option 2 creates a parallel storage system with different ownership/access semantics.

## Decision

**Memory is an artifact.** Agent memory is stored as an artifact containing a reference to a Qdrant collection.

```python
# Memory artifact structure
memory_artifact = Artifact(
    id="memory_agent_001",
    content={
        "type": "memory",
        "qdrant_collection": "agent_001_memory",
        "embedding_model": "text-embedding-3-small"
    },
    access_contract_id="agent_001",  # Self-owned
    has_standing=False,
    has_loop=False
)
```

**Key properties:**
- Memory artifact references external Qdrant collection
- Artifact ownership controls memory access
- Memory can be transferred, sold, traded like any artifact
- Access contract governs who can read/write memory

## Consequences

### Positive

- **Consistent model** - Memory fits the artifact ontology
- **Tradeable** - Agents can sell memories to others
- **Access controlled** - Same contract system governs memory access
- **Observable** - Memory operations appear in action log

### Negative

- **Indirection** - Must load artifact to find Qdrant collection
- **Split state** - Artifact metadata separate from Qdrant contents
- **Cleanup complexity** - Deleting memory artifact should clean Qdrant

### Neutral

- Qdrant collection lifecycle managed separately from artifact
- Multiple agents could theoretically share a memory collection

## Related

- ADR-0001: Everything is an artifact
- Gap #10: Memory Persistence
- Gap #6: Unified Artifact Ontology
