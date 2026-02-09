# ADR-0028: created_by is Purely Informational

**Status:** Accepted
**Date:** 2026-02-06
**Supersedes:** ADR-0016 code examples (prose intent preserved)

## Context

ADR-0016 replaced `owner_id` with `created_by` and stated it is "an immutable fact, not a role." However, its code examples showed `created_by` being used for access control decisions in kernel contracts. Over time, 13+ locations in the codebase used `created_by` for authorization checks and payment routing — directly contradicting the stated intent.

The fundamental issue: `created_by` records who originally created an artifact (like `created_at` records when). It is immutable and purely historical. Using it for access control prevents ownership transfer, conflates creation with authorization, and embeds policy decisions in an immutable field.

## Decision

**`created_by` is purely informational. It MUST NOT be used for:**
- Access control decisions (who can read/write/invoke)
- Payment routing (who receives scrip for artifact usage)
- Authorization checks of any kind

**Contracts alone decide authorization** via artifact state fields:
- `artifact.state["writer"]` — who can write (used by freeware/transferable_freeware contracts)
- `artifact.state["principal"]` — who has full access (used by self_owned/private contracts)

**Contracts alone decide payment** via `PermissionResult.recipient`:
- Contracts set `recipient` on allowed results
- Payment code uses `result.recipient` instead of `artifact.created_by`

**Backward compatibility:** `ArtifactStore.write()` auto-populates authorization state fields from `created_by` when creating new artifacts (if not already set by the caller). This preserves existing behavior while making the authorization field mutable and transferable. Auth data lives in `artifact.state` (not `metadata`) to prevent forgery via `update_metadata` (Plan #311).

### Concrete changes

1. **Kernel contracts** check `context["_artifact_state"]` instead of `context["target_created_by"]`
2. **PermissionResult** has a new `recipient` field set by contracts
3. **Payment routing** uses `PermissionResult.recipient` or artifact state fields
4. **Hardcoded auth checks** replaced with contract permission checks
5. **Delegation payer resolution** uses artifact state for target/contract charge_to directives

## Consequences

### Positive

- Ownership transfer becomes possible (change `artifact.state["writer"]`)
- Clear separation: creation fact vs. authorization policy
- Contracts have full control over authorization (principle #9: "when in doubt, contract decides")
- Consistent with ADR-0016's stated prose intent

### Negative

- Artifact state fields are mutable — authorization can change (this is intentional for transferability)
- Artifacts created outside `ArtifactStore.write()` (e.g., in tests) must set authorization state explicitly
- Delegation payer resolution now uses mutable artifact state instead of immutable `created_by` (delegation authorization prevents abuse)

### Neutral

- `created_by` field remains on all artifacts — still useful for provenance, auditing, and display
- `target_created_by` still passed in contract context — available for informational use

## Related

- ADR-0016: Establishes `created_by` field (this ADR clarifies its role)
- ADR-0019: Unified permission architecture (contracts govern access)
- Plan #306: Implementation plan for this change
