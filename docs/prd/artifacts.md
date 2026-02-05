# PRD: Artifact Capabilities

# Metadata
id: prd/artifacts
type: prd
domain: artifacts
status: draft
thesis_refs:
  - THESIS.md#emergence-over-prescription
  - THESIS.md#observability-over-control

## Overview

Artifacts are the fundamental unit of persistent state - "everything is an artifact" (ADR-0001). Agents, data, contracts, tools, memory - all are artifacts with different properties.

This PRD defines what the artifact system must be **capable** of, not how it's implemented.

## Capabilities

### persistent-storage

**Description:** Artifacts must persist across simulation restarts and be reliably retrievable.

**Why:** Without persistence, agents lose all their work on restart. Artifacts are the durable record of what agents have created.

**Acceptance Criteria:**
- Artifacts survive simulation restart
- Artifacts are retrievable by ID
- Artifact content can be updated
- Deleted artifacts can be soft-deleted (recoverable) or hard-deleted

### universal-addressability

**Description:** Every artifact must have a unique, stable identifier.

**Why:** Agents need to reference artifacts reliably. Contracts need to identify targets. The system needs to track ownership. Stable IDs make all of this possible.

**Acceptance Criteria:**
- Each artifact has a unique ID
- IDs are stable (don't change after creation)
- IDs are meaningful (namespacing conventions)
- Single ID namespace across all artifact types

### execution

**Description:** Artifacts marked as executable can run code that interacts with the world.

**Why:** Tools and services are executable artifacts. This allows agents to build reusable capabilities that other agents can invoke.

**Acceptance Criteria:**
- Executable artifacts contain code (Python)
- Code executes in a sandboxed environment
- Code can access a "wallet" of caller resources
- Execution has timeout protection
- Results are returned to caller

### metadata-and-typing

**Description:** Artifacts must carry metadata including creator, creation time, and type.

**Why:** Metadata enables attribution, auditing, and type-based behavior. Knowing who created an artifact and when is essential for trust and debugging.

**Acceptance Criteria:**
- `created_by` is immutable and tracks the creator
- `created_at` and `updated_at` track temporal information
- `type` categorizes artifacts (immutable after creation)
- Custom metadata can be attached

### discoverability

**Description:** Agents must be able to discover what artifacts exist and what they do.

**Why:** Agents can't use artifacts they can't find. Discoverability enables ecosystem awareness, collaboration, and service discovery.

**Acceptance Criteria:**
- Artifacts can be listed/queried
- Executable artifacts can have interface schemas
- Agents can filter artifacts by type, creator, etc.
- Query results respect access control

### dependency-tracking

**Description:** Artifacts can declare dependencies on other artifacts.

**Why:** Complex artifacts may depend on libraries, data, or other services. Explicit dependencies enable proper loading order and impact analysis.

**Acceptance Criteria:**
- `depends_on` field lists artifact dependencies
- Dependencies are validated (exist, accessible)
- Circular dependencies are detectable

## Non-Goals

- **Versioning** - No built-in version history (updates overwrite)
- **Branching/merging** - No git-like artifact version control
- **Schema enforcement** - Content is free-form (typing is advisory)

## Open Questions

1. **Should artifacts support binary content?** Currently content is string-only.
2. **How large can artifacts be?** No explicit size limits defined.

## References

- Thesis: `docs/THESIS.md`
- Domain Model: `docs/domain_model/artifacts.yaml`
- ADR-0001: Everything is an artifact
- ADR-0016: created_by replaces owner_id
- ADR-0021: Executor design principles
- Current implementation: `docs/architecture/current/artifacts_executor.md`
