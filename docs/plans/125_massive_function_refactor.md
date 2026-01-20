# Plan #125: Massive Function Refactor

**Status:** 📋 Planned
**Priority:** **Medium**
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Several functions exceed 200 lines, making them hard to test, understand, and maintain:

| Function | File | Lines | Issues |
|----------|------|-------|--------|
| `execute_with_invoke()` | `executor.py:1053` | 339 | 3 nested invoke() definitions |
| `_execute_invoke()` | `world.py:852` | 341 | Permission + execution intertwined |
| `create_app()` | `dashboard/server.py:166` | 706 | All routes in one function |
| `build_prompt()` | `agent.py:591` | 229 | Multiple prompt assembly phases |
| `get_temporal_network_data()` | `parser.py:1097` | 206 | Data transformation chains |

**Target:** Break these into smaller, focused functions with single responsibilities.

**Why Medium:** Technical debt that slows development but doesn't cause immediate failures.

---

## References Reviewed

- `src/world/executor.py:1053-1392` - execute_with_invoke
- `src/world/world.py:852-1193` - _execute_invoke
- `src/dashboard/server.py:166-872` - create_app
- `src/agents/agent.py:591-820` - build_prompt
- `src/dashboard/parser.py:1097-1303` - get_temporal_network_data

---

## Files Affected

- src/world/executor.py (modify)
- src/world/world.py (modify)
- src/dashboard/server.py (modify)
- src/agents/agent.py (modify)
- src/dashboard/parser.py (modify)

---

## Plan

### Phase 1: `_execute_invoke()` in world.py (Highest Value)

Extract into:
```python
def _validate_invoke_permission(self, caller: str, artifact: Artifact, method: str) -> None:
    """Check if caller has permission to invoke method."""

def _check_invoke_affordability(self, caller: str, cost: int) -> bool:
    """Check if caller can afford the compute cost."""

def _execute_genesis_method(self, artifact: GenesisArtifact, method: str, args: list) -> Any:
    """Execute a genesis artifact method."""

def _execute_user_artifact(self, artifact: Artifact, method: str, args: list) -> Any:
    """Execute a user-defined artifact method."""
```

### Phase 2: `create_app()` in server.py

Extract route handlers into separate functions:
```python
def _register_api_routes(app: Flask, ...) -> None:
    """Register /api/* routes."""

def _register_static_routes(app: Flask, ...) -> None:
    """Register static file serving."""

def _register_websocket_handlers(app: Flask, ...) -> None:
    """Register WebSocket event handlers."""
```

### Phase 3: Other functions (lower priority)

- `execute_with_invoke()` - Extract nested invoke definitions
- `build_prompt()` - Extract prompt section builders
- `get_temporal_network_data()` - Extract data transformation steps

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_world.py` | `test_validate_invoke_permission_*` | Permission checks work in isolation |
| `tests/unit/test_world.py` | `test_check_invoke_affordability_*` | Cost checking works in isolation |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_world.py` | World behavior unchanged |
| `tests/unit/test_executor.py` | Executor behavior unchanged |
| `tests/integration/test_invoke.py` | End-to-end invoke unchanged |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Invoke still works | Run simulation with artifact invocations | Same behavior as before |

---

## Verification

### Tests & Quality
- [ ] All tests pass: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] No behavior changes (refactor only)

### Documentation
- [ ] No doc changes needed (internal refactor)

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`

---

## Notes
This is a pure refactoring plan - no behavioral changes. The goal is improved testability and maintainability. Each phase can be done independently.

Risk mitigation: Ensure comprehensive test coverage exists BEFORE refactoring. Run tests after each extraction.
