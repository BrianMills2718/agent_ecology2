# Design Clarifications

**Purpose:** WHY decisions were made - architecture discussions, design constraints, and invariants that prevent rediscovery loops.

**Last Updated:** 2026-01-31

---

## Table of Contents

1. [Current vs Target Architecture](#1-current-vs-target-architecture)
2. [Interface Mismatch Limitation](#2-interface-mismatch-limitation)
3. [Security-Critical Invariants](#3-security-critical-invariants)
4. [Hard Anchors and Provenance](#4-hard-anchors-and-provenance)
5. [Non-Forgeable Rights Requirement](#5-non-forgeable-rights-requirement)
6. [Charge Routing (charge_to)](#6-charge-routing-charge_to)
7. [Consent Model for Non-Caller Charging](#7-consent-model-for-non-caller-charging)
8. [Reserved Namespaces and ID Squatting](#8-reserved-namespaces-and-id-squatting)
9. [Schema Safety Principles](#9-schema-safety-principles)
10. [Deferred Features](#10-deferred-features)
11. [Open Questions](#11-open-questions)
12. [Known Code Bugs (Schema Audit)](#12-known-code-bugs-schema-audit)
13. [Pending Decisions (User Review Required)](#13-pending-decisions-user-review-required)

---

## 1. Current vs Target Architecture

**Status: RESOLVED** — CMF v3 (2026-01-31) separates Part 1 (current ADR-0019) from Part 2 (target ADR-0024). See `docs/CONCEPTUAL_MODEL_FULL.yaml`.

---

## 2. Interface Mismatch Limitation

**Status: DOCUMENTED** — CMF v3 Part 2 covers the target `handle_request` interface. Plan #234 tracks implementation. See `docs/CONCEPTUAL_MODEL_FULL.yaml` Part 2.

---

## 3. Security-Critical Invariants

**Status: FIXED + INTEGRATED** — All invariants fixed by Plan #235 Phase 0+1. Attack scenarios and kernel branching locations integrated into `docs/SECURITY.md` "Kernel-Level Security Invariants" section.

---

## 4. Hard Anchors and Provenance

**Why record:** The persistent confusion is "provenance vs control." Deconflict rather than delete.

### What is a Hard Anchor?

A **hard anchor** is a kernel-trustworthy identity fact - something the enforcement layer treats as stable input that cannot be forged or modified by agents.

### created_by as Hard Anchor

`created_by` functions as a hard anchor today because:
- It's immutable (set once at artifact creation)
- It's a system field (not in user-modifiable metadata)
- The kernel can trust it for authorization decisions

### The Provenance vs Control Problem

**Problem:** `created_by` is non-transferable (cannot change owners/controllers).

**Correct interpretation:**
- `created_by` = **provenance** (who originally created this artifact) - historical fact
- `created_by` ≠ **current owner/controller** - that's a different concept

**Current workaround:** Use `created_by` as the interim authority anchor, but recognize it cannot model ownership transfer.

**Future:** Need a separate `controller_id` or authority mechanism that is:
- Kernel-enforced (not metadata)
- Transferable
- Distinct from provenance

---

## 5. Non-Forgeable Rights Requirement

**Status: FIXED** — Plan #235 Phase 1 added `kernel_protected` field. See `docs/GLOSSARY.md` Artifact Properties.

---

## 6. Charge Routing (charge_to)

**Why record:** Clarifies scope and orthogonality of cost routing.

### Current State

`charge_to` is not implemented. Today "caller always pays" (`resource_payer = intent.principal_id`).

### Orthogonality

`charge_to` can be implemented **without ADR-0024** because:
- Settlement happens AFTER execution in the action executor
- You can route debits there without changing the interface
- Independent of `run()` vs `handle_request` decision

### Implementation Requirement

Adding `charge_to` requires consent (payer authorization) or it becomes a **drain-anyone exploit**.

**Implementation:** Plan #236 (Charge Delegation)

---

## 7. Consent Model for Non-Caller Charging

**Why record:** Avoids infinite regress ("who pays for the authorization check?") and clarifies threat model.

### Separation of Concerns

| Concern | Mechanism |
|---------|-----------|
| Routing | `charge_to` says who SHOULD pay |
| Consent | Delegation record says who is ALLOWED to charge whom |

### Design Principles

1. **Explicit delegation records** - Static policy lookup, no handler recursion
2. **Exposure caps** - Max per call/window limits worst-case loss
3. **Atomic settlement** - Single lock around check→debit→record prevents race-condition bypass

### Atomic Settlement Pattern

```python
async def atomic_settlement(self, payer_id, charger_id, amount):
    async with self._settlement_lock:  # SINGLE LOCK - all 3 steps
        # 1. Check caps (reads window usage)
        if not self._check_caps(payer_id, charger_id, amount):
            return False, "Cap exceeded"
        # 2. Debit payer
        if not self._debit(payer_id, amount):
            return False, "Insufficient funds"
        # 3. Record charge (updates window usage)
        self._record_charge(payer_id, charger_id, amount)
        return True, "OK"
```

**Implementation:** Plan #236 (Charge Delegation)

---

## 8. Reserved Namespaces and ID Squatting

**Status: FIXED** — Plan #235 Phase 1 implemented reserved ID namespaces. See `src/world/artifacts.py` reserved namespace validation.

---

## 9. Schema Safety Principles

**Why record:** "Configurable strictness" must not become "configurable security."

### Safe Version

- Strong typing
- Interfaces as advisory (for discoverability/validation)
- Enforced invariants at the kernel boundary
- Security properties are not optional

### Unsafe Version (AVOID)

- Runtime toggles that weaken enforcement
- Per-agent or per-artifact security downgrades
- "Permissive mode" flags

**Downgrade attack surface:** Attacker flips system into permissive mode, then exploits.

### Principle

Configuration can control **behavior** (timeouts, limits, features) but not **security invariants** (immutability, permission enforcement, forgery prevention).

---

## 10. Deferred Features

**Why record:** So they don't blur with current capabilities.

| Feature | Plan | Status | Dependency |
|---------|------|--------|------------|
| ADR-0024 migration | #234 | Planned | None |
| Kernel-protected artifacts | #235 | ✅ Complete (Phase 0+1) | None |
| Charge delegation | #236 | Planned | #235 ✅ |
| Contract-governed policy upgrades | Future | Deferred | ADR-0024 |
| Ownership/control transfer (kernel-enforced) | Future | Deferred | ADR-0024 |
| Scrip-as-rights (conceptual purity) | Future | Deferred | #235 (non-forgeable rights) |

### Contract-Governed Policy Upgrades

Long-term goal: Changing an artifact's `access_contract_id` should be governed by the **current contract**, not just "creator-only."

Current interim: Creator-only restriction (Plan #235 FM-7).

### Transferable Authority

Need kernel-enforced ownership transfer mechanism:
- Distinct from `created_by` (provenance)
- Transferable between principals
- Not metadata-based (metadata is forgeable)

---

## 11. Open Questions

**Why record:** These force downstream architecture decisions.

### 11.1 What is a Principal?

**Question:** What distinguishes a principal (entity that can hold balances / be charged) from an artifact?

**Current answer:** Principals are registered in ledger with `has_standing: true`. Artifacts can have `has_standing: true` but typically don't hold balances.

**Implication for charge_to:** Initially restricting payers to principals only (Plan #236 FM-3).

### 11.2 Minimal Artifact Interface Schema

**Question:** What is the minimal artifact interface schema to standardize (JSON Schema / tool signature), and is it purely advisory?

**Current state:** Interface is advisory (stored in `interface` field), used for:
- Discovery (`query_kernel` action)
- Validation (optional, via `interface_validation.py`)
- LLM presentation (linearization)

**Open:** Should interface validation be mandatory or remain optional?

### 11.3 Long-Term Control Mechanism

**Question:** What is the long-term "owner/control" field/mechanism, distinct from `created_by`, that is kernel-enforced and transferable?

**Options:**
1. `controller_id` system field (mutable by current controller)
2. Rights-based authority (holder of specific right controls artifact)
3. Contract-governed (contract code determines controller)

**Deferred:** Requires ADR-0024 and non-forgeable rights first.

---

## 12. Known Code Bugs (Schema Audit)

**Status: ALL FIXED** — All bugs fixed by Plan #239. See `docs/SCHEMA_AUDIT.md` section 2 for historical detail.

---

## 13. Pending Decisions (User Review Required)

**Why record:** Consolidates all open architecture decisions from across the codebase into one actionable list. These need human judgment — they involve trade-offs that affect the project's direction.

**Added:** 2026-01-31

### 13.1 CONCEPTUAL_MODEL_FULL.yaml: Deprecate or Update? — CLOSED

**Decision (2026-01-31):** Full rewrite (Option 2). CMF v3 rewrites from scratch using code as source of truth, with clear 3-part structure: Part 1 (Current ADR-0019), Part 2 (Target ADR-0024), Part 3 (Reference). Maintenance burden addressed by adding CMF to `scripts/relationships.yaml` coupling graph — future code changes to `artifacts.py`, `actions.py`, `kernel_interface.py` now trigger CMF update checks.

**Original context:** `docs/CONCEPTUAL_MODEL_FULL.yaml` (CMF) mixed ADR-0019 (current) and ADR-0024 (target) content without clear boundaries. Root cause: CMF was never in the doc-code coupling graph, so it drifted silently.

**Resolution:** All 17 SCHEMA_AUDIT.md inconsistencies resolved by CMF v3. See `docs/SCHEMA_AUDIT.md` for resolution status per inconsistency.

### 13.2 Plan #231: has_standing ↔ Ledger Coupling Mechanism

**Context:** `has_standing` on artifacts and ledger registration are currently independent — you can have one without the other, creating invalid states.

**Options:**
1. **Artifact-driven** — Setting `artifact.has_standing = True` auto-creates ledger entry. Single operation but couples artifact store to ledger.
2. **Ledger-driven** (plan recommends) — `create_principal()` is the ONLY way. Creates ledger entry AND sets `has_standing=True`. Clear single source of truth.
3. **New kernel primitive** — `create_standing_artifact()` creates both atomically. Cleanest semantics but adds API surface.

**Additional question:** What happens on checkpoint restore if artifact has `has_standing` but ledger entry doesn't exist yet? (Order of operations)

**Reference:** `docs/plans/231_has_standing_ledger_coupling.md`

### 13.3 Plan #234: ADR-0024 Migration Design Questions

**Context:** ADR-0024 proposes moving from kernel-mediated permission checking (`run()`) to artifact self-handled access (`handle_request(caller, operation, args)`). Major architectural shift.

**Questions:**
1. **Data artifacts (no code):** Currently `code: ""` is valid for data artifacts. Under handle_request, do they need stub handlers, or should the kernel provide a default "deny all" / "allow read" handler?
2. **Performance impact:** Current permission checks are lightweight Python contract calls. Full artifact code execution per operation is heavier. Is this acceptable, or do we need a fast-path optimization?

**Reference:** `docs/plans/234_adr0024_handle_request_migration.md`

### 13.4 Plan #236: Can Artifacts Be Payers?

**Context:** Charge delegation enables "target pays" and "pool pays" patterns. The plan's FM-3 restricts payers to principals only as an interim measure.

**Question:** Should artifacts with `has_standing=True` be allowed as payers? This would enable contract-as-treasury patterns but complicates the authority model.

**Current interim:** Principals only.

**Reference:** `docs/plans/236_charge_delegation.md`

### 13.5 Interface Validation: Advisory or Mandatory?

**Context:** Artifact interfaces are currently advisory — stored in the `interface` field, used for discovery and LLM presentation, but not enforced at the kernel level.

**Question:** Should interface validation become mandatory (kernel rejects operations that don't match declared interface), or remain advisory (agents can ignore it)?

**Trade-off:** Mandatory = safer, less emergent flexibility. Advisory = more emergent, but agents can make mistakes the system won't catch.

**Reference:** §11.2 above

### 13.6 Long-Term Control Mechanism

**Context:** `created_by` is immutable and non-transferable — it represents provenance, not current control. We need a transferable authority mechanism for ownership transfer.

**Options:**
1. **`controller_id` system field** — Mutable by current controller, kernel-enforced
2. **Rights-based authority** — Holder of specific right controls artifact
3. **Contract-governed** — Contract code determines controller

**Blocked by:** ADR-0024 + Plan #235 (non-forgeable rights). This is a future decision but should be on the radar.

**Reference:** §11.3 above, §4 (Hard Anchors)

---

## References

- **Plans:** #231, #234, #235, #236
- **ADRs:** ADR-0016 (created_by not owner), ADR-0019 (current), ADR-0024 (target), ADR-0025 (rights removal)
- **Source:** ChatGPT/Claude security dialogue (2026-01-31), Schema audit (2026-01-31)
- **Code:** `src/world/artifacts.py`, `src/world/action_executor.py`, `src/world/kernel_queries.py` (rights.py removed per ADR-0025)
- **Audit:** `docs/SCHEMA_AUDIT.md`
