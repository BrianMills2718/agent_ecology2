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

---

## 1. Current vs Target Architecture

**Why record:** Prevents documentation drift where the conceptual model reads as implemented reality.

| Aspect | Current (ADR-0019) | Target (ADR-0024) |
|--------|-------------------|-------------------|
| Runtime model | Kernel-mediated permission checks | Artifact-handled access |
| Interface | `run(*args)` | `handle_request(caller, operation, args)` |
| Contract execution | Contracts executed BEFORE artifact code | Artifacts handle access in their code |
| Kernel role | Routes AND interprets policy | Routes only (kernel opacity) |
| Defaults | Freeware contract fallback | No defaults |

**Kernel opacity:** Under ADR-0024, kernel treats artifact code as a black box - executes but does not interpret policy.

**Reference:** `docs/CONCEPTUAL_MODEL.yaml` (implementation status table)

---

## 2. Interface Mismatch Limitation

**Why record:** Bounds what "contracts are just artifacts" can mean today.

`handle_request` does not exist in code today; only `run()` exists.

**Implications:**
- No operation-level dispatch (read/write/invoke/delete) inside artifact code under current model
- Current contracts cannot distinguish between operation types in a standard way
- Artifacts cannot implement fine-grained access control per operation

**Migration:** Plan #234 (ADR-0024 Handle Request Migration)

---

## 3. Security-Critical Invariants

**Why record:** These are concrete privilege-escalation channels, not style preferences.

### 3.1 Type Mutation (FM-6)

**Vulnerability:** `type` is currently user-mutable but used for kernel branching.

**Attack:** Type confusion - attacker creates normal artifact, changes `type` to "right"/"trigger"/"config", gains privileged kernel handling.

**Kernel branching locations:**
- `rights.py:250,277,312,383,471` - `if artifact.type != "right"`
- `triggers.py:209` - `if artifact.type != "trigger"`
- `genesis/memory.py:187` - `if artifact.type != "memory_store"`

**Mitigation:** `type` must be immutable after creation. Plan #235 Phase 0.

### 3.2 Policy-Pointer Swap (FM-7)

**Vulnerability:** `access_contract_id` is currently mutable by anyone with write permission.

**Attack:** Attacker with write permission changes `access_contract_id` to `genesis_contract_freeware`, making artifact publicly accessible.

**Mitigation:** `access_contract_id` is creator-only - only `created_by` can change it. Plan #235 Phase 0.

### 3.3 Authorized Writer Forgery

**Vulnerability:** `authorized_writer` (metadata field) is forgeable - any writer can rewrite it.

**Rule:** NEVER use `authorized_writer` as an authorization anchor for payment or delegation.

**Safe anchors:** Only `created_by` (immutable system field) is kernel-trustworthy.

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

**Why record:** "Scarcity" (cannot counterfeit) is foundational for any resource economy.

### Current Problem

Rights-as-artifacts are currently forgeable because:
1. Content can be edited directly via `edit_artifact`
2. Contract validation cannot reliably prevent "counterfeiting" because contracts don't see proposed deltas/content in a strong way

### Solution

Near-term fix requires kernel-enforced immutability:
- A `kernel_protected` field (system field, not metadata)
- `kernel_protected: true` means only kernel primitives can modify
- Normal write/edit actions are rejected

**Implementation:** Plan #235 (Kernel-Protected Artifacts)

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

**Why record:** Otherwise delegation artifacts are not trustworthy.

### The Problem

Deterministic IDs like `charge_delegation:{payer}` are vulnerable to **ID squatting**:
- Attacker creates `charge_delegation:victim` before victim does
- Attacker's artifact is now the canonical delegation record for victim
- Victim cannot create their own

### Mitigation

Kernel must enforce **reserved ID namespaces**:
- `charge_delegation:X` can ONLY be created by principal X
- `right:*` reserved for kernel-created rights
- Validation at artifact creation time in `ArtifactStore.write()`

**Implementation:** Plan #235 Phase 1 (Reserved Namespaces)

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
| Kernel-protected artifacts | #235 | Planned | None |
| Charge delegation | #236 | Planned | #235 |
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

## References

- **Plans:** #234, #235, #236
- **ADRs:** ADR-0016 (created_by not owner), ADR-0019 (current), ADR-0024 (target)
- **Source:** ChatGPT/Claude security dialogue (2026-01-31)
- **Code:** `src/world/artifacts.py`, `src/world/action_executor.py`, `src/world/rights.py`
