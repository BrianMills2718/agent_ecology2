# Gap 27: Successful Invocation Registry

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Event log tracks actions but not invoke success/failure by artifact.

**Target:** Track successful invocations per artifact for emergent reputation.

---

## Problem Statement

MCP interfaces are declarative, not verifiable. An artifact can claim to do "risk calculation" but actually do something else. Without tracking actual success/failure:

1. Agents can't discover which artifacts actually work
2. No reputation signal emerges from usage
3. Gaming interfaces is trivial (lie about capabilities)

Tracking what artifacts *actually succeed* creates reputation from usage patterns.

---

## Design

### Event Types

Emit from executor on every invoke:

```python
# On success
{
    "type": "INVOKE_SUCCESS",
    "artifact_id": "risk_calculator",
    "method": "calculate_risk",
    "invoker_id": "agent_alice",
    "tick": 1500,
    "execution_ms": 45
}

# On failure
{
    "type": "INVOKE_FAILURE",
    "artifact_id": "risk_calculator",
    "method": "calculate_risk",
    "invoker_id": "agent_alice",
    "tick": 1500,
    "error_code": "EXECUTION_ERROR",
    "error_message": "Division by zero"
}
```

### Query Patterns

Agents can use genesis_event_log to answer:

| Query | How |
|-------|-----|
| "Which artifacts handle 'calculate_risk'?" | Filter INVOKE_SUCCESS by method |
| "What's success rate for artifact X?" | Count SUCCESS vs FAILURE for artifact |
| "Who successfully invoked X?" | Filter INVOKE_SUCCESS by artifact_id |
| "Most reliable artifacts?" | Rank by success rate |

### Aggregation (Optional)

Add `invoke_stats` to artifact metadata via genesis_store:

```python
{
    "artifact_id": "risk_calculator",
    "invoke_count": 150,
    "success_count": 142,
    "failure_count": 8,
    "unique_invokers": 5,
    "last_invoked_tick": 1500
}
```

**Note:** Aggregation is optional Phase 2. Events alone enable reputation queries.

---

## Implementation Steps

### Phase 1: Event Emission

1. [ ] Update `executor.py` to emit `INVOKE_SUCCESS` event on successful invoke
2. [ ] Update `executor.py` to emit `INVOKE_FAILURE` event on failed invoke
3. [ ] Include method name, invoker_id, artifact_id, tick in events
4. [ ] Include execution time for SUCCESS, error details for FAILURE

### Phase 2: Query Support (Optional)

5. [ ] Add `query_invocations()` method to genesis_event_log
6. [ ] Support filtering by artifact_id, method, invoker_id, time range
7. [ ] Return aggregated stats (success_rate, invoke_count)

### Phase 3: Artifact Metadata (Optional)

8. [ ] Add `invoke_stats` field to artifact metadata
9. [ ] Update stats on each invoke (success/failure count)
10. [ ] Expose via genesis_store.get_artifact_info()

---

## Required Tests

| Test | Type | Purpose |
|------|------|---------|
| `test_invoke_success_emits_event` | Unit | Success emits INVOKE_SUCCESS |
| `test_invoke_failure_emits_event` | Unit | Failure emits INVOKE_FAILURE |
| `test_event_contains_method_name` | Unit | Events include method name |
| `test_event_contains_invoker_id` | Unit | Events include invoker_id |
| `test_event_contains_execution_time` | Unit | Success events include execution_ms |
| `test_event_contains_error_details` | Unit | Failure events include error info |

```python
# tests/unit/test_invocation_registry.py

def test_invoke_success_emits_event(world_with_executable):
    """Successful invoke emits INVOKE_SUCCESS event."""
    world = world_with_executable
    result = world.invoke_artifact("alice", "calculator", {"method": "add", "args": [1, 2]})
    assert result["success"]

    events = world.event_log.read_recent(1)
    assert events[0]["type"] == "INVOKE_SUCCESS"
    assert events[0]["artifact_id"] == "calculator"

def test_invoke_failure_emits_event(world_with_failing_artifact):
    """Failed invoke emits INVOKE_FAILURE event."""
    world = world_with_failing_artifact
    result = world.invoke_artifact("alice", "buggy_artifact", {"method": "crash"})
    assert not result["success"]

    events = world.event_log.read_recent(1)
    assert events[0]["type"] == "INVOKE_FAILURE"
    assert "error_code" in events[0]

def test_event_contains_method_name(world_with_executable):
    """Events include the method name."""
    world = world_with_executable
    world.invoke_artifact("alice", "calculator", {"method": "multiply", "args": [3, 4]})

    events = world.event_log.read_recent(1)
    assert events[0]["method"] == "multiply"

def test_event_contains_invoker_id(world_with_executable):
    """Events include who invoked the artifact."""
    world = world_with_executable
    world.invoke_artifact("bob", "calculator", {"method": "add", "args": [1, 2]})

    events = world.event_log.read_recent(1)
    assert events[0]["invoker_id"] == "bob"

def test_event_contains_execution_time(world_with_executable):
    """Success events include execution time."""
    world = world_with_executable
    world.invoke_artifact("alice", "calculator", {"method": "add", "args": [1, 2]})

    events = world.event_log.read_recent(1)
    assert "execution_ms" in events[0]
    assert events[0]["execution_ms"] >= 0
```

---

## E2E Verification

1. Start simulation with multiple agents
2. Agent A creates an executable artifact
3. Agent B invokes it successfully
4. Agent C invokes it with bad args (fails)
5. Verify event log contains both INVOKE_SUCCESS and INVOKE_FAILURE
6. Query event log to compute success rate for the artifact

---

## Verification

- [ ] `INVOKE_SUCCESS` events emitted on successful invoke
- [ ] `INVOKE_FAILURE` events emitted on failed invoke
- [ ] Events contain: artifact_id, method, invoker_id, tick
- [ ] Success events contain execution_ms
- [ ] Failure events contain error_code, error_message
- [ ] Unit tests pass
- [ ] `docs/architecture/current/supporting_systems.md` updated (event types)

---

## Notes

**Why reputation from usage:**
- JSON Schema interfaces can lie
- Actual success/failure is observable truth
- Agents discovering "this artifact works" is more valuable than "this artifact claims to work"

**Privacy consideration:** All invocations are logged. Artifacts cannot hide their usage patterns. This is intentional - observability over privacy for ecosystem health.

**Future extensions:**
- Weighted reputation (recent invocations matter more)
- Method-level stats (some methods may fail more)
- Invoker reputation (successful invokers may be better judges)

See GAPS.md archive (section 27) for original context.
