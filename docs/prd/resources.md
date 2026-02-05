# PRD: Resource Capabilities

# Metadata
id: prd/resources
type: prd
domain: resources
status: draft
thesis_refs:
  - THESIS.md#physics-first
  - THESIS.md#stage-1-individual-agency

## Overview

Resources are the "physics" of the ecosystem - the constraints that drive emergent behavior. Without scarcity, there's no pressure for efficiency, collaboration, or specialization.

This PRD defines what the resource system must be **capable** of, not how it's implemented.

## Capabilities

### scarcity-enforcement

**Description:** The system must enforce real resource limits that agents cannot bypass.

**Why:** Scarcity is the core driver of emergent behavior. If agents can get unlimited resources, there's no pressure to be efficient or collaborate. (Thesis: Physics-First)

**Acceptance Criteria:**
- Agents cannot spend resources they don't have
- Resource limits are configurable but enforced
- No "debt" or negative balances for constrained resources
- Resource exhaustion is observable (agents know when they're out)

### resource-types

**Description:** The system must support different resource types with different behaviors.

**Why:** Different resources behave differently in the real world. LLM API calls are rate-limited, disk space is allocatable, and API budget is depletable. The system should model these accurately.

**Acceptance Criteria:**
- **Depletable**: Gone forever when spent (e.g., API budget in dollars)
- **Allocatable**: Can be freed and reused (e.g., disk space)
- **Renewable**: Regenerates over time / rolling window (e.g., rate limits)
- Each resource type has appropriate enforcement behavior

### resource-tracking

**Description:** The system must track resource ownership and usage accurately.

**Why:** Agents need to know their resource state to make decisions. The system needs accurate accounting for enforcement.

**Acceptance Criteria:**
- Each principal has tracked resource balances
- Usage is logged with attribution (who used what, when)
- Balances are queryable by agents
- Historical usage is available for analysis

### resource-transfer

**Description:** Principals must be able to transfer resources to each other.

**Why:** Resource transfer enables economic exchange, collaboration, and specialization. An agent with excess compute can trade with one that has excess storage.

**Acceptance Criteria:**
- Transfer requires sender to have sufficient balance
- Transfers are atomic (no partial transfers)
- Transfers are logged with sender, receiver, amount
- Transfers respect resource type semantics

### scrip-currency

**Description:** The system must provide an internal currency (scrip) for economic signaling.

**Why:** Scrip provides a common unit of account separate from physical resources. It enables pricing, payment for services, and economic coordination without requiring resource-for-resource barter.

**Acceptance Criteria:**
- Scrip balances are tracked per principal
- Scrip can be transferred between principals
- Scrip is distinct from physical resources
- Scrip can be earned (mint) and spent (services, artifacts)

### quota-management

**Description:** The system must support configurable per-principal quotas.

**Why:** Different agents may have different resource allocations based on their role or earned capacity. Quotas enable differentiated access.

**Acceptance Criteria:**
- Per-principal quotas for each resource type
- Quotas are configurable at runtime
- Quota can be transferred between principals
- Usage is tracked against quota

## Non-Goals

- **External billing integration** - We don't integrate with real payment systems
- **Resource markets** - Automated pricing/markets are emergent, not built-in
- **Complex resource dependencies** - Resource A requiring resource B is not modeled

## Open Questions

1. **Should scrip be backed by anything?** Currently it's fiat currency with no backing.
2. **How do agents discover resource prices?** No built-in price discovery mechanism.

## References

- Thesis: `docs/THESIS.md`
- Domain Model: `docs/domain_model/resources.yaml`
- ADR-0002: No compute debt
- ADR-0008: Token bucket rate limiting
- ADR-0012: Scrip non-negative
- Current implementation: `docs/architecture/current/resources.md`
