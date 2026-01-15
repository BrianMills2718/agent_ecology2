# ADR-0007: Single ID Namespace

**Status:** Accepted
**Date:** 2026-01-14
**Certainty:** 90%

## Context

The system originally had separate ID namespaces: agent IDs, artifact IDs, contract IDs, principal IDs. This created:

- Confusion about which ID type to use where
- Duplicate lookups (is this an agent or artifact?)
- Complex relationships (agent has artifacts, owns contracts)
- API complexity (different endpoints for different types)

With ADR-0001 (Everything is an artifact), we needed a unified way to address all entities.

## Decision

**Single ID namespace for all artifacts.** Every entity in the system has a unique ID in the same namespace.

```python
# All IDs share the same namespace
agent_id = "agent_001"           # An agent artifact
contract_id = "contract_market"  # A contract artifact
data_id = "artifact_memory_x"    # A data artifact

# Same API works for all
store.get(agent_id)      # Works
store.get(contract_id)   # Works
store.get(data_id)       # Works
```

ID format is simply a string. No type prefixes required (though `genesis_*` prefix used by convention for genesis artifacts).

## Consequences

### Positive

- **Unified API** - One `store.get(id)` method handles all types
- **Simpler references** - `access_contract_id` just stores an ID, no type annotation needed
- **Composability** - Any artifact can reference any other artifact by ID
- **Consistent queries** - "Find all things owned by X" doesn't need type filtering

### Negative

- **Type discovery** - Must inspect artifact properties to determine type
- **ID collisions** - Need to ensure uniqueness across all entity types
- **Query filtering** - "Find all agents" requires property filter, not namespace query

### Neutral

- Legacy `agent_id`, `principal_id` fields may appear in older code
- Type is determined by properties (`has_standing`, `can_execute`), not ID

## Related

- ADR-0001: Everything is an artifact
- Gap #7: Single ID Namespace
- Gap #6: Unified Artifact Ontology
