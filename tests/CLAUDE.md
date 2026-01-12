# Tests Directory

pytest test suite organized by test type.

## Structure

```
tests/
├── unit/           # Single component, no external deps (19 files, ~500 tests)
├── integration/    # Multiple components together (12 files, ~400 tests)
└── e2e/            # Full system tests (2 files)
    ├── test_smoke.py      # Mocked LLM (fast, CI)
    └── test_real_e2e.py   # Real LLM (slow, $$$, --run-external)
```

## Running Tests

```bash
# All tests (fast, CI default)
pytest tests/ -v

# By type
pytest tests/unit/ -v              # Unit tests only
pytest tests/integration/ -v       # Integration tests only
pytest tests/e2e/test_smoke.py -v  # E2E with mocked LLM

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

## When to Use Each

- **Unit**: Testing logic in isolation (ledger math, policy checks)
- **Integration**: Testing components work together (executor + ledger + artifacts)
- **E2E smoke**: CI - verify simulation runs without crashing
- **E2E real**: Pre-release - verify real LLM integration works

## Key Files

| Directory | Key Files |
|-----------|-----------|
| `unit/` | test_ledger.py, test_executor.py, test_contracts.py, test_agent_loop.py |
| `integration/` | test_runner.py, test_escrow.py, test_invoke.py, test_genesis_store.py |
| `e2e/` | test_smoke.py (mocked), test_real_e2e.py (real LLM) |

## Test Conventions

1. **Use fixtures** from `conftest.py` for common setup
2. **Real tests preferred** - Avoid mocks; accept time/cost of real calls (see root CLAUDE.md #5)
3. **Fast execution** - Unit + integration suite runs in ~15 seconds

## Adding Tests

When adding functionality:
1. Add unit tests for new logic
2. Add integration test if multiple components involved
3. Add E2E test if new user-facing feature
4. Real E2E test required before marking feature complete

## CI Integration

GitHub Actions runs `pytest tests/ -v --tb=short` on every PR (excludes real E2E).

For releases: `pytest tests/ -v --run-external` (includes real E2E).
