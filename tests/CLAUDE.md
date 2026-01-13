# Tests Directory

pytest test suite organized by test type with plan-specific E2E tests.

## Structure

```
tests/
├── conftest.py         # Global fixtures + plan markers
├── unit/               # Single component, no external deps
├── integration/        # Multiple components together
├── e2e/                # Full system tests
│   ├── test_smoke.py   # Mocked LLM (fast, CI)
│   └── test_real_e2e.py  # Real LLM (slow, $$$, --run-external)
└── plans/              # Feature-specific E2E tests (organized by plan)
    ├── conftest.py     # Plan-specific fixtures
    ├── plan_01/        # Plan #1: Rate Limiting
    ├── plan_06/        # Plan #6: Unified Ontology
    └── ...
```

## Running Tests

```bash
# All tests (fast, CI default)
pytest tests/ -v

# By type
pytest tests/unit/ -v              # Unit tests only
pytest tests/integration/ -v       # Integration tests only
pytest tests/e2e/test_smoke.py -v  # E2E with mocked LLM

# By plan number (uses pytest marker)
pytest --plan 6 tests/             # All tests for Plan #6

# Plan-specific E2E
pytest tests/plans/plan_06/ -v     # E2E tests for Plan #6

# Real E2E (actual LLM calls, costs ~$0.01-0.05)
pytest tests/e2e/test_real_e2e.py -v --run-external

# Single test
pytest tests/unit/test_ledger.py::TestTransfer::test_basic_transfer -v
```

## Test Types

| Type | Purpose | Speed | Mocks |
|------|---------|-------|-------|
| **Unit** | Single class/function in isolation | Fast | None ideally |
| **Integration** | Multiple components together | Medium | External APIs only |
| **E2E (smoke)** | Full simulation, mocked LLM | Fast | LLM mocked |
| **E2E (real)** | Full simulation, real LLM | Slow | None |
| **Plan E2E** | Feature-specific E2E | Medium | Depends on feature |

## Plan Markers

Tests can be marked to associate with specific plans:

```python
import pytest

@pytest.mark.plans([1, 11])  # Tests relevant to Plans #1 and #11
class TestRateLimiting:
    ...

@pytest.mark.plans(6)  # Single plan
def test_artifact_backed_agent():
    ...
```

Run tests for a specific plan:
```bash
pytest --plan 6 tests/
```

## When to Use Each

- **Unit**: Testing logic in isolation (ledger math, policy checks)
- **Integration**: Testing components work together (executor + ledger + artifacts)
- **E2E smoke**: CI - verify simulation runs without crashing
- **E2E real**: Pre-release - verify real LLM integration works
- **Plan E2E**: Feature acceptance - verify specific feature works

## Key Files

| Directory | Key Files |
|-----------|-----------|
| `unit/` | test_ledger.py, test_executor.py, test_contracts.py, test_agent_loop.py |
| `integration/` | test_runner.py, test_escrow.py, test_invoke.py, test_genesis_store.py |
| `e2e/` | test_smoke.py (mocked), test_real_e2e.py (real LLM) |
| `plans/` | Feature-specific E2E organized by plan number |

## Test Conventions

1. **Use fixtures** from `conftest.py` for common setup
2. **Real tests preferred** - Avoid mocks; accept time/cost of real calls (see `docs/meta/mocking-policy.md`)
3. **Fast execution** - Unit + integration suite runs in ~15 seconds
4. **Mark with plans** - Use `@pytest.mark.plans(N)` for plan association
5. **Justify mocks** - If mocking internal code, add `# mock-ok: <reason>`

## Adding Tests

When adding functionality:
1. Add unit tests for new logic
2. Add integration test if multiple components involved
3. Add E2E test in `tests/plans/plan_NN/` for the feature
4. Mark tests with `@pytest.mark.plans(N)`
5. Real E2E test required before marking plan complete

## TDD Workflow

See `docs/meta/testing-strategy.md` for full TDD workflow.

1. Define tests in plan's `## Required Tests` section
2. Create test stubs (they will fail)
3. Implement until tests pass
4. Verify with `python scripts/check_plan_tests.py --plan N`
5. Complete with `python scripts/complete_plan.py --plan N`

## CI Integration

GitHub Actions runs `pytest tests/ -v --tb=short` on every PR:
- Unit + integration tests run
- E2E smoke tests run (mocked LLM)
- Real E2E skipped (no `--run-external`)
- Plan tests validated (`check_plan_tests.py --all`)

For releases: `pytest tests/ -v --run-external` (includes real E2E).

## Mocking Policy

See `docs/meta/mocking-policy.md` for full policy.

**Summary:**
- No mocks by default
- Mock external APIs when needed for speed/cost
- Require `# mock-ok: <reason>` for justified mocks
- CI fails on suspicious patterns without justification
