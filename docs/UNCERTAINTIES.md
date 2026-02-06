# Uncertainties & Human Review Queue

Questions and decisions that need human review before or during implementation.
Surfaced automatically by `scripts/file_context.py` during context loading (Pattern #34).

**Lifecycle:** Identified → Filed → User Reviews → Resolved → Correction persisted → Archived here.

## Format

| Field | Description |
|-------|-------------|
| **ID** | U-NNN, monotonically increasing |
| **Question** | The actual question needing resolution |
| **Context** | Links to ADR/plan/code/section that raises the question |
| **Blocking** | `true` = gates implementation of affected files; `false` = surfaced as warning |
| **Status** | OPEN / RESOLVED |
| **Resolution** | Decision made + where it was persisted |

---

## Open

### U-001: `created_by` used for access control despite being informational

**Question:** Kernel contracts (freeware, self_owned, private) all use `created_by` for authorization decisions. ADR-0016 says it should be informational only (like `created_at`). Which is correct?

**Context:** ADR-0016, `src/world/kernel_contracts.py`, `src/world/permission_checker.py`, `docs/DESIGN_CLARIFICATIONS.md` section 4

**Blocking:** true

**Status:** RESOLVED (user decision: created_by is purely informational, Plan #306 Workstream C will fix)

**Resolution:** `created_by` is purely informational metadata like `created_at`. Contracts alone decide authorization and payment. Fix tracked in Plan #306 Workstream C.

---

### U-002: Long-term control mechanism (transferable authority)

**Question:** What is the long-term "owner/control" mechanism, distinct from `created_by`, that is kernel-enforced and transferable?

**Context:** DESIGN_CLARIFICATIONS section 11.3, section 13.6

**Blocking:** false

**Status:** OPEN

**Resolution:** —

**Options:**
1. `controller_id` system field (mutable by current controller)
2. Rights-based authority (holder of specific right controls artifact)
3. Contract-governed (contract code determines controller)

**Blocked by:** ADR-0024 + non-forgeable rights (Plan #235). Future decision.

---

### U-003: Interface validation — advisory or mandatory?

**Question:** Should artifact interface validation become mandatory (kernel rejects non-matching operations), or remain advisory?

**Context:** DESIGN_CLARIFICATIONS sections 11.2, 13.5

**Blocking:** false

**Status:** OPEN

**Resolution:** —

**Trade-off:** Mandatory = safer, less emergent flexibility. Advisory = more emergent, agents can make mistakes the system won't catch.

---

### U-004: Can artifacts with `has_standing` be payers?

**Question:** Should artifacts with `has_standing=True` be allowed as payers in charge delegation? Enables contract-as-treasury but complicates authority model.

**Context:** DESIGN_CLARIFICATIONS section 13.4, Plan #236

**Blocking:** false

**Status:** OPEN

**Resolution:** —

**Current interim:** Principals only (Plan #236 FM-3).

---

### U-005: `has_standing` ↔ Ledger coupling mechanism

**Question:** How should `has_standing` on artifacts couple with ledger registration? Currently independent, creating invalid states.

**Context:** DESIGN_CLARIFICATIONS section 13.2, Plan #231

**Blocking:** false

**Status:** OPEN

**Resolution:** —

**Options:**
1. Artifact-driven — `has_standing=True` auto-creates ledger entry
2. Ledger-driven — `create_principal()` is the ONLY way (plan recommends)
3. New kernel primitive — `create_standing_artifact()` creates both atomically

---

### U-006: ADR-0024 migration — data artifact handlers

**Question:** Under `handle_request`, data artifacts (no code) need handling. Stub handlers? Kernel default? Deny all? Allow read?

**Context:** DESIGN_CLARIFICATIONS section 13.3, Plan #234

**Blocking:** false

**Status:** OPEN

**Resolution:** —

---

### U-007: What distinguishes a principal from an artifact?

**Question:** What is a principal? Currently: registered in ledger with `has_standing: true`. Is this sufficient, or do we need a formal distinction?

**Context:** DESIGN_CLARIFICATIONS section 11.1

**Blocking:** false

**Status:** OPEN

**Resolution:** —

---

## Resolved

(None yet — U-001 is the first to move here after Plan #306 Workstream C ships.)
