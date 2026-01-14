# Gap 27: Successful Invocation Registry

**Status:** ✅ Complete

**Verified:** 2026-01-14T02:25:57Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-14T02:25:57Z
tests:
  unit: 1147 passed, 1 skipped in 13.79s
  e2e_smoke: PASSED (2.04s)
  doc_coupling: passed
commit: 0d8892a
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** No tracking of invoke success/failure

**Target:** Track invocations for emergent reputation

---

## Problem Statement

When agents invoke artifacts (contracts, services), outcomes are not systematically tracked. This prevents:

1. **Emergent reputation** - No way to know which artifacts are reliable
2. **Risk assessment** - Can't evaluate if an artifact is safe to invoke
3. **Market signals** - No data on artifact usage patterns
4. **Debugging** - Hard to trace why an invocation failed

The goal is observability, not enforcement. We track invocations so that reputation can emerge from observable behavior.

---

## Plan

### Phase 1: Invocation Events

Add structured events for each artifact invocation:

**Event: INVOKE_ATTEMPT**
```python
{
    "event_type": "invoke_attempt",
    "tick": 42,
    "invoker_id": "agent_alice",
    "artifact_id": "contract_foo",
    "method": "execute",
    "args_count": 3,
    "timestamp": "2026-01-13T10:30:00.000Z"
}
```

**Event: INVOKE_SUCCESS**
```python
{
    "event_type": "invoke_success",
    "tick": 42,
    "invoker_id": "agent_alice",
    "artifact_id": "contract_foo",
    "method": "execute",
    "duration_ms": 15,
    "result_type": "dict",  # Type of return value
    "timestamp": "2026-01-13T10:30:00.015Z"
}
```

**Event: INVOKE_FAILURE**
```python
{
    "event_type": "invoke_failure",
    "tick": 42,
    "invoker_id": "agent_alice",
    "artifact_id": "contract_foo",
    "method": "execute",
    "error_type": "timeout",  # validation, permission, execution, etc.
    "error_message": "Code execution timed out",
    "duration_ms": 5000,
    "timestamp": "2026-01-13T10:30:05.000Z"
}
```

### Phase 2: Invocation Registry

Add a queryable registry of invocation history:

```python
# src/world/invocation_registry.py

@dataclass
class InvocationRecord:
    """Record of a single invocation."""
    tick: int
    invoker_id: str
    artifact_id: str
    method: str
    success: bool
    duration_ms: float
    error_type: str | None = None
    timestamp: str = ""

class InvocationRegistry:
    """Tracks invocation history for observability."""

    def record_invocation(self, record: InvocationRecord) -> None:
        """Add an invocation record."""
        ...

    def get_artifact_stats(self, artifact_id: str) -> dict:
        """Get success/failure stats for an artifact."""
        return {
            "total_invocations": 100,
            "successful": 95,
            "failed": 5,
            "success_rate": 0.95,
            "avg_duration_ms": 12.5,
            "failure_types": {"timeout": 3, "validation": 2}
        }

    def get_invoker_history(self, invoker_id: str, limit: int = 100) -> list[InvocationRecord]:
        """Get recent invocations by an invoker."""
        ...
```

### Phase 3: Dashboard Integration

Add dashboard endpoint for invocation stats:

```python
@app.get("/api/artifacts/{artifact_id}/invocations")
async def get_artifact_invocations(artifact_id: str) -> dict:
    """Get invocation statistics for an artifact."""
    return registry.get_artifact_stats(artifact_id)

@app.get("/api/invocations")
async def get_recent_invocations(
    artifact_id: str | None = None,
    invoker_id: str | None = None,
    success: bool | None = None,
    limit: int = 100
) -> list[dict]:
    """Get filtered invocation history."""
    ...
```

### Implementation Steps

1. **Create `src/world/invocation_registry.py`** - InvocationRecord, InvocationRegistry
2. **Add events to executor** - Emit INVOKE_* events on artifact invocation
3. **Integrate registry with World** - Track invocations globally
4. **Add dashboard endpoints** - `/api/artifacts/{id}/invocations`, `/api/invocations`
5. **Update parser** - Parse new event types
6. **Add tests** - Unit and integration tests

---

## Required Tests

### Unit Tests
- `tests/unit/test_invocation_registry.py::test_record_invocation` - Records stored correctly
- `tests/unit/test_invocation_registry.py::test_get_artifact_stats` - Stats calculated correctly
- `tests/unit/test_invocation_registry.py::test_success_rate_calculation` - Rate math correct
- `tests/unit/test_invocation_registry.py::test_filter_by_invoker` - Filtering works
- `tests/unit/test_invocation_registry.py::test_failure_type_counts` - Error categorization

### Integration Tests
- `tests/integration/test_invocation_events.py::test_invoke_success_event` - Event emitted on success
- `tests/integration/test_invocation_events.py::test_invoke_failure_event` - Event emitted on failure
- `tests/integration/test_invocation_events.py::test_dashboard_invocation_api` - API returns stats

---

## E2E Verification

Run simulation and verify invocation tracking:

```bash
python run.py --ticks 10 --agents 2 --dashboard
# Check http://localhost:8080/api/invocations
# Verify invocations are tracked with success/failure
grep "invoke_success\|invoke_failure" run.jsonl | head -5
```

---

## Out of Scope

- **Reputation scoring** - Just track data, let agents compute reputation
- **Blacklisting** - No automatic blocking of artifacts
- **Rate limiting based on failures** - Not changing invocation policy
- **Historical persistence** - In-memory for now

---

## Verification

- [ ] Tests pass
- [ ] Docs updated
- [ ] Implementation matches target

---

## Notes

This provides the data for emergent reputation without prescribing how reputation should work.

Key design decisions:
- **Observability only** - We track, not enforce
- **In-memory registry** - Events persist to log, registry is per-session
- **No reputation algorithm** - Agents decide what stats matter to them
- **Compatible with existing executor** - Wraps existing invocation flow

See also:
- `src/world/executor.py` - Current invocation logic
- `src/world/contracts.py` - Contract execution
- `docs/DESIGN_CLARIFICATIONS.md` - Reputation emergence discussion
