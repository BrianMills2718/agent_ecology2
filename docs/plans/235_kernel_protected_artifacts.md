# Plan 235: Kernel-Protected Artifacts

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** #236 (Charge Delegation)

---

## Gap

**Current:**
- Any artifact with write permission can have its content/metadata modified via `edit_artifact`
- No mechanism to mark artifacts as "kernel-only modifiable"
- Reserved ID namespaces (like `charge_delegation:{payer_id}`) have no creation restrictions
- **`type` field is mutable** - used for kernel branching but can be changed via `write_artifact` (type-confusion vulnerability)
- **`access_contract_id` is mutable by anyone with write permission** - policy-pointer swap vulnerability
- **Note:** `src/world/rights.py` was removed per ADR-0025 (tokenized rights deferred), but these protections are still needed for any value-storing artifacts (triggers, configs, future tokens)

**Target:**
- `kernel_protected: true` system field prevents `edit_artifact`/`write_artifact` modifications
- Only kernel primitives can modify protected artifacts
- Reserved ID prefixes (e.g., `charge_delegation:`, `right:`) enforce creation restrictions
- Rights cannot be "counterfeited" by editing artifact content
- **`type` is immutable after creation** - reject changes in `ArtifactStore.write()`
- **`access_contract_id` is creator-only** - only `created_by` can change it

**Why High:**
- Rights forgery is a critical security gap - anyone with write access can inflate their resource rights
- Charge delegation (Plan #236) depends on non-forgeable delegation records
- This is foundational for any artifact that stores "value" (scrip amounts, delegations, rights)
- **Type-confusion vulnerability** - attacker can flip `type` to "right"/"trigger"/"config" and get privileged handling
- **Authorization bypass** - attacker with write permission can swap `access_contract_id` to permissive contract

---

## References Reviewed

- `src/world/action_executor.py:469-473` - Metadata merge happens without field restrictions
- `src/world/action_executor.py:_execute_edit()` - edit_artifact path
- `src/world/action_executor.py:467-468` - `access_contract_id` modifiable via edit
- `src/world/artifacts.py:793-861` - **Central enforcement point**: `ArtifactStore.write()`
- `src/world/artifacts.py:802` - `artifact.type = type` allows type mutation
- `src/world/artifacts.py:810-811` - `access_contract_id` mutation path
- `src/world/triggers.py:209` - Kernel branches on `artifact.type != "trigger"`
- ~~`src/world/rights.py`~~ - Removed per ADR-0025 (tokenized rights deferred)
- `docs/adr/0016-created-by-not-owner.md` - Immutability pattern for `created_by`
- `docs/CONCEPTUAL_MODEL.yaml` - Target architecture definitions
- ChatGPT dialogue (2026-01-31) - Identified rights forgery, ID squatting, type-confusion, policy-pointer swap attacks

---

## Open Questions

### Resolved

1. [x] **Question:** Is `created_by` actually immutable?
   - **Status:** ✅ RESOLVED
   - **Answer:** Yes - no `.created_by =` in kernel code (only dashboard visualization)
   - **Verified in:** `src/world/artifacts.py:write()`, ADR-0016

2. [x] **Question:** Can metadata fields be modified via `edit_artifact`?
   - **Status:** ✅ RESOLVED
   - **Answer:** Yes - `action_executor.py:469-473` merges all metadata without restrictions
   - **Verified in:** `src/world/action_executor.py:469-473`

3. [x] **Question:** What ID prefixes need reservation?
   - **Status:** ✅ RESOLVED
   - **Answer:** `charge_delegation:`, `right:` (future: any artifact storing economic value)
   - **Verified in:** Dialogue with ChatGPT, design discussion

---

## Files Affected

- `src/world/action_executor.py` (modify) - Add kernel_protected check in edit/write paths
- `src/world/artifacts.py` (modify) - Add reserved ID namespace validation in create
- `src/world/kernel_interface.py` (modify) - Add `modify_protected_artifact()` primitive
- Note: `src/world/rights.py` removed per ADR-0025. When tokenized rights resume, they would use these kernel primitives.
- `tests/unit/test_kernel_protected.py` (create)
- `tests/integration/test_rights_protection.py` (create)

---

## Plan

### Changes Required

| File | Change | Phase |
|------|--------|-------|
| `artifacts.py:797` | **Block `type` mutation** - reject if `type != existing.type` | **Phase 0** |
| `artifacts.py:810` | **Creator-only `access_contract_id`** - reject if changer != `created_by` | **Phase 0** |
| `action_executor.py:467` | **Creator-only `access_contract_id`** in edit path | **Phase 0** |
| `action_executor.py` | Check `kernel_protected` system field before allowing edit/write | Phase 1 |
| `artifacts.py` | Validate reserved ID prefixes on artifact creation | Phase 1 |
| `artifacts.py` | Add `kernel_protected` as system field (not metadata) | Phase 1 |
| ~~`rights.py`~~ | ~~Route through kernel primitive~~ (removed per ADR-0025) | N/A |
| `kernel_interface.py` | Add `modify_protected_content()` for kernel-only updates | Phase 1 |

### Steps

#### Phase 0: Close Confirmed Authorization Bypasses (IMMEDIATE)

**0.1. Block `type` mutation in `ArtifactStore.write()` (artifacts.py:797)**
```python
# In ArtifactStore.write() - BEFORE any mutations to existing artifact
if artifact_id in self.artifacts:
    existing = self.artifacts[artifact_id]

    # FM-6: type is immutable after creation
    if type != existing.type:
        raise ValueError(f"Cannot change artifact type from '{existing.type}' to '{type}'")

    # ... rest of existing update logic
```

**0.2. Creator-only `access_contract_id` in `ArtifactStore.write()` (artifacts.py:810)**
```python
# In ArtifactStore.write() - BEFORE allowing access_contract_id change
if artifact_id in self.artifacts:
    existing = self.artifacts[artifact_id]

    # FM-7: Only creator can change access_contract_id
    if access_contract_id is not None and access_contract_id != existing.access_contract_id:
        if created_by != existing.created_by:
            raise PermissionError(
                f"Only creator '{existing.created_by}' can change access_contract_id"
            )
```

**0.3. Creator-only `access_contract_id` in `_execute_edit()` (action_executor.py:467)**
```python
# In _execute_edit - before adding to updates dict
if intent.access_contract_id is not None:
    if intent.access_contract_id != artifact.access_contract_id:
        if intent.principal_id != artifact.created_by:
            return ActionResult(
                success=False,
                message="Only creator can change access_contract_id",
                error_code=ErrorCode.PERMISSION_DENIED.value,
            )
    updates["access_contract_id"] = intent.access_contract_id
```

#### Phase 1: kernel_protected and Reserved Namespaces

**1.1. Add kernel_protected check in action_executor**
```python
# In _execute_edit and _execute_write
# kernel_protected is a SYSTEM FIELD, not metadata
if getattr(artifact, 'kernel_protected', False):
    return ActionResult(
        success=False,
        error="kernel_protected: modification only via kernel primitives"
    )
```

**1.2. Add reserved ID namespace enforcement**
```python
# In artifact creation path
RESERVED_PREFIXES = {
    "charge_delegation:": lambda caller, artifact_id: caller == artifact_id.split(":")[1],
    "right:": lambda caller, artifact_id: True,  # Rights created by kernel
}

for prefix, validator in RESERVED_PREFIXES.items():
    if artifact_id.startswith(prefix):
        if not validator(caller_id, artifact_id):
            raise PermissionError(f"Cannot create {prefix} artifact for another principal")
```

**1.3. Add kernel primitive for protected artifact modification**
```python
# In kernel_interface.py
def modify_protected_content(self, artifact_id: str, new_content: str) -> bool:
    """Kernel-only: modify content of a kernel_protected artifact."""
    artifact = self._world.artifacts.get(artifact_id)
    if artifact is None:
        return False
    artifact.content = new_content
    return True
```

**1.4. (Deferred)** ~~Update rights.py to use kernel primitive~~ - Removed per ADR-0025. When tokenized rights resume, they would use `modify_protected_content()`.

**1.5. (Deferred)** ~~Mark rights artifacts as kernel_protected on creation~~ - Removed per ADR-0025.

---

## Required Tests

### Phase 0 Tests (IMMEDIATE - Must implement first)

| Test File | Test Function | What It Verifies | Failure Mode |
|-----------|---------------|------------------|--------------|
| `tests/unit/test_kernel_protected.py` | `test_type_flip_to_right_blocked` | Can't change type to "right" after creation | **FM-6** |
| `tests/unit/test_kernel_protected.py` | `test_type_flip_to_trigger_blocked` | Can't change type to "trigger" after creation | **FM-6** |
| `tests/unit/test_kernel_protected.py` | `test_type_flip_to_config_blocked` | Can't change type to "config" after creation | **FM-6** |
| `tests/unit/test_kernel_protected.py` | `test_non_creator_cannot_swap_access_contract` | Non-creator write can't change access_contract_id | **FM-7** |
| `tests/unit/test_kernel_protected.py` | `test_creator_can_change_access_contract` | Creator CAN change access_contract_id | **FM-7** |
| `tests/unit/test_kernel_protected.py` | `test_authorized_writer_cannot_swap_access_contract` | authorized_writer can write but NOT swap contract | **FM-7** |

### Phase 1 Tests (kernel_protected and Reserved Namespaces)

| Test File | Test Function | What It Verifies | Failure Mode |
|-----------|---------------|------------------|--------------|
| `tests/unit/test_kernel_protected.py` | `test_edit_blocked_on_protected_artifact` | edit_artifact fails with kernel_protected=true | Basic |
| `tests/unit/test_kernel_protected.py` | `test_write_blocked_on_protected_artifact` | write_artifact fails with kernel_protected=true | Basic |
| `tests/unit/test_kernel_protected.py` | `test_kernel_primitive_can_modify_protected` | Kernel can modify via primitive | Basic |
| `tests/unit/test_kernel_protected.py` | `test_cannot_toggle_kernel_protected_via_edit` | Can't set kernel_protected=false via edit | **FM-1** |
| `tests/unit/test_kernel_protected.py` | `test_protection_covers_content_code_and_metadata` | All fields protected | **FM-2** |
| `tests/unit/test_kernel_protected.py` | `test_system_fields_immutable_regardless_of_protection` | System fields never modifiable | **FM-3** |
| `tests/unit/test_kernel_protected.py` | `test_id_squatting_blocked` | Attacker can't squat on victim's ID | **FM-4** |
| `tests/unit/test_kernel_protected.py` | `test_self_id_creation_allowed` | Can create `charge_delegation:X` if caller == X | **FM-4** |
| `tests/integration/test_rights_protection.py` | `test_right_amount_forgery_blocked` | Can't inflate right amount via edit_artifact | Rights |
| `tests/integration/test_rights_protection.py` | `test_right_amount_updated_via_kernel` | Kernel primitive updates work | Rights |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| ~~`tests/unit/test_rights*.py`~~ | ~~Rights functionality~~ (removed per ADR-0025) |
| `tests/unit/test_executor*.py` | Executor behavior unchanged for non-protected artifacts |
| `tests/integration/test_artifact*.py` | Artifact operations work for normal artifacts |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Rights forgery blocked | 1. Create right artifact 2. Try to edit amount via edit_artifact | Fails with kernel_protected error |
| Kernel update works | 1. Create right artifact 2. Consume via kernel primitive | Amount decremented correctly |
| ID squatting blocked | 1. Attacker tries to create `charge_delegation:victim` | Creation fails with permission error |

```bash
# Run E2E verification
pytest tests/integration/test_rights_protection.py -v
pytest tests/unit/test_kernel_protected.py -v
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 235`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] E2E verification passes

### Documentation
- [ ] `docs/architecture/current/artifacts_executor.md` updated
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`
- [ ] ADR-0025 created for kernel_protected pattern

### Completion Ceremony
- [ ] Plan file status to `✅ Complete`
- [ ] `plans/CLAUDE.md` index updated
- [ ] Claim released
- [ ] Branch merged

---

## Uncertainties

| Question | Status | Resolution |
|----------|--------|------------|
| Should kernel_protected be a top-level field or metadata? | ✅ Resolved | **Top-level system field** - NOT metadata. If in metadata, attacker could toggle it. |
| Should we allow "un-protecting" an artifact? | ✅ Resolved | **No** - once protected, always protected. Irreversible. |

---

## Critical Failure Modes (ChatGPT Review)

These failure modes MUST be addressed with explicit tests:

### FM-1: kernel_protected Must Not Be User-Writable

**Attack:** Attacker uses `edit_artifact` to set `kernel_protected=false`, then modifies content.

**Mitigation:** `kernel_protected` is a **system field** (like `created_by`), not metadata. The kernel:
1. Ignores any `kernel_protected` value in user-provided metadata
2. Only sets it internally via kernel primitives
3. Rejects any edit/write attempt on protected artifacts regardless of metadata changes

**Test:** `test_cannot_toggle_kernel_protected_via_edit`

### FM-2: Protection Surface Must Be Precise

**Attack:** Ambiguity about what's protected allows attacker to modify unprotected parts.

**Mitigation:** When `kernel_protected=true`, ALL of these are blocked for user actions:
- `content` - artifact data
- `code` - executable code
- `metadata` - all key-value pairs
- Only **kernel primitives** can modify any field

**Test:** `test_protection_covers_content_code_and_metadata`

### FM-3: System Field Immutability Must Be Enforced

**Attack:** Even without `kernel_protected`, attacker tries to modify `created_by`, `id`, `type`, etc.

**Mitigation:** Kernel rejects updates to system fields regardless of protection status:
```python
SYSTEM_FIELDS = {"id", "created_by", "type", "event_number", "kernel_protected"}
# These fields are NEVER modifiable via edit_artifact/write_artifact
```

**Test:** `test_system_fields_immutable_regardless_of_protection`

### FM-4: Reserved ID Namespace Enforcement at Creation

**Attack:** ID squatting - attacker creates `charge_delegation:victim` before victim.

**Mitigation:** Kernel enforces at artifact creation time:
```python
# charge_delegation:X can ONLY be created by principal X
if artifact_id.startswith("charge_delegation:"):
    payer_id = artifact_id.split(":")[1]
    if caller_id != payer_id:
        raise PermissionError("Cannot create delegation for another principal")
```

**Test:** `test_id_squatting_blocked`, `test_self_id_creation_allowed`

### FM-5: Dashboard created_by Mutation (Design Hazard)

**Issue:** Dashboard parser mutates `created_by` to show "current owner", causing conceptual drift.

**Mitigation:** Create follow-up task to:
1. Add `current_owner` display field to dashboard state (separate from `created_by`)
2. Keep `created_by` as immutable "original creator"
3. Track ownership transfers via `ownership_history` (already exists)

**Test:** N/A (dashboard-only, not security bug, but tracked for cleanup)

### FM-6: Type Field is Mutable but Used for Kernel Branching (PHASE 0)

**Attack:** Type-confusion - attacker creates normal artifact, then uses `write_artifact` to change `type` to "right", gaining privileged handling by kernel.

```python
# Kernel branches on type in multiple places:
# rights.py:250 - if artifact.type != "right": return ...
# triggers.py:209 - if artifact.type != "trigger": return ...
# genesis/memory.py:187 - if artifact.type != "memory_store": return ...
```

**Mitigation:** `type` is a **system field** - immutable after creation. In `ArtifactStore.write()`:
```python
# At artifacts.py:797 - BEFORE any mutations
if artifact_id in self.artifacts:
    existing = self.artifacts[artifact_id]
    if type != existing.type:
        raise ValueError("type is immutable after creation")
```

**Central enforcement point:** `ArtifactStore.write()` lines 793-861

**Tests:**
- `test_type_flip_to_right_blocked`
- `test_type_flip_to_trigger_blocked`
- `test_type_flip_to_config_blocked`

### FM-7: access_contract_id Mutable by Anyone with Write Permission (PHASE 0)

**Attack:** Policy-pointer swap - attacker with write permission changes `access_contract_id` to `genesis_contract_freeware`, making artifact publicly accessible.

```python
# Current code allows this (action_executor.py:467-468):
if intent.access_contract_id is not None:
    updates["access_contract_id"] = intent.access_contract_id
```

**Mitigation:** `access_contract_id` is **creator-only** - only `created_by` can change it:

```python
# In ArtifactStore.write() - around line 797
if artifact_id in self.artifacts:
    existing = self.artifacts[artifact_id]
    if access_contract_id is not None and access_contract_id != existing.access_contract_id:
        if created_by != existing.created_by:
            raise PermissionError("Only creator can change access_contract_id")

# In action_executor._execute_edit() - around line 467
if intent.access_contract_id is not None:
    if intent.access_contract_id != artifact.access_contract_id:
        if intent.principal_id != artifact.created_by:
            return ActionResult(success=False, error="Only creator can change access_contract_id")
```

**Note on future:** Contract-governed policy upgrade (where current contract authorizes the change) is the long-term goal under ADR-0024. Creator-only is the Phase 0 pragmatic fix.

**Tests:**
- `test_non_creator_cannot_swap_access_contract`
- `test_creator_can_change_access_contract`
- `test_authorized_writer_cannot_swap_access_contract`

---

## Updated Tests (TDD)

| Test File | Test Function | Failure Mode |
|-----------|---------------|--------------|
| `test_kernel_protected.py` | `test_edit_blocked_on_protected_artifact` | Basic protection |
| `test_kernel_protected.py` | `test_write_blocked_on_protected_artifact` | Basic protection |
| `test_kernel_protected.py` | `test_kernel_primitive_can_modify_protected` | Kernel bypass |
| `test_kernel_protected.py` | `test_cannot_toggle_kernel_protected_via_edit` | **FM-1** |
| `test_kernel_protected.py` | `test_protection_covers_content_code_and_metadata` | **FM-2** |
| `test_kernel_protected.py` | `test_system_fields_immutable_regardless_of_protection` | **FM-3** |
| `test_kernel_protected.py` | `test_id_squatting_blocked` | **FM-4** |
| `test_kernel_protected.py` | `test_self_id_creation_allowed` | **FM-4** |
| `test_kernel_protected.py` | `test_type_flip_to_right_blocked` | **FM-6 (Phase 0)** |
| `test_kernel_protected.py` | `test_type_flip_to_trigger_blocked` | **FM-6 (Phase 0)** |
| `test_kernel_protected.py` | `test_type_flip_to_config_blocked` | **FM-6 (Phase 0)** |
| `test_kernel_protected.py` | `test_non_creator_cannot_swap_access_contract` | **FM-7 (Phase 0)** |
| `test_kernel_protected.py` | `test_creator_can_change_access_contract` | **FM-7 (Phase 0)** |
| `test_kernel_protected.py` | `test_authorized_writer_cannot_swap_access_contract` | **FM-7 (Phase 0)** |
| `test_rights_protection.py` | `test_right_amount_forgery_blocked` | Rights security |
| `test_rights_protection.py` | `test_right_amount_updated_via_kernel` | Rights functionality |

---

## Notes

**Phased approach (ChatGPT recommendation):**
- **Phase 0 (IMMEDIATE):** Close confirmed authorization bypasses - `type` immutability, `access_contract_id` creator-only
- **Phase 1:** `kernel_protected` system field, reserved namespaces
- **Phase 2 (future):** Contract-governed policy upgrade under ADR-0024
- **Phase 3 (future):** "Everything is rights" including scrip

**Design rationale:**
- `kernel_protected` as **system field** (not metadata) prevents toggle attacks
- Reserved ID prefixes follow the same pattern as genesis artifact IDs
- The kernel primitive approach reuses existing architecture (kernel_actions pattern)
- System field immutability is enforced, not conventional
- Central enforcement at `ArtifactStore.write()` (lines 793-861) - single point of control

**Security model:**
- `kernel_protected` prevents ALL agent-level modifications (content, code, metadata)
- Only kernel primitives (not artifact code) can modify protected artifacts
- System fields (`id`, `created_by`, `type`, `event_number`, `kernel_protected`) are NEVER user-modifiable
- This is defense-in-depth: even if a contract allows write, kernel blocks it

**On `created_by` (ChatGPT guidance):**
- Keep `created_by` as **immutable provenance** (historical fact of who created it)
- Do NOT remove it - it's the only "hard anchor" for authorization until transferable authority exists
- Do NOT treat it as "current owner" - ownership is a separate concept
- Future: separate `controller_id` or authority mechanism for transferable control

**Related work:**
- ChatGPT/Claude dialogue identified this gap via "rights forgery" attack
- ADR-0016 established immutability pattern for `created_by`
- Plan #236 (Charge Delegation) depends on this for non-forgeable delegation records
- ChatGPT review (2026-01-31) identified FM-1 through FM-7
- Archive: `docs/archive/ARCHITECTURE_DECISIONS_2026_01.md:1564` - Contract Upgrade Path (future)
