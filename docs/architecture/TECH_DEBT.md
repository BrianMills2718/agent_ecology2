# Technical Debt & Architectural Improvements

Tracked architectural concerns and potential improvements. Items here are candidates for future plans.

**Last reviewed:** 2026-01-21

---

## Active Debt (Should Address)

### TD-001: World.py is too large (2000+ lines)

**Problem:** `src/world/world.py` has accumulated too many responsibilities:
- State management (ledger, artifacts)
- Mint auction logic (~300 lines)
- Resource quota management
- Event logging coordination
- Genesis artifact coordination

**Impact:** Hard to test in isolation, hard to understand, merge conflicts likely.

**Recommended fix:** Extract into focused components:
```
World (orchestrator)
├── MintAuction (auction logic) ← Start here
├── QuotaManager (resource enforcement)
└── Keep: ledger, artifacts, logger refs
```

**Effort:** Medium | **Risk:** Low (behavior-preserving refactor)

---

### TD-002: Circular coupling World ↔ RightsRegistry

**Problem:** Bidirectional reference creates tight coupling:
```python
# In World.__init__():
self.rights_registry = genesis_rights_registry
self.rights_registry.set_world(self)  # Circular!
```

World calls `rights_registry.can_write()`, registry calls `world.set_quota()`.

**Impact:**
- Unit testing requires full World instance
- Potential for infinite loops if permission checks invoke artifacts
- Unclear ownership of quota state

**Recommended fix:** World owns quota state directly, RightsRegistry becomes read-only facade:
```python
# World owns quotas
self._quotas: dict[str, dict[str, float]] = {}

# RightsRegistry gets read-only access
rights_registry = GenesisRightsRegistry(quota_reader=self.get_quota)
```

**Effort:** Medium | **Risk:** Medium (need to audit all quota paths)

---

### TD-003: Executor has mixed responsibilities

**Problem:** `src/world/executor.py` handles:
- Safe code execution (sandboxing, timeouts)
- Permission checking (contract evaluation)
- Genesis method dispatch
- Invocation depth tracking

**Impact:** Hard to test permission logic without execution, hard to change one without affecting others.

**Recommended fix:** Split into:
- `SafeExecutor` - Sandboxing, timeouts, code execution
- `PermissionChecker` - Contract permission evaluation
- `GenesisDispatcher` - Genesis method routing

**Effort:** Medium-High | **Risk:** Medium

---

### TD-005: Config flow is implicit

**Problem:** Components receive full config dict, extract what they need:
```python
def from_config(cls, config: dict[str, Any]) -> SimulationEngine:
    costs = config.get("costs", {})
    budget = config.get("budget", {})
    # ...
```

No clear contract about what each component needs.

**Impact:** Hard to know what config a component uses, easy to break with config changes.

**Recommended fix:** Explicit config dataclasses per component:
```python
@dataclass
class LedgerConfig:
    precision_decimals: int = 8

class Ledger:
    def __init__(self, config: LedgerConfig): ...
```

**Effort:** High | **Risk:** Low (additive change)

---

## Potential Improvements (Nice to Have)

### TD-006: No explicit Kernel interface

**Problem:** "Kernel" is a design concept in docs but not in code. `World` implements kernel primitives but there's no explicit interface.

**Recommended fix:** Create `Kernel` protocol that World implements:
```python
class Kernel(Protocol):
    def store(self, id: str, data: bytes) -> None: ...
    def load(self, id: str) -> bytes | None: ...
    def get_quota(self, principal: str, resource: str) -> float: ...
```

Makes the design doc match the code.

**Effort:** Low | **Risk:** Low

---

### TD-007: Missing `__all__` exports

**Problem:** Most world modules export everything implicitly. No clear public API.

**Impact:** IDE autocomplete includes internals, easy to depend on implementation details.

**Recommended fix:** Add explicit `__all__` lists to all modules.

**Effort:** Low | **Risk:** Very Low

---

### TD-008: Genesis artifact IDs are hardcoded

**Problem:** IDs like `"genesis_ledger"`, `"genesis_mint"` are string literals scattered throughout.

**Recommended fix:** Constants in one place:
```python
# src/world/genesis/ids.py
GENESIS_LEDGER = "genesis_ledger"
GENESIS_MINT = "genesis_mint"
```

**Effort:** Low | **Risk:** Very Low

---

### TD-009: Contract permission depth limit not enforced

**Problem:** Target docs mention depth limit for contract permission checks to prevent loops, but it's not implemented.

**Impact:** Circular contract references could cause infinite loops.

**Recommended fix:** Add configurable `MAX_PERMISSION_DEPTH` check in executor.

**Effort:** Low | **Risk:** Low

---

## Resolved

| ID | Description | Resolved In | Date |
|----|-------------|-------------|------|
| TD-004 | Inconsistent resource naming | Constants in `resources.py` (already existed), config/code fixed | 2026-01-31 |

---

## How to Use This File

1. **Adding debt:** Add new item with TD-NNN ID, describe problem/impact/fix
2. **Addressing debt:** Create a plan in `docs/plans/`, reference TD-NNN
3. **Resolving debt:** Move to Resolved table with plan reference

This file is for architectural concerns. For bugs, use GitHub issues.
