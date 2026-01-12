# ADR-0001: Everything is an Artifact

**Status:** Accepted
**Date:** 2026-01-11
**Certainty:** 90%

## Context

The system needs a unified way to represent agents, data, contracts, and other entities. Having separate storage and semantics for each type creates complexity and limits composability.

Questions that motivated this:
- Can agents own other agents?
- Can contracts be traded?
- Can an agent's memory be sold separately?

## Decision

**Everything is an artifact.** Agents, contracts, data, configs - all are artifacts with different properties.

Properties determine role:

```python
@dataclass
class Artifact:
    id: str                    # Universal ID
    content: Any               # Data, code, config
    access_contract_id: str    # Who answers permission questions
    has_standing: bool         # Can hold scrip, bear costs (= principal)
    can_execute: bool          # Has runnable code
    created_by: str            # Creator's artifact ID
    interface: dict | None     # Required if can_execute=True
```

**Relationships:**
- Agent = artifact with `has_standing=True, can_execute=True`
- Principal = artifact with `has_standing=True`
- Contract = artifact with `can_execute=True`, implements `check_permission`
- Data = artifact with both False

## Consequences

### Positive

- **Unified ID namespace** - No separate principal_id, artifact_id, agent_id
- **Composability** - Anything can own anything, trade anything
- **Emergent structures** - DAOs, hierarchies, markets emerge naturally
- **Simpler kernel** - One storage system, one permission model

### Negative

- **Query complexity** - "Find all agents" requires filtering by properties
- **Migration cost** - Existing code assumes separate agent/artifact storage
- **Conceptual overhead** - "Agent is an artifact" is less intuitive than "Agent has artifacts"

### Neutral

- Contract that governs an artifact is itself an artifact (turtles all the way down)
- Genesis artifacts are still special (created at init, hardcoded behavior) but fit the model

## Related

- Gap #6: Unified Artifact Ontology
- Gap #7: Single ID Namespace
- ADR-0003: Contracts can do anything (contracts are artifacts too)
