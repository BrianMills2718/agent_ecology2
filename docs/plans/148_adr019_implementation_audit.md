# Plan 148: ADR-0019 Implementation Audit

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** Full contract-based permission system

## Problem Statement

ADR-0019 (Unified Permission Architecture) documents the target permission system, but current implementation may not fully align. This plan audits the codebase against ADR-0019 and closes gaps.

## ADR-0019 Requirements

### 1. Five Kernel Actions - All Contract-Checked

| Action | Purpose | Contract-Checked? |
|--------|---------|-------------------|
| `read` | Read artifact content | ❓ Audit needed |
| `write` | Create/replace artifact | ❓ Audit needed |
| `edit` | Surgical content modification | ❓ Audit needed |
| `invoke` | Call method on artifact | ❓ Audit needed |
| `delete` | Remove artifact | ❓ Audit needed |

### 2. Immediate Caller Model

When A→B→C, C's contract should see B (not A) as caller.

- **Status:** ❓ Needs verification

### 3. Null Contract Default

When `access_contract_id` is null:
- Creator has full rights
- All others blocked
- Configurable via `contracts.default_when_null`

- **Status:** ❓ Needs verification
- **Config option:** Not in schema yet

### 4. Dangling Contract Fallback

When `access_contract_id` points to deleted contract:
- Fall back to configurable default (freeware)
- Log warning
- Configurable via `contracts.default_on_missing`

- **Status:** ❓ Needs verification (ADR-0017 accepted, but implementation?)
- **Config option:** Not in schema yet

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

- **Status:** ❌ Current implementation passes more (artifact_type, caller_type)

### 6. Freeware Kernel Optimization

Kernel MAY skip contract call for `genesis_freeware_contract`.

- **Status:** ❓ Needs verification

### 7. Genesis Not Privileged

Genesis contracts should use same code path as user contracts.

- **Status:** Partial (Plan #100 done, but genesis artifacts like GenesisMemory use hardcoded checks)

## Implementation Tasks

### Phase 1: Audit

- [ ] Audit `src/world/executor.py` - which actions check contracts?
- [ ] Audit `src/world/contracts.py` - what context is passed?
- [ ] Audit `src/world/artifacts.py` - null/dangling contract handling?
- [ ] Audit `src/world/genesis/*.py` - hardcoded permission checks?
- [ ] Document gaps in this plan

### Phase 2: Config Schema

- [ ] Add `contracts.default_when_null` to `config/schema.yaml`
- [ ] Add `contracts.default_on_missing` to `config/schema.yaml`
- [ ] Update `src/config_schema.py` with new options

### Phase 3: Null Contract Default

- [ ] Implement null contract → creator-only behavior in executor
- [ ] Add tests for null contract default
- [ ] Verify configurable via config

### Phase 4: Context Minimization

- [ ] Remove extra context keys from contract calls (or make optional)
- [ ] Ensure only ADR-0019 specified keys are required
- [ ] Update tests

### Phase 5: Genesis Alignment

- [ ] Refactor GenesisMemory to use contracts (or document why hardcoded is acceptable)
- [ ] Audit other genesis artifacts for hardcoded checks
- [ ] Ensure genesis uses same permission path as user artifacts

### Phase 6: Verification

- [ ] All five actions contract-checked (or documented exceptions)
- [ ] Immediate caller model verified
- [ ] Null/dangling behavior matches ADR-0019
- [ ] Context matches ADR-0019 spec

## Files Affected

- `src/world/executor.py` - permission checking
- `src/world/contracts.py` - contract execution
- `src/world/artifacts.py` - artifact storage
- `src/world/genesis/memory.py` - hardcoded checks
- `src/world/genesis/embedder.py` - check for hardcoded checks
- `config/schema.yaml` - new config options
- `src/config_schema.py` - config validation
- `tests/unit/test_contracts.py` - new tests
- `tests/integration/test_permissions.py` - new tests

## Success Criteria

1. All five kernel actions route through contract checks (or documented exceptions)
2. Null contract default implemented and configurable
3. Dangling contract fallback implemented and configurable
4. Context matches ADR-0019 specification
5. No undocumented hardcoded permission checks in genesis artifacts
6. All tests pass

## Notes

- Phase 1 (Audit) should be done first to understand actual gaps
- Some hardcoded checks may be acceptable if functionally equivalent to contract behavior
- Balance purity vs pragmatism per project heuristics

## Related

- ADR-0019: Unified Permission Architecture
- ADR-0017: Dangling Contracts Fail Open
- Plan #100: Contract System Overhaul (completed)
- Plan #146: Unified Artifact Intelligence (uses hardcoded checks)
