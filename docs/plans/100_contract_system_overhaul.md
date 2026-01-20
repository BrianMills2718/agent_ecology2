# Plan 100: Contract System Overhaul

**Status:** 🚧 In Progress
**Priority:** High
**Blocked By:** None
**Blocks:** Custom contracts, advanced access control patterns

---

## Overview

Route ALL permission checks through contracts. Remove hardcoded owner bypass. Rename `owner_id` to `created_by` per ADR-0016.

**Approach:** Aggressive move to target architecture. No backwards compatibility. If tests break, fix them.

---

## Current State (Investigated 2026-01-20)

| Aspect | Status | Notes |
|--------|--------|-------|
| Genesis contracts (4 classes) | ✅ Exist | FreewareContract, PrivateContract, SelfOwnedContract, PublicContract |
| Permission caching | ✅ Implemented | `PermissionCache` class in contracts.py |
| Depth limit (10) | ✅ Implemented | `max_contract_depth` in config, enforced in executor |
| `access_contract_id` on Artifact | ❌ Missing | Only on AgentEntry helper, not Artifact dataclass |
| Owner bypass in `can_*()` | ❌ Exists | Lines 210, 219, 257 in artifacts.py |
| World.py uses contracts | ❌ No | Uses `artifact.can_read/write/invoke()` directly |
| `owner_id` → `created_by` | ❌ Not done | ADR-0016 accepted but not implemented |

**The Core Problem:**
```
Agent action → world.py → artifact.can_read() → owner bypass (no contracts!)
Artifact invokes artifact → executor.py → _check_permission() → uses contracts ✓
```

---

## Changes Required

### 1. Add `access_contract_id` to Artifact dataclass

```python
# src/world/artifacts.py
@dataclass
class Artifact:
    ...
    access_contract_id: str = "genesis_contract_freeware"  # Default from config
```

### 2. Rename `owner_id` → `created_by`

Per ADR-0016. Throughout codebase:
- `Artifact.owner_id` → `Artifact.created_by`
- All references in world.py, artifacts.py, executor.py, genesis files
- Update genesis contracts to use `context["created_by"]`

### 3. Delete `can_read()`, `can_write()`, `can_invoke()` from Artifact

These methods have hardcoded owner bypass. Delete them entirely.

### 4. World.py uses executor._check_permission()

Replace:
```python
# OLD (line 680)
if not artifact.can_read(intent.principal_id):

# NEW
allowed, reason = self.executor._check_permission(intent.principal_id, "read", artifact)
if not allowed:
```

Same for write (line 778) and invoke (line 892).

### 5. Update context dict in executor._check_permission_via_contract()

```python
# OLD (line 598)
context = {"owner": artifact.owner_id, ...}

# NEW
context = {"created_by": artifact.created_by, ...}
```

### 6. Add configurable default contract

```yaml
# config/schema.yaml
executor:
  default_access_contract: "genesis_contract_freeware"  # Configurable
```

---

## Files Affected

### Core Changes (permission routing)
| File | Changes |
|------|---------|
| `src/world/artifacts.py` | Add `access_contract_id`, rename `owner_id`→`created_by`, delete `can_*()` methods (32 refs) |
| `src/world/world.py` | Use `executor._check_permission()` instead of `artifact.can_*()` (13 refs) |
| `src/world/executor.py` | Ensure `_check_permission` is accessible, handle default contract (5 refs) |
| `src/world/genesis_contracts.py` | Update to use `created_by` in context |
| `src/world/kernel_interface.py` | Rename owner_id references (8 refs) |

### Genesis Artifacts
| File | Changes |
|------|---------|
| `src/world/genesis/store.py` | Rename owner_id (10 refs) |
| `src/world/genesis/ledger.py` | Rename owner_id (6 refs) |
| `src/world/genesis/base.py` | Rename owner_id (3 refs) |
| `src/world/genesis/escrow.py` | Rename owner_id (1 ref) |
| `src/world/genesis/types.py` | Rename owner_id (1 ref) |

### Agents
| File | Changes |
|------|---------|
| `src/agents/agent.py` | Rename owner_id (4 refs) |
| `src/agents/memory.py` | Rename owner_id (2 refs) |
| `src/agents/loader.py` | Rename owner_id (2 refs) |

### Dashboard
| File | Changes |
|------|---------|
| `src/dashboard/parser.py` | Rename owner_id (15 refs) |
| `src/dashboard/models.py` | Rename owner_id (3 refs) |
| `src/dashboard/server.py` | Rename owner_id (1 ref) |
| `src/dashboard/kpis.py` | Rename owner_id (1 ref) |

### Other
| File | Changes |
|------|---------|
| `src/simulation/runner.py` | Rename owner_id (3 refs) |
| `src/config_schema.py` | Add `default_access_contract` config (1 ref) |
| `config/schema.yaml` | Document new config |
| `tests/**` | Fix tests that rely on owner bypass |

---

## Required Tests

| Test | Description |
|------|-------------|
| `test_permission_via_contract` | Verify all permissions go through contracts |
| `test_no_owner_bypass` | Creator cannot bypass contract restrictions |
| `test_default_contract_configurable` | Default contract comes from config |
| `test_created_by_immutable` | `created_by` is set at creation, never changes |

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| No `can_read/write/invoke` methods | Grep returns 0 matches in Artifact class |
| All permissions via contracts | World.py calls `executor._check_permission()` |
| No `owner_id` in codebase | Grep returns 0 matches (except migrations/docs) |
| Default contract configurable | Config value used when `access_contract_id` missing |
| All tests pass | `make test` green |

---

## ADRs Applied

- ADR-0015: Contracts as Artifacts
- ADR-0016: `created_by` Replaces `owner_id`
- ADR-0017: Dangling Contracts Fail-Open (to default contract)
- ADR-0018: Bootstrap and Eris

---

## Deferred (Not This Plan)

- LLM access in contracts (`call_llm`)
- Contract composition
- Custom contract creation by agents
- Cost models beyond simple pricing

These are separate plans after the foundation is solid.
