# Tests Directory

pytest test suite organized by test type with marker-based feature/plan associations.

## Structure

```
tests/
├── conftest.py              # Global fixtures + markers
├── unit/                    # Single component, no external deps
├── integration/             # Multiple components together
│   ├── test_*_acceptance.py # Feature acceptance tests (AC-mapped)
│   └── test_*.py            # Component integration tests
└── e2e/                     # Full system tests
    ├── test_smoke.py        # Mocked LLM (fast, CI)
    └── test_real_e2e.py     # Real LLM (slow, $$$, --run-external)
```

## Running Tests

```bash
# All tests (fast, CI default)
pytest tests/ -v

# By type
pytest tests/unit/ -v              # Unit tests only
pytest tests/integration/ -v       # Integration tests only
pytest tests/e2e/test_smoke.py -v  # E2E with mocked LLM

# By feature (uses pytest marker)
pytest --feature escrow tests/     # All tests for escrow feature
pytest --feature rate_limiting tests/

# By plan number (uses pytest marker)
pytest --plan 6 tests/             # All tests for Plan #6

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
| **Acceptance** | Feature AC from acceptance_gates/*.yaml | Medium | Depends on feature |
| **E2E (smoke)** | Full simulation, mocked LLM | Fast | LLM mocked |
| **E2E (real)** | Full simulation, real LLM | Slow | None |

## Markers

### Feature Marker

Tests map to features via explicit markers (not directory structure):

```python
import pytest

@pytest.mark.feature("escrow")  # Maps to acceptance_gates/escrow.yaml
class TestEscrowFeature:
    def test_ac_1_successful_artifact_sale(self):
        """AC-1: Successful artifact sale via escrow."""
        ...
```

Run tests for a specific feature:
```bash
pytest --feature escrow tests/
```

### Plan Marker

Tests can also associate with implementation plans:

```python
@pytest.mark.plans([1, 11])  # Tests relevant to Plans #1 and #11
class TestRateLimiting:
    ...
```

Run tests for a specific plan:
```bash
pytest --plan 6 tests/
```

## Acceptance Tests

Feature acceptance tests live in `tests/integration/test_*_acceptance.py`:

| File | Feature | Maps To |
|------|---------|---------|
| `test_escrow_acceptance.py` | escrow | acceptance_gates/escrow.yaml |
| `test_rate_limiting_acceptance.py` | rate_limiting | acceptance_gates/rate_limiting.yaml |
| `test_agent_loop_acceptance.py` | agent_loop | acceptance_gates/agent_loop.yaml |

**Naming convention:** Test functions map to acceptance criteria:
- `test_ac_1_*` → AC-1 from feature spec
- `test_ac_2_*` → AC-2 from feature spec

## When to Use Each

- **Unit**: Testing logic in isolation (ledger math, policy checks)
- **Integration**: Testing components work together (executor + ledger + artifacts)
- **Acceptance**: Verify feature acceptance criteria from acceptance_gates/*.yaml
- **E2E smoke**: CI - verify simulation runs without crashing
- **E2E real**: Pre-release - verify real LLM integration works

## Key Files

| Directory | Key Files |
|-----------|-----------|
| `unit/` | test_ledger.py, test_executor.py, test_contracts.py, test_agent_loop.py |
| `integration/` | test_escrow.py, test_*_acceptance.py, test_invoke.py |
| `e2e/` | test_smoke.py (mocked), test_real_e2e.py (real LLM) |

## Test Conventions

1. **Use fixtures** from `conftest.py` for common setup
2. **Real tests preferred** - Avoid mocks; accept time/cost of real calls
3. **Fast execution** - Unit + integration suite runs in ~15 seconds
4. **Mark with feature** - Use `@pytest.mark.feature("X")` for feature association
5. **Mark with plans** - Use `@pytest.mark.plans(N)` for plan association
6. **Justify mocks** - If mocking internal code, add `# mock-ok: <reason>`

## Adding Tests

When adding functionality:
1. Add unit tests for new logic
2. Add integration test if multiple components involved
3. For new features, create `test_*_acceptance.py` with `@pytest.mark.feature("X")`
4. Mark tests with appropriate markers
5. Real E2E test required before marking plan complete

## TDD Workflow

See `docs/meta/03_testing-strategy.md` for full TDD workflow.

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

See `docs/meta/05_mocking-policy.md` for full policy.

**Summary:**
- No mocks by default
- Mock external APIs when needed for speed/cost
- Require `# mock-ok: <reason>` for justified mocks
- CI fails on suspicious patterns without justification
