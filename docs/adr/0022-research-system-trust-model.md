# ADR-0022: Research System Trust Model

**Status:** Accepted
**Date:** 2026-01-24
**Based on:** DESIGN_CLARIFICATIONS.md Section 2, Contradiction Resolution C4

## Context

When designing the agent ecology, questions arose about admin privileges, state rollback, and fault tolerance. The initial design discussions used blockchain terminology, leading to confusion about what guarantees the system should provide.

Key question: Is this a trustless production system (like Bitcoin/Ethereum) or a research platform with different assumptions?

## Decision

**This is a research system with an explicit admin role, not a trustless production blockchain.**

| Aspect | Production Blockchain | This Research System |
|--------|----------------------|---------------------|
| **Admin access** | None (trustless) | Yes, with transparency |
| **Rollback** | Computationally infeasible | Possible if needed |
| **State reset** | Prohibited | Allowed for research |
| **Bug fixes** | Requires hard fork | Genesis artifacts mutable |
| **Fault tolerance** | Byzantine | Trusted operators |

### 1. Admin Intervention is Possible

Unlike lost Bitcoin, an admin can intervene if a catastrophic bug locks valuable work. This is a feature, not a bug.

### 2. Simpler Design Choices

We don't need Byzantine fault tolerance for a system with trusted operators. This enables simpler mechanisms throughout.

### 3. Experiments Can Be Reset

If an experiment goes wrong, we can restore from checkpoint, not lose months of work.

### 4. Genesis Artifact Evolution

Genesis artifacts can be updated via code deploy. No governance token voting required.

### 5. Transparency Requirement

Any admin intervention must be:
- Logged in the event system
- Documented with rationale
- Visible to all agents and observers

This isn't "centralized vs decentralized" - it's acknowledging that research systems have different trust assumptions than production deployments.

## Consequences

### Positive

- **Simpler mechanisms** - No Byzantine consensus, no proof-of-work, no governance tokens
- **Faster iteration** - Can fix bugs without protocol upgrades
- **Recoverable** - Catastrophic failures can be undone
- **Clear expectations** - Agents know the rules (admin exists, must be transparent)

### Negative

- **Trust required** - Must trust admin to be transparent and fair
- **Not production-ready** - Can't deploy as public service without redesign
- **Different guarantees** - Agents can't rely on "code is law" immutability

### Neutral

- Admin power is documented, not hidden
- Research results are still valid (system is honest about its constraints)
- Could evolve to trustless if needed (add consensus, remove admin)

## Related

- ADR-0004: Mint as System Primitive (system vs genesis distinction)
- ADR-0018: Bootstrap and Eris (genesis creation)
- Philosophy in README.md ("Accept risk, observe outcomes")
