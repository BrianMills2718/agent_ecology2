# ADR-0021: Resource Attribution Model

**Status:** Accepted
**Date:** 2026-01-24
**Based on:** ARCHITECTURE_DECISIONS_2026_01.md Sections 7 and 18

## Context

When artifact A invokes artifact B which makes LLM calls, who pays for the resources consumed? The system needs clear rules for:

1. **Attribution** - Tracking who originated a call chain for billing purposes
2. **Payment flexibility** - Supporting different cost models (pay-per-use, subscriptions, sponsorship)
3. **Charging timing** - When resources are measured and charged

Options considered for attribution:
- Full call stack tracking (O(n) overhead)
- Immediate caller only (loses originator information)
- Single billing principal tracking (minimal, sufficient)

## Decision

### 1. billing_principal Tracking

The kernel tracks a single `billing_principal` in the invocation context - the principal who originated the call chain.

```python
context = {
    "caller": "tool_b",            # Immediate caller (for permission checks)
    "billing_principal": "alice",  # Who started chain (for billing)
}
```

**Rules:**
- Set when agent initiates action
- Propagated unchanged through all nested invocations
- Used to determine who gets charged (unless contract overrides)

### 2. resource_payer Contract Field

Contracts can specify who pays for resources via the `resource_payer` field in their response:

```python
{
    "allowed": True,
    "scrip_cost": 10,                      # Paid by billing_principal
    "resource_payer": "billing_principal"  # or "self"
}
```

| Value | Behavior | Use Case |
|-------|----------|----------|
| `"billing_principal"` (default) | Caller's originator pays | Normal pay-per-use |
| `"self"` | Artifact pays from own balance | Freemium, subscriptions, sponsorship |

### 3. Charge at Computation Time

Resources are charged when consumed, not when artifacts are created.

```python
# In executor (kernel)
with ResourceMeasurer() as measurer:
    result = execute_artifact_code(...)

usage = measurer.get_usage()
ledger.deduct_resource(billing_principal, "cpu_seconds", usage.cpu_seconds)
```

### 4. Patterns Enabled

**Subscription/freemium:**
1. Subscriber pays upfront to artifact (via genesis_ledger transfer)
2. Contract checks subscriber status
3. Returns `resource_payer: "self"` for subscribers
4. Artifact pays from its own balance

**Third-party sponsorship:**
1. Sponsor funds artifact directly
2. Artifact uses `resource_payer: "self"` for all callers
3. Provides free service until funds depleted

**Pay-per-use (default):**
- `billing_principal` pays for all resources consumed

### 5. Kernel Responsibility

- Set `billing_principal` at invocation start
- Pass unchanged through entire call chain
- Deduct resources from `billing_principal` or artifact based on `resource_payer`
- No authorization at kernel level (artifacts protect themselves via contract logic)

## Consequences

### Positive

- **Minimal tracking** - One ID, not unbounded call stack
- **Flexible patterns** - Supports pay-per-use, subscriptions, sponsorship without complex machinery
- **Clear attribution** - Always know who originated the request
- **Direct feedback** - Use resources → pay for resources (conservation law)
- **Creates demand** - Pressure for efficient artifacts

### Negative

- **Artifacts must manage buffers** - LLM costs are unpredictable; self-paying artifacts need reserves
- **No pre-authorization** - Artifacts can be drained if poorly configured
- **Liquidity locked** - Sponsor capital sits in artifact accounts

### Neutral

- Artifacts protect themselves via contract logic (rate limits, caps, subscriber checks)
- If artifact allows draining, that's the artifact's problem (physics-first)
- `has_standing=true` required for self-paying artifacts (already true for any artifact holding resources)

## Related

- ADR-0002: No Compute Debt (resources cannot go negative)
- ADR-0003: Contracts Can Do Anything (invoker pays)
- ADR-0011: Standing Pays Costs (only principals bear costs)
- Plan #95: Unified Resource System
- `src/world/ledger.py` - Ledger implementation
- `src/world/simulation_engine.py` - Resource measurement
