# Plan 148: ADR-0019 Implementation Audit

**Status:** 📋 Planned (Audit Complete)
**Priority:** High
**Blocked By:** None
**Blocks:** Full contract-based permission system

## Problem Statement

ADR-0019 (Unified Permission Architecture) documents the target permission system, but current implementation may not fully align. This plan audits the codebase against ADR-0019 and closes gaps.

---

## Phase 1 Audit Results

### 1. Five Kernel Actions - All Contract-Checked

| Action | Contract-Checked? | Location | Notes |
|--------|-------------------|----------|-------|
| `read` | ✅ Yes | `world.py:706` | Uses `executor._check_permission()` |
| `write` | ✅ Yes | `world.py:810` | Uses `executor._check_permission()` |
| `edit` | ⚠️ Yes (as "write") | `world.py:921` | Checks "write" permission, not "edit" |
| `invoke` | ✅ Yes | `world.py:1013` | Uses `executor._check_permission()` |
| `delete` | ✅ Yes | `world.py:1141` | Uses `executor._check_permission()` |

**Gap:** `edit` action uses "write" permission, not a separate "edit" action. The `PermissionAction` enum has `WRITE` but no `EDIT`. Need to add `EDIT` action or document why "write" is sufficient.

### 2. Immediate Caller Model

**Status:** ❌ NOT IMPLEMENTED

**Finding:** In nested invoke (`executor.py:1292-1401`), the permission check at line 1334 passes `caller_id` which is the **original** caller, not the intermediate artifact:

```python
# Line 1334 - WRONG: passes original caller_id
allowed, reason = self._check_permission(caller_id, "invoke", target)
```

Per ADR-0019: When A invokes B which invokes C, C's contract should see **B** as caller, not A.

**Fix Required:** Change to pass `artifact_id` (the current artifact) as caller for nested invokes.

### 3. Null Contract Default

**Status:** ❌ NOT IMPLEMENTED

**Finding:** Current behavior (`executor.py:795-802`):
- When `access_contract_id` is None, falls back to **legacy policy**
- Legacy policy (`executor.py:715-770`) delegates to **freeware** contract
- This allows anyone to read/invoke, NOT creator-only as ADR-0019 specifies

**Config option:** `contracts.default_when_null` is documented in ADR but:
- ❌ Not in `config/schema.yaml`
- ❌ Not used anywhere in code

**Fix Required:**
1. Add config option to schema
2. Implement creator-only default when null

### 4. Dangling Contract Fallback

**Status:** ✅ IMPLEMENTED

**Finding:** `executor.py:560-578` handles dangling contracts correctly:
- Increments `_dangling_contract_count` for observability
- Logs warning message
- Falls back to `contracts.default_on_missing` config (line 565)
- Defaults to freeware if config not set

**Config option:** `contracts.default_on_missing` IS used but:
- ⚠️ Not in `config/schema.yaml` (should be documented)

### 5. Minimal Context

**Status:** ❌ DOES NOT MATCH ADR-0019

**Current context** (`executor.py:675-679`):
```python
context = {
    "created_by": artifact.created_by,  # Key name mismatch
    "artifact_type": artifact.type,      # NOT in ADR spec
    "artifact_id": artifact.id,          # NOT in ADR spec
}
```

**ADR-0019 specifies:**
```python
context = {
    "caller": str,             # Currently passed separately
    "action": str,             # Currently passed separately
    "target": str,             # Currently passed separately
    "target_created_by": str,  # Key named "created_by" instead
    "method": str,             # NOT passed (invoke only)
    "args": list,              # NOT passed (invoke only)
}
```

**Gaps:**
1. ❌ `created_by` should be renamed to `target_created_by`
2. ❌ `artifact_type` included but NOT in spec
3. ❌ `artifact_id` included but NOT in spec (target passed separately)
4. ❌ `method` not included for invoke
5. ❌ `args` not included for invoke
6. ⚠️ `caller` and `action` passed as params, not in context dict (acceptable)

### 6. Freeware Kernel Optimization

**Status:** ✅ NOT IMPLEMENTED (ACCEPTABLE)

ADR says kernel "MAY" skip contract call. Not implemented, but this is an optional optimization, not a requirement.

### 7. Genesis Not Privileged

**Status:** ⚠️ PARTIAL - Hardcoded Checks Found

**Genesis contracts** (Plan #100): ✅ Use same code path as user contracts

**Genesis artifacts** with hardcoded permission checks:
- `src/world/genesis/memory.py:273-282` - Hardcoded owner check for `add`
- `src/world/genesis/memory.py:401-410` - Hardcoded owner check for `delete`

These checks bypass the contract system. The memory artifacts they operate on have `access_contract_id` but it's not checked.

**Question:** Is this acceptable because:
- GenesisMemory is checking *its own* business logic (only owner can modify their memory)?
- Or should it delegate to the target artifact's contract?

---

## Summary of Gaps

| Requirement | Status | Severity | Fix Complexity |
|-------------|--------|----------|----------------|
| Five actions contract-checked | ✅ Mostly | Low | Add EDIT action |
| Immediate caller model | ❌ Missing | **High** | Medium |
| Null contract default | ❌ Missing | **High** | Medium |
| Dangling contract fallback | ✅ Done | - | - |
| Minimal context | ❌ Wrong | Medium | Low |
| Freeware optimization | ⚠️ Optional | - | - |
| Genesis not privileged | ⚠️ Partial | Low | Decision needed |

---

## ADR-0019 Requirements (Reference)

### 1. Five Kernel Actions - All Contract-Checked

| Action | Purpose | Contract-Checked? |
|--------|---------|-------------------|
| `read` | Read artifact content | ✅ Yes |
| `write` | Create/replace artifact | ✅ Yes |
| `edit` | Surgical content modification | ⚠️ Uses "write" |
| `invoke` | Call method on artifact | ✅ Yes |
| `delete` | Remove artifact | ✅ Yes |

### 2. Immediate Caller Model

When A→B→C, C's contract should see B (not A) as caller.

- **Status:** ❌ Not implemented

### 3. Null Contract Default

When `access_contract_id` is null:
- Creator has full rights
- All others blocked
- Configurable via `contracts.default_when_null`

- **Status:** ❌ Not implemented
- **Config option:** Not in schema

### 4. Dangling Contract Fallback

When `access_contract_id` points to deleted contract:
- Fall back to configurable default (freeware)
- Log warning
- Configurable via `contracts.default_on_missing`

- **Status:** ✅ Implemented
- **Config option:** Used but not in schema

### 5. Minimal Context

Kernel should provide only:
```python
context = {
    "caller": str,
    "action": str,
    "target": str,
    "target_created_by": str,
    "method": str,      # invoke only
    "args": list,       # invoke only
}
```

- **Status:** ❌ Context keys don't match spec

### 6. Freeware Kernel Optimization

Kernel MAY skip contract call for `genesis_freeware_contract`.

- **Status:** ⚠️ Not implemented (optional)

### 7. Genesis Not Privileged

Genesis contracts should use same code path as user contracts.

- **Status:** ⚠️ Partial (hardcoded checks in GenesisMemory)

## Implementation Tasks

### Phase 1: Audit ✅ COMPLETE

- [x] Audit `src/world/executor.py` - which actions check contracts?
- [x] Audit `src/world/contracts.py` - what context is passed?
- [x] Audit `src/world/artifacts.py` - null/dangling contract handling?
- [x] Audit `src/world/genesis/*.py` - hardcoded permission checks?
- [x] Document gaps in this plan

### Phase 2: Immediate Caller Model (HIGH PRIORITY)

This is the most critical gap - fundamentally changes permission semantics.

- [ ] Update `executor.py:1334` to pass `artifact_id` instead of `caller_id` for nested invokes
- [ ] Track "original caller" separately if needed for billing (separate from permission checking)
- [ ] Add tests for immediate caller model
- [ ] Update docstrings to clarify caller semantics

### Phase 3: Null Contract Default (HIGH PRIORITY)

- [ ] Add `contracts.default_when_null` to `config/schema.yaml`
- [ ] Add `contracts.default_on_missing` to `config/schema.yaml` (document existing)
- [ ] Update `src/config_schema.py` with new options
- [ ] Implement null contract → creator-only behavior in `executor.py:795-802`
- [ ] Add tests for null contract default

### Phase 4: Context Alignment (MEDIUM PRIORITY)

- [ ] Rename `created_by` → `target_created_by` in context dict
- [ ] Remove `artifact_type` from context (or document why needed)
- [ ] Remove `artifact_id` from context (target passed separately)
- [ ] Add `method` and `args` to context for invoke actions
- [ ] Update tests for new context structure

### Phase 5: Edit Action (LOW PRIORITY)

- [ ] Add `EDIT = "edit"` to `PermissionAction` enum in `contracts.py`
- [ ] Update `world.py:921` to check "edit" permission instead of "write"
- [ ] Update genesis contracts to handle "edit" action
- [ ] Add tests for edit action
- [ ] OR: Document that "write" implies "edit" (if acceptable)

### Phase 6: Genesis Alignment (DECISION NEEDED)

**Question for user:** Should GenesisMemory's hardcoded owner checks be replaced with contract checks?

Options:
1. **Keep hardcoded**: GenesisMemory is checking its own service logic (acceptable)
2. **Use contracts**: Delegate to target artifact's `access_contract_id` for full ADR compliance

- [ ] Get decision on approach
- [ ] If option 2: Update `genesis/memory.py` to use `_check_permission` for target artifacts
- [ ] Document reasoning for chosen approach

### Phase 7: Verification

- [ ] All five actions contract-checked (or documented exceptions)
- [ ] Immediate caller model working correctly
- [ ] Null/dangling behavior matches ADR-0019
- [ ] Context matches ADR-0019 spec
- [ ] All tests pass

## Files Affected

**Core permission logic:**
- `src/world/executor.py:1334` - Immediate caller model fix
- `src/world/executor.py:795-802` - Null contract default
- `src/world/executor.py:675-679` - Context structure
- `src/world/contracts.py:52-76` - Add EDIT action to enum

**Genesis artifacts:**
- `src/world/genesis/memory.py:273-282, 401-410` - Hardcoded owner checks
- `src/world/genesis_contracts.py` - May need EDIT action handling

**Config:**
- `config/schema.yaml` - Add contracts.default_when_null, document contracts.default_on_missing
- `src/config_schema.py` - New options

**Tests:**
- `tests/unit/test_contracts.py` - New tests for immediate caller, null default, context
- `tests/integration/test_permissions.py` - E2E permission tests

## Success Criteria

1. ✅ All five kernel actions route through contract checks (done, minor edit action gap)
2. Null contract default implemented and configurable
3. ✅ Dangling contract fallback implemented (done)
4. Context matches ADR-0019 specification
5. Immediate caller model implemented for nested invokes
6. Decision made on GenesisMemory hardcoded checks
7. All tests pass

## Notes

- **Phase 1 complete** - Audit found 4 significant gaps
- **Highest priority:** Immediate caller model and null contract default
- **GenesisMemory decision needed:** Ask user whether hardcoded checks are acceptable
- The "edit" action gap is low priority - could document "write implies edit" as acceptable

## Related

- ADR-0019: Unified Permission Architecture
- ADR-0017: Dangling Contracts Fail Open
- Plan #100: Contract System Overhaul (completed)
- Plan #146: Unified Artifact Intelligence (implements GenesisMemory)
