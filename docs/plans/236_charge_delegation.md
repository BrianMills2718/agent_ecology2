# Plan 236: Charge Delegation

**Status:** ✅ Complete

**Verified:** 2026-01-31T23:55:25Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-31T23:55:25Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 0d0fd25
```
**Priority:** High
**Blocked By:** #235 (Kernel-Protected Artifacts)
**Blocks:** None (enables charge_to for Plan #234)

---

## Gap

**Current:**
- `resource_payer = intent.principal_id` always (action_executor.py:1508)
- Only the caller can pay for operations - no delegation mechanism
- `charge_to` enum defined in CONCEPTUAL_MODEL.yaml but not enforced
- Settlement path has multiple non-atomic operations (race condition risk)

**Target:**
- Principals can delegate charging authority to other principals/artifacts
- Delegation records are non-forgeable (using kernel_protected from Plan #235)
- Settlement is atomic: check -> debit -> record under single transaction boundary
- Rate-limited charging with per-call and per-window caps

**Why High:**
- Enables "target pays" and "pool pays" patterns from charge_to enum
- Required for artifact-as-a-service business models
- Foundation for sophisticated economic patterns (sponsors, pools, escrow)

---

## References Reviewed

- `src/world/action_executor.py:1508` - `resource_payer = intent.principal_id`
- `src/world/action_executor.py:1565-1572` - Settlement path (non-atomic)
- `src/world/ledger.py:120-121` - `_scrip_lock` and `_resource_lock` exist
- `src/world/rate_tracker.py` - Existing rate window tracking pattern
- `docs/CONCEPTUAL_MODEL.yaml` - `charge_to: enum [caller, target, contract, pool]`
- `docs/adr/0016-created-by-not-owner.md` - `created_by` as authority anchor
- ChatGPT dialogue (2026-01-31) - Delegation schema design, atomicity requirements

---

## Open Questions

### Resolved

1. [x] **Question:** Where should delegation records be stored?
   - **Status:** ✅ Complete

**Verified:** 2026-01-31T23:55:25Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-31T23:55:25Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 0d0fd25
```
   - **Answer:** As artifacts with `type="charge_delegation"`, using `kernel_protected: true`
   - **Verified in:** Dialogue with ChatGPT - follows "everything is artifact" philosophy

2. [x] **Question:** What is the ID pattern for delegation artifacts?
   - **Status:** ✅ Complete

**Verified:** 2026-01-31T23:55:25Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-31T23:55:25Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 0d0fd25
```
   - **Answer:** `charge_delegation:{payer_id}` - deterministic, one per payer
   - **Verified in:** Design discussion - enables O(1) lookup

3. [x] **Question:** Who can issue delegations?
   - **Status:** ✅ Complete

**Verified:** 2026-01-31T23:55:25Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-31T23:55:25Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 0d0fd25
```
   - **Answer:** Only the payer themselves (interim rule - no transferable authority)
   - **Verified in:** `created_by` is the only safe anchor; `authorized_writer` is forgeable

4. [x] **Question:** Does Plan #236 require Plan #234 (handle_request)?
   - **Status:** ✅ Complete

**Verified:** 2026-01-31T23:55:25Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-31T23:55:25Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 0d0fd25
```
   - **Answer:** No - can implement under ADR-0019 by adding delegation check to settlement path
   - **Verified in:** ChatGPT analysis - settlement is post-execution, independent of access checking

### Before Planning

1. [ ] **Question:** Can artifacts be payers (have standing)?
   - **Status:** ✅ Complete

**Verified:** 2026-01-31T23:55:25Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-31T23:55:25Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 0d0fd25
```
   - **Why it matters:** Affects `has_authority(caller, payer)` implementation

---

## Files Affected

- `src/world/kernel_interface.py` (modify) - Add delegation primitives
- `src/world/action_executor.py` (modify) - Integrate delegation check in settlement
- `src/world/ledger.py` (modify) - Add atomic settlement wrapper
- `src/world/delegation.py` (create) - Delegation record management
- `tests/unit/test_delegation.py` (create)
- `tests/integration/test_charge_delegation.py` (create)

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `delegation.py` | New module: delegation schema, authorization, rate tracking |
| `kernel_interface.py` | Add `grant_charge_delegation()`, `revoke_charge_delegation()`, `authorize_charge()` |
| `action_executor.py` | Replace `resource_payer = intent.principal_id` with delegation-aware resolution |
| `ledger.py` | Add `atomic_settlement()` wrapper for transaction boundary |

### Delegation Artifact Schema

```python
# Artifact: charge_delegation:{payer_id}
{
    "id": "charge_delegation:alice",
    "type": "charge_delegation",
    "created_by": "alice",  # Immutable authority anchor
    "content": {
        "delegations": [
            {
                "charger_id": "artifact_B",
                "max_per_call": 10.0,
                "max_per_window": 100.0,
                "window_seconds": 3600,
                "expires_at": null
            }
        ]
    },
    "metadata": {
        "kernel_protected": true,
        "access_contract_id": "kernel_contract_private"
    }
}
```

### Kernel Primitives

```python
# In kernel_interface.py

def grant_charge_delegation(
    self,
    caller_id: str,
    charger_id: str,
    max_per_call: float | None = None,
    max_per_window: float | None = None,
    window_seconds: int = 60,
    expires_at: str | None = None,
) -> bool:
    """
    Grant permission for charger to charge caller's account.

    Caller IS the payer (can only grant delegations from yourself).
    Creates or updates charge_delegation:{caller_id} artifact.
    """
    ...

def revoke_charge_delegation(
    self,
    caller_id: str,
    charger_id: str,
) -> bool:
    """Revoke a previously granted charge delegation."""
    ...

def authorize_charge(
    self,
    charger_id: str,
    payer_id: str,
    amount: float,
) -> tuple[bool, str]:
    """
    Check if charger is authorized to charge payer.

    Returns (authorized, reason).
    """
    ...
```

### Atomic Settlement

```python
# In ledger.py

async def atomic_settlement(
    self,
    payer_id: str,
    charger_id: str,
    amount: float,
    delegation_checker: Callable,
) -> tuple[bool, str]:
    """
    Atomic: authorize -> debit -> record.

    All operations under single lock to prevent race conditions.
    """
    async with self._settlement_lock:
        # 1. Check delegation authorization
        authorized, reason = delegation_checker(charger_id, payer_id, amount)
        if not authorized:
            return False, reason

        # 2. Debit payer
        if not self.deduct_scrip(payer_id, amount):
            return False, "Insufficient funds"

        # 3. Record charge for rate window tracking
        self._record_charge(payer_id, charger_id, amount)

        return True, "Settlement complete"
```

### Steps

1. **Create delegation.py module**
   - DelegationRecord dataclass
   - `authorize_charge()` algorithm
   - Rate window tracking (similar to rate_tracker.py)

2. **Add kernel primitives**
   - `grant_charge_delegation()` - creates/updates delegation artifact
   - `revoke_charge_delegation()` - removes delegation entry
   - `authorize_charge()` - checks delegation and caps

3. **Add atomic settlement**
   - New lock in ledger: `_settlement_lock`
   - `atomic_settlement()` method wrapping check->debit->record

4. **Integrate in action_executor**
   - Replace hardcoded `resource_payer = intent.principal_id`
   - Add delegation lookup and authorization
   - Use atomic_settlement for non-caller payers

5. **Add rate window tracking**
   - Track recent charges per (payer, charger) pair
   - Prune old entries beyond max window
   - Checkpoint integration for simulation resume

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies | Failure Mode |
|-----------|---------------|------------------|--------------|
| `tests/unit/test_delegation.py` | `test_grant_delegation_creates_artifact` | Delegation artifact created correctly | Basic |
| `tests/unit/test_delegation.py` | `test_grant_delegation_only_self` | Can only delegate own resources | Basic |
| `tests/unit/test_delegation.py` | `test_authorize_charge_valid` | Authorization succeeds with valid delegation | Basic |
| `tests/unit/test_delegation.py` | `test_authorize_charge_no_delegation` | Authorization fails without delegation | Basic |
| `tests/unit/test_delegation.py` | `test_authorize_charge_exceeds_cap` | Authorization fails when cap exceeded | Basic |
| `tests/unit/test_delegation.py` | `test_authorize_charge_expired` | Authorization fails when delegation expired | Basic |
| `tests/unit/test_delegation.py` | `test_rate_window_enforcement` | Per-window cap enforced | Basic |
| `tests/unit/test_delegation.py` | `test_revoke_delegation` | Revocation removes authorization | Basic |
| `tests/unit/test_delegation.py` | `test_concurrent_charges_respect_caps` | Race conditions don't bypass caps | **FM-1** |
| `tests/unit/test_delegation.py` | `test_payer_resolution_ignores_forgeable_metadata` | Never use mutable fields | **FM-2** |
| `tests/unit/test_delegation.py` | `test_payer_must_be_principal_not_artifact` | Artifacts can't be payers | **FM-3** |
| `tests/unit/test_delegation.py` | `test_window_accounting_bounded_memory` | Pruning works, no unbounded growth | **FM-5** |
| `tests/integration/test_charge_delegation.py` | `test_delegated_charge_succeeds` | Full flow: grant -> invoke -> charge | Integration |
| `tests/integration/test_charge_delegation.py` | `test_delegated_charge_atomic` | Settlement is atomic under concurrency | Integration |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_ledger*.py` | Ledger operations unchanged for caller-pays |
| `tests/unit/test_executor*.py` | Executor behavior preserved |
| `tests/integration/test_invoke*.py` | Existing invoke flows work |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Delegated charging | 1. Alice grants delegation to Bob 2. Bob invokes artifact 3. Alice is charged | Alice's balance decremented, Bob's unchanged |
| Cap enforcement | 1. Grant with max_per_call=5 2. Try to charge 10 | Charge rejected |
| Rate window | 1. Grant with max_per_window=100 2. Charge 60 3. Charge 60 | Second charge rejected |

```bash
# Run E2E verification
pytest tests/integration/test_charge_delegation.py -v
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 236`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] E2E verification passes

### Documentation
- [ ] `docs/architecture/current/resources.md` updated
- [ ] `docs/CONCEPTUAL_MODEL.yaml` updated with delegation definitions
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status to `✅ Complete`
- [ ] `plans/CLAUDE.md` index updated
- [ ] Claim released
- [ ] Branch merged

---

## Uncertainties

| Question | Status | Resolution |
|----------|--------|------------|
| Should delegation transfer be supported later? | ⏸️ Deferred | Not in v1 - requires transferable authority |
| Should artifacts with standing be payers? | ✅ Resolved | **Interim: Principals only.** See FM-3 below. |
| How to handle delegation artifact deletion? | ✅ Resolved | **Blocked.** Delegation artifacts are kernel_protected (Plan #235). |

---

## Critical Failure Modes (ChatGPT Review)

These failure modes MUST be addressed with explicit tests:

### FM-1: Atomic Settlement is Mandatory

**Attack:** Race condition - two concurrent charges bypass per-window cap.
```
Thread A: check cap (90/100 used) -> OK
Thread B: check cap (90/100 used) -> OK
Thread A: debit 20 -> success (110/100 used!)
Thread B: debit 20 -> success (130/100 used!)
```

**Mitigation:** Single lock around **entire** check→debit→record sequence:
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

**Lock acquisition order:** If multiple locks needed, always acquire in same order to prevent deadlock.

**Test:** `test_concurrent_charges_respect_caps` (spawn multiple threads, verify cap not exceeded)

### FM-2: Payer Resolution Must Not Depend on Forgeable Fields

**Attack:** Malicious artifact sets `metadata.authorized_writer = rich_victim`, then returns `charge_to: target`. Victim is charged without consent.

**Mitigation:** Payer resolution uses ONLY kernel-trustworthy anchors:
```python
def resolve_payer(charge_to: str, artifact: Artifact) -> str:
    if charge_to == "caller":
        return intent.principal_id  # Always safe
    elif charge_to == "target":
        # ONLY use created_by (immutable), NOT authorized_writer (forgeable)
        return artifact.created_by
    elif charge_to == "contract":
        contract = get_contract(artifact)
        return contract.created_by  # Immutable
    elif charge_to.startswith("pool:"):
        payer_id = charge_to.split(":")[1]
        # Delegation check happens AFTER resolution
        return payer_id
    else:
        raise ValueError(f"Unknown charge_to: {charge_to}")
```

**NEVER consult:** `authorized_writer`, any `metadata.*` field, or any other mutable data.

**Test:** `test_payer_resolution_ignores_forgeable_metadata`

### FM-3: Payer Identity Must Be Formally Defined

**Question:** Can artifacts be payers (have standing)?

**Answer (Interim):** **Principals only.** An artifact cannot be charged because:
1. Artifacts don't have "accounts" in the ledger (only principals do)
2. If artifacts could be payers, we'd need "controller" semantics
3. `created_by` is the only safe controller anchor, but it's non-transferable

**Implication:** `charge_to: target` resolves to `artifact.created_by` (the principal who created it), NOT to the artifact itself.

**Future:** If artifacts need to "pay" directly, implement as a separate plan with explicit controller semantics.

**Test:** `test_payer_must_be_principal_not_artifact`

### FM-4: Anti-Squatting Rule for Delegation IDs

**Attack:** Attacker creates `charge_delegation:victim` before victim, adds delegation to themselves.

**Mitigation:** Plan #235 enforces: `charge_delegation:X` can ONLY be created by principal X.

**Test:** (Covered in Plan #235) `test_id_squatting_blocked`

### FM-5: Window Accounting Needs Bounded Storage

**Attack:** Unbounded rate-window logs cause memory exhaustion.

**Mitigation:**
1. **Deterministic pruning:** On every charge, prune entries older than `max_window_seconds`
2. **Bounded per-pair:** Max 1000 entries per (payer, charger) pair; oldest evicted first
3. **Checkpoint integration:** Rate-window state included in simulation checkpoints

```python
def _record_charge(self, payer_id: str, charger_id: str, amount: float):
    key = (payer_id, charger_id)
    now = time.time()

    # Add new entry
    self._charge_history.setdefault(key, []).append((now, amount))

    # Prune old entries (deterministic, bounded)
    max_age = self._max_window_seconds
    self._charge_history[key] = [
        (ts, amt) for ts, amt in self._charge_history[key]
        if now - ts <= max_age
    ][-1000:]  # Hard cap
```

**Test:** `test_window_accounting_bounded_memory`

---

## Updated Tests (TDD)

| Test File | Test Function | Failure Mode |
|-----------|---------------|--------------|
| `test_delegation.py` | `test_grant_delegation_creates_artifact` | Basic |
| `test_delegation.py` | `test_grant_delegation_only_self` | Basic |
| `test_delegation.py` | `test_authorize_charge_valid` | Basic |
| `test_delegation.py` | `test_authorize_charge_no_delegation` | Basic |
| `test_delegation.py` | `test_authorize_charge_exceeds_cap` | Basic |
| `test_delegation.py` | `test_authorize_charge_expired` | Basic |
| `test_delegation.py` | `test_revoke_delegation` | Basic |
| `test_delegation.py` | `test_concurrent_charges_respect_caps` | **FM-1** |
| `test_delegation.py` | `test_payer_resolution_ignores_forgeable_metadata` | **FM-2** |
| `test_delegation.py` | `test_payer_must_be_principal_not_artifact` | **FM-3** |
| `test_delegation.py` | `test_window_accounting_bounded_memory` | **FM-5** |
| `test_charge_delegation.py` | `test_delegated_charge_succeeds` | Integration |
| `test_charge_delegation.py` | `test_delegated_charge_atomic` | Integration |

---

## Notes

**Design rationale:**
- Artifact-based storage for observability and "everything is artifact" philosophy
- Deterministic ID pattern enables O(1) lookup
- Rate window tracking follows existing rate_tracker.py pattern
- Atomic settlement prevents race condition cap bypass

**Authority model (interim):**
- Only principals can delegate their own resources
- Only `created_by` can delegate on behalf of an artifact (non-transferable)
- Full transferable authority deferred to post-ADR-0024

**Relationship to charge_to enum:**
- `caller` - No delegation needed (current behavior)
- `target` - Resolve to artifact.created_by, check delegation
- `contract` - Resolve to contract.created_by, check delegation
- `pool:{id}` - Explicit payer ID, check delegation

**ChatGPT validation:**
- Schema design validated through dialogue
- Atomicity requirement identified as critical (FM-1)
- ID squatting attack identified and mitigated via Plan #235 (FM-4)
- Payer resolution rules: never consult mutable metadata (FM-2)
- Payer identity: principals only for v1 (FM-3)
- Window accounting: bounded storage required (FM-5)
- ChatGPT review (2026-01-31) identified FM-1 through FM-5
