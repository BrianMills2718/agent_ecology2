# Plan #42: Kernel Quota Primitives

**Status:** 🚧 In Progress

**Priority:** High
**Blocked By:** None
**Blocks:** Plan #1 (Rate Allocation - proper enforcement)

---

## Problem

Quotas currently live in `GenesisRightsRegistry` (a genesis artifact), but they should be **kernel state**. This creates several issues:

1. **Architectural inconsistency**: Quotas are "physics" (what agents CAN do), not social convention
2. **No enforcement**: Kernel doesn't enforce quotas—they're advisory only
3. **Privileged genesis**: GenesisRightsRegistry appears privileged when it shouldn't be
4. **Integration gap**: RateTracker exists but isn't wired into kernel action execution

### Current State

| Component | Status | Issue |
|-----------|--------|-------|
| `GenesisRightsRegistry` | Exists | Stores quotas as artifact state (wrong) |
| `RateTracker` | Exists | Not wired into kernel |
| `KernelState` | Exists | No quota query methods |
| `KernelActions` | Exists | No quota mutation methods |
| Quota enforcement | Missing | Kernel doesn't check quotas before actions |

### Target State

| Component | Target |
|-----------|--------|
| Kernel metadata | Tracks quotas per principal |
| `KernelState` | `get_quota()`, `get_available_capacity()` |
| `KernelActions` | `transfer_quota()`, enforces limits |
| `GenesisRightsRegistry` | Thin wrapper around kernel primitives |
| Quota enforcement | Kernel checks before action execution |

---

## Solution

### Phase 1: Kernel Quota State

Add quota tracking to kernel metadata:

```python
# In kernel state (per principal)
quotas: dict[str, float] = {
    "cpu_seconds_per_minute": 10.0,
    "llm_tokens_per_minute": 1000,
    "disk_bytes": 1_000_000,
    "memory_bytes": 100_000_000,
}
```

### Phase 2: KernelState Methods

```python
class KernelState:
    def get_quota(self, principal_id: str, resource: str) -> float:
        """Get assigned quota for resource."""
        ...

    def get_available_capacity(self, principal_id: str, resource: str) -> float:
        """Get remaining capacity considering rolling window usage."""
        ...

    def would_exceed_quota(self, principal_id: str, resource: str, amount: float) -> bool:
        """Check if action would exceed quota."""
        ...
```

### Phase 3: KernelActions Methods

```python
class KernelActions:
    def transfer_quota(self, from_id: str, to_id: str,
                       resource: str, amount: float) -> bool:
        """Atomically transfer quota between principals."""
        ...

    def consume_quota(self, principal_id: str, resource: str, amount: float) -> bool:
        """Record quota usage (for rate limiting)."""
        ...
```

### Phase 4: Enforcement Integration

Wire quota checks into action execution:

```python
def _execute_action(self, intent: ActionIntent) -> ActionResult:
    # Check quota BEFORE executing
    if not self._check_quota(intent.principal_id, intent.resource_type, intent.estimated_cost):
        return ActionResult(
            success=False,
            error_code="QUOTA_EXCEEDED",
            error_category="resource",
            retriable=True,
        )
    # Execute action...
```

### Phase 5: GenesisRightsRegistry as Wrapper

Refactor GenesisRightsRegistry to delegate to kernel:

```python
class GenesisRightsRegistry(GenesisArtifact):
    def get_quota(self, principal_id: str, resource: str) -> float:
        # Delegate to kernel
        return self.kernel_state.get_quota(principal_id, resource)

    def transfer_quota(self, from_id: str, to_id: str,
                       resource: str, amount: float) -> MethodResult:
        # Delegate to kernel
        success = self.kernel_actions.transfer_quota(from_id, to_id, resource, amount)
        return MethodResult(success=success, ...)
```

---

## Required Tests

### Unit Tests
- [ ] `test_kernel_quota_state` - Quota stored in kernel metadata
- [ ] `test_kernel_get_quota` - KernelState.get_quota works
- [ ] `test_kernel_get_available_capacity` - Rolling window calculation
- [ ] `test_kernel_transfer_quota` - Atomic quota transfer
- [ ] `test_quota_would_exceed` - Pre-check before action

### Integration Tests
- [ ] `test_action_quota_enforcement` - Actions blocked when quota exceeded
- [ ] `test_quota_retriable_error` - QUOTA_EXCEEDED returns retriable=True
- [ ] `test_genesis_rights_delegates_to_kernel` - GenesisRightsRegistry is thin wrapper
- [ ] `test_quota_trading` - Agents can trade quotas via kernel primitives

### E2E Tests
- [ ] `test_rate_limited_agent` - Agent with low quota executes fewer actions
- [ ] `test_quota_transfer_enables_execution` - Transfer quota, action succeeds

---

## Acceptance Criteria

1. Quotas stored in kernel metadata, not GenesisRightsRegistry artifact state
2. KernelState provides quota query methods
3. KernelActions provides quota mutation methods
4. Kernel enforces quotas before action execution
5. GenesisRightsRegistry is a thin wrapper (not privileged)
6. RateTracker integrated with kernel quota state
7. All tests pass

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/world/kernel_interface.py` | Add quota methods to KernelState/KernelActions |
| `src/world/world.py` | Store quotas in kernel state, enforce in action execution |
| `src/world/genesis.py` | Refactor GenesisRightsRegistry to delegate to kernel |
| `src/world/rate_tracker.py` | Wire into kernel state |
| `docs/architecture/target/08_kernel.md` | Document quota primitives |
| `docs/architecture/current/resources.md` | Update after implementation |

---

## Verification

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Docs updated

---

## Notes

This plan implements the architectural principle that **quotas are kernel physics**, not genesis artifact convention. Agents could build alternative quota interfaces, but the kernel is the source of truth.
