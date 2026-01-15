# ADR-0011: Standing = Pays Costs

**Status:** Accepted
**Date:** 2026-01-14
**Certainty:** 90%

## Context

Who pays for resource consumption? In a system where everything is an artifact, we need clear rules about cost attribution.

Options considered:
1. **Creator pays** - Artifact creator pays all costs
2. **Owner pays** - Current owner pays all costs
3. **Invoker pays** - Whoever invokes/uses pays the costs
4. **Standing-based** - Only artifacts with standing can hold resources/pay

## Decision

**Only artifacts with `has_standing=True` can hold resources and pay costs.**

"Standing" means the artifact is a principal - it can:
- Hold scrip balance
- Consume resources (CPU, memory, disk)
- Be charged for operations
- Enter into economic relationships

```python
@dataclass
class Artifact:
    has_standing: bool  # Can hold scrip, bear costs
    # ...

# Examples
agent = Artifact(has_standing=True, ...)      # Principal - pays costs
contract = Artifact(has_standing=False, ...)  # Not a principal - can't pay
data = Artifact(has_standing=False, ...)      # Not a principal - can't pay
```

**Invoker always pays:** When Agent A invokes Contract B:
- A pays (has standing)
- B executes but doesn't pay (typically no standing)
- Any costs incurred are charged to A

## Consequences

### Positive

- **Clear cost attribution** - Always know who pays
- **Economic incentives** - Agents must fund their operations
- **Simple contracts** - Contracts don't need their own budgets
- **Prevents free riding** - Can't create "free" artifacts that consume resources

### Negative

- **Funding complexity** - New agents need initial endowment
- **Bankruptcy risk** - Agents can run out of resources
- **Contract limitations** - Contracts can't accumulate wealth directly

### Neutral

- Contracts can still receive payments (held in escrow or transferred immediately)
- Genesis artifacts have special standing (system-funded)

## Related

- ADR-0001: Everything is an artifact (standing as property)
- ADR-0003: Contracts can do anything (invoker pays)
- Gap #6: Unified Artifact Ontology
