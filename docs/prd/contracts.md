# PRD: Contract Capabilities

# Metadata
id: prd/contracts
type: prd
domain: contracts
status: draft
thesis_refs:
  - THESIS.md#emergence-over-prescription
  - THESIS.md#when-in-doubt-contract-decides

## Overview

Contracts are the access control layer - they determine who can do what to which artifacts. Rather than hard-coded permissions, contracts allow flexible, agent-definable access patterns.

This PRD defines what the contract system must be **capable** of, not how it's implemented.

## Capabilities

### permission-checking

**Description:** The system must check permissions before any artifact operation.

**Why:** Access control is fundamental to ownership and privacy. Without permission checking, any agent could read/modify any artifact, eliminating the concept of property.

**Acceptance Criteria:**
- Every read/write/invoke/delete operation checks permissions first
- Permission check receives caller identity and operation details
- Denied operations fail with clear error messages
- Permission checks are logged for observability

### flexible-policies

**Description:** Contracts must support a variety of access patterns, not just owner-only.

**Why:** Different artifacts need different access. Some should be public, some private, some shared with specific principals. Flexibility enables emergent access patterns.

**Acceptance Criteria:**
- Support for common patterns: public, private, owner-only, authorized list
- Contracts can implement custom logic (not just static rules)
- Contracts can charge for access (pricing)
- Contracts can impose conditions (caller must have property X)

### contract-as-artifact

**Description:** Contracts themselves are artifacts that agents can create and modify.

**Why:** If contracts are special kernel objects, only the kernel can define access patterns. Making contracts artifacts means agents can create novel access patterns. (Thesis: Emergence Over Prescription)

**Acceptance Criteria:**
- Contracts are stored as artifacts with `executable: true`
- Agents can create new contracts
- Contracts implement a standard interface (`check_permission`)
- Contract behavior can be inspected/tested

### default-behavior

**Description:** The system must have sensible defaults when no contract is specified.

**Why:** Cold-start problem - new artifacts need access control before agents have created sophisticated contracts. Defaults provide baseline security.

**Acceptance Criteria:**
- Artifacts without explicit contracts get a default policy
- Default policy is configurable (not hard-coded)
- Default errs toward restrictive (deny by default) or permissive based on config
- Genesis contracts provide common patterns for bootstrapping

### pricing-integration

**Description:** Contracts must support pricing for operations.

**Why:** Pricing enables economic exchange - agents can sell access to their artifacts. This creates incentive to build useful services.

**Acceptance Criteria:**
- Permission results include optional cost
- Cost is charged to caller when access is granted
- Cost is credited to artifact creator/owner
- Free access (cost=0) is the default

## Non-Goals

- **Complex authorization graphs** - No role hierarchies or group memberships built-in
- **Time-limited permissions** - No expiring access grants
- **Revocation** - Contract changes affect future checks, not past grants

## Open Questions

1. **Can contracts delegate to other contracts?** Currently each artifact has one contract.
2. **How do agents discover contract capabilities?** No standard contract introspection.

## References

- Thesis: `docs/THESIS.md`
- Domain Model: `docs/domain_model/contracts.yaml`
- ADR-0003: Contracts can do anything
- ADR-0015: Contracts as artifacts
- ADR-0019: Unified permission architecture
- Current implementation: `docs/architecture/current/contracts.md`
