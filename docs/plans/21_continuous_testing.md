# Gap 21: Testing for Continuous Execution

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None (Plan #2 Complete)
**Blocks:** None

---

## Gap

**Current:** Tests for continuous execution exist but use real `asyncio.sleep()` which is slow and non-deterministic. No unified testing utilities for time control.

**Target:** Testing strategy with deterministic time control and reusable utilities for continuous/async agent testing.

---

## Design

### Problem Analysis

Current tests in `test_agent_loop.py` use patterns like:
```python
await agent_loop.start()
await asyncio.sleep(0.05)  # Wait for things to happen
assert loop.state == AgentState.RUNNING
```

Issues:
1. **Slow** - Real sleeps add up (0.05s × many tests = slow suite)
2. **Flaky** - Timing-dependent, fails under system load
3. **Non-deterministic** - Hard to test precise timing scenarios

### Solution: VirtualClock + wait_for Helpers

#### VirtualClock

A mock clock that can be advanced programmatically:

```python
@dataclass
class VirtualClock:
    """Deterministic time control for tests."""
    _time: float = 0.0
    _waiters: list[tuple[float, asyncio.Event]] = field(default_factory=list)

    def time(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        """Advance time, waking any waiters whose time has come."""
        self._time += seconds
        self._wake_expired_waiters()

    async def sleep(self, seconds: float) -> None:
        """Async sleep that responds to advance()."""
        wake_time = self._time + seconds
        event = asyncio.Event()
        self._waiters.append((wake_time, event))
        await event.wait()
```

Usage in tests:
```python
async def test_rate_tracker_window(self):
    clock = VirtualClock()
    tracker = RateTracker(window_seconds=60.0, clock=clock)

    tracker.consume("agent", "llm_calls", 50.0)
    assert tracker.get_remaining("agent", "llm_calls") == 50.0

    clock.advance(61.0)  # Instant, not real time

    assert tracker.get_remaining("agent", "llm_calls") == 100.0
```

#### wait_for Helpers

Condition-based assertions with timeout:

```python
async def wait_for(
    condition: Callable[[], bool],
    timeout: float = 1.0,
    interval: float = 0.01,
) -> None:
    """Wait until condition is True or timeout."""
    start = time.time()
    while not condition():
        if time.time() - start > timeout:
            raise TimeoutError(f"Condition not met within {timeout}s")
        await asyncio.sleep(interval)

async def wait_for_value(
    getter: Callable[[], T],
    expected: T,
    timeout: float = 1.0,
) -> None:
    """Wait until getter() returns expected value."""
    await wait_for(lambda: getter() == expected, timeout)
```

Usage:
```python
async def test_agent_loop_starts(self):
    loop = AgentLoop(...)
    await loop.start()

    # Instead of: await asyncio.sleep(0.05)
    await wait_for_value(lambda: loop.state, AgentState.RUNNING)
```

### Integration Points

1. **RateTracker** - Already has `_get_current_time()` method, add optional clock injection
2. **AgentLoop** - Add clock parameter for time-based wake conditions
3. **Tests** - Create `tests/testing_utils.py` with shared utilities

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `tests/testing_utils.py` | NEW: VirtualClock, RealClock, wait_for, wait_for_value |
| `src/world/rate_tracker.py` | Add optional `clock` parameter |
| `tests/test_testing_utils.py` | NEW: Tests for testing utilities |
| `tests/test_agent_loop.py` | Optionally migrate to wait_for (not required) |

### Implementation Steps

#### Step 1: Create Testing Utilities

Create `tests/testing_utils.py` with:
1. `ClockProtocol` - Protocol for clock implementations
2. `VirtualClock` - Deterministic mock clock
3. `RealClock` - Wrapper around real time (for interface compatibility)
4. `wait_for()` - Wait for condition with timeout
5. `wait_for_value()` - Wait for specific value

#### Step 2: Add Clock Injection to RateTracker

Modify `RateTracker` to accept optional clock:
```python
@dataclass
class RateTracker:
    window_seconds: float = 60.0
    clock: ClockProtocol | None = None  # NEW

    def _get_current_time(self) -> float:
        if self.clock:
            return self.clock.time()
        return time.time()
```

#### Step 3: Create Tests for Testing Utilities

Write comprehensive tests proving the utilities work correctly:
- VirtualClock advances deterministically
- Waiters wake at correct times
- wait_for handles timeout correctly
- RateTracker works with VirtualClock

#### Step 4: Document Testing Patterns

Add documentation in `tests/CLAUDE.md` describing:
- When to use VirtualClock vs real time
- Common patterns for async testing
- How to test rate-limited behavior

---

## Required Tests

### New Tests (TDD)

Create these tests FIRST, before implementing:

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_testing_utils.py` | `test_virtual_clock_initial_time` | Clock starts at 0 |
| `tests/test_testing_utils.py` | `test_virtual_clock_advance` | advance() increases time |
| `tests/test_testing_utils.py` | `test_virtual_clock_sleep_wakes_on_advance` | Sleeper wakes when time passes |
| `tests/test_testing_utils.py` | `test_virtual_clock_multiple_sleepers` | Multiple sleepers wake correctly |
| `tests/test_testing_utils.py` | `test_wait_for_immediate_true` | Returns immediately if condition true |
| `tests/test_testing_utils.py` | `test_wait_for_becomes_true` | Waits until condition becomes true |
| `tests/test_testing_utils.py` | `test_wait_for_timeout` | Raises TimeoutError on timeout |
| `tests/test_testing_utils.py` | `test_wait_for_value_matches` | Waits for specific value |
| `tests/test_testing_utils.py` | `test_rate_tracker_with_virtual_clock` | RateTracker uses injected clock |
| `tests/test_testing_utils.py` | `test_rate_tracker_window_expiry_virtual` | Window expires with clock.advance() |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/test_agent_loop.py` | Existing behavior unchanged |
| `tests/test_rate_tracker.py` | Rate tracker still works without clock |

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 21`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `tests/CLAUDE.md` updated with testing patterns section
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

### Why Not Migrate All Existing Tests

The existing tests in `test_agent_loop.py` work correctly. While they could be faster with VirtualClock, migrating them is optional:
- Risk of introducing bugs in working tests
- Time investment for marginal benefit
- New tests should use new patterns

### Alternative Considered: pytest-freezegun

We considered using `freezegun` but rejected it because:
- It doesn't handle async well
- We need fine-grained control over time advancement
- VirtualClock is simpler and more transparent

### RealClock for Interface Compatibility

When code needs a clock but doesn't need mocking:
```python
clock = RealClock()  # Just wraps time.time() and asyncio.sleep()
tracker = RateTracker(clock=clock)  # Same interface, real time
```

This ensures the clock parameter can always be provided, making the API consistent.
