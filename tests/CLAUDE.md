# Tests Directory

pytest test suite. All tests must pass before committing.

## Running Tests

```bash
# All tests
pytest tests/ -v

# Single file
pytest tests/test_ledger.py -v

# Single test
pytest tests/test_ledger.py::TestTransfer::test_basic_transfer -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## Test Organization

| File | Tests |
|------|-------|
| `test_ledger.py` | Resource tracking, scrip transfers |
| `test_executor.py` | Code execution, safety, invoke() |
| `test_escrow.py` | Trustless trading, atomic operations |
| `test_oracle_auction.py` | Bidding, resolution, minting |
| `test_checkpoint.py` | Save/load round-trip |
| `test_runner.py` | Tick loop, phase execution |
| `test_invoke.py` | Recursive invocation, depth limits |
| `test_async_agent.py` | Parallel agent thinking |
| `test_memory.py` | Mem0 integration |
| `test_policy.py` | Access control policies |
| `test_agent_loop.py` | Autonomous agent loops |
| `test_testing_utils.py` | VirtualClock, wait_for helpers |
| `testing_utils.py` | Testing utilities (not a test file) |

## Test Conventions

1. **Use fixtures** from `conftest.py` for common setup
2. **Test edge cases** - empty inputs, max values, error conditions
3. **No external dependencies** - Tests use mocks for LLM calls
4. **Fast execution** - Full suite runs in ~5-10 seconds

## Adding New Tests

When adding new functionality:
1. Add tests FIRST (TDD preferred)
2. Cover happy path AND error cases
3. Use descriptive test names: `test_transfer_fails_with_insufficient_balance`

## CI Integration

GitHub Actions runs `pytest tests/ -v --tb=short` on every PR.

## Plan Test Integration

Plans in `docs/plans/` can define required tests in their `## Required Tests` section. Use:

```bash
# See what tests a plan needs
python scripts/check_plan_tests.py --plan 1 --tdd

# Run all required tests for a plan
python scripts/check_plan_tests.py --plan 1
```

When implementing a plan:
1. Define tests in plan's `## Required Tests` section
2. Write test stubs here (TDD - they fail initially)
3. Implement feature
4. Tests pass, plan complete

## Testing Utilities for Continuous Execution

For testing async/continuous code, use utilities from `tests/testing_utils.py`:

### VirtualClock - Deterministic Time Control

```python
from tests.testing_utils import VirtualClock
from src.world.rate_tracker import RateTracker

def test_rate_limit_expires():
    clock = VirtualClock()  # Starts at t=0
    tracker = RateTracker(window_seconds=60.0, clock=clock)
    tracker.configure_limit("llm_calls", 100.0)

    tracker.consume("agent", "llm_calls", 100.0)
    assert tracker.get_remaining("agent", "llm_calls") == 0.0

    clock.advance(61.0)  # Instant, no real delay
    assert tracker.get_remaining("agent", "llm_calls") == 100.0
```

### wait_for / wait_for_value - Condition-Based Assertions

```python
from tests.testing_utils import wait_for, wait_for_value

@pytest.mark.asyncio
async def test_loop_starts():
    loop = AgentLoop(...)
    await loop.start()

    # Instead of: await asyncio.sleep(0.05)
    await wait_for_value(lambda: loop.state, AgentState.RUNNING)
```

### When to Use What

| Pattern | Use Case |
|---------|----------|
| `VirtualClock` | Testing time-dependent logic (rate limiting, expiry, timeouts) |
| `wait_for()` | Waiting for async conditions without fixed sleeps |
| `wait_for_value()` | Waiting for specific value |
| `wait_for_predicate()` | Waiting with custom predicate |
| Real `asyncio.sleep()` | Only when testing actual timing behavior |

### Clock Injection

Components that depend on time accept an optional `clock` parameter:

```python
# Production (or default)
tracker = RateTracker(window_seconds=60.0)  # Uses real time

# Testing
clock = VirtualClock()
tracker = RateTracker(window_seconds=60.0, clock=clock)
```

See `tests/test_testing_utils.py` for more examples.
