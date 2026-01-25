# ADR-0021: Executor Design Principles

**Status:** Accepted
**Date:** 2026-01-24
**Certainty:** 90%

## Context

During architecture review, several questions arose about executor behavior:

1. When are resource costs (llm_budget, compute) deducted vs economic costs (scrip)?
2. Should the kernel provide atomic multi-step transactions?
3. Should the kernel mandate that contracts provide decision reasons?

These questions reflect the boundary between kernel physics (what the system enforces) and contract policy (what contracts handle).

## Decision

### 1. Cost Timing Asymmetry

**Resource costs deducted BEFORE execution. Scrip deducted AFTER success.**

| Cost Type | When Deducted | Rationale |
|-----------|---------------|-----------|
| Resources (llm_budget, compute) | Before | Physical consumption - like gas in a car, spent regardless of destination |
| Scrip (economic payment) | After success | Payment for service - like a bank transfer, only completes if valid |

This is intentional, not a bug. Resources represent physical consumption that occurs regardless of outcome. Scrip represents economic exchange that only happens on successful completion.

### 2. No Kernel Atomic Transactions

**The kernel provides no atomic multi-step transactions. Contracts handle atomicity.**

If a contract needs to:
1. Transfer scrip from A
2. Transfer artifact from B
3. Transfer scrip to C

And step 2 fails, the kernel does NOT automatically roll back step 1. The contract is responsible for safe operation ordering.

**Safe pattern:** Hold all assets in escrow before releasing any. Don't release until all preconditions met.

```python
# UNSAFE: partial failure leaves inconsistent state
transfer(a, escrow, 100)  # succeeds
transfer_artifact(b, escrow, artifact)  # fails!
# Now escrow has A's scrip but not B's artifact

# SAFE: verify all deposits before any release
deposit_scrip(a, 100)      # hold in escrow
deposit_artifact(b, art)   # hold in escrow
# Only after both deposits succeed:
release_to(c, scrip)
release_to(a, artifact)
```

**Rationale:** Atomic transactions in kernel add complexity. Contracts are the right layer for coordination logic. This follows "minimal kernel, maximum flexibility."

### 3. Contract Decision Opacity

**The kernel does NOT mandate that contracts provide decision reasons. Best practice, not requirement.**

Contracts SHOULD return detailed reasons:
```python
{"allowed": False, "reason": "Caller balance 50 < required 100"}
```

But the kernel only requires:
```python
{"allowed": False}
```

**Rationale:** Mandating reasons adds kernel complexity. Good contract authors will provide reasons. Bad contracts will be avoided via reputation/observation.

## Consequences

### Positive

- **Simple kernel** - Fewer guarantees = less complexity
- **Flexible contracts** - Contracts can implement any coordination pattern
- **Clear responsibility** - Kernel = physics, Contracts = policy
- **Selection pressure** - Bad contracts observable, avoided by agents

### Negative

- **Contract author burden** - Must think about atomicity, reasons
- **Potential for bad contracts** - No kernel protection against poor design
- **Learning curve** - Agents must understand safe patterns

### Mitigations

- Handbook documents safe patterns (`handbook_trading.md`)
- Genesis escrow demonstrates correct atomicity
- Bad contracts become observable through event log

## Related

- ADR-0003: Contracts Can Do Anything
- ADR-0011: Standing Pays Costs
- Plan #165: Genesis Contracts as Artifacts
- Plan #166: Resource Rights Model
