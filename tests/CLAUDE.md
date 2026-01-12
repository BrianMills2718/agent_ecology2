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
