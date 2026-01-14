# Unit Tests Directory

Tests for individual components in isolation.

## Scope

Unit tests verify single classes/functions work correctly:
- No external dependencies
- No database/file I/O
- No network calls
- Fast execution (< 100ms each)

## Key Test Files

| File | Tests |
|------|-------|
| `test_ledger.py` | Balance tracking, transfers |
| `test_executor.py` | Action execution, validation |
| `test_contracts.py` | Contract artifact behavior |
| `test_agent_loop.py` | Agent decision loop |
| `test_rate_tracker.py` | Rate limiting logic |
| `test_models.py` | Pydantic model validation |

## Running

```bash
# All unit tests
pytest tests/unit/ -v

# Single file
pytest tests/unit/test_ledger.py -v

# Single test
pytest tests/unit/test_ledger.py::TestTransfer::test_basic -v
```

## Writing Unit Tests

1. One test file per source file (`test_<module>.py`)
2. Test class per logical group (`class TestTransfer`)
3. Clear test names (`test_transfer_fails_with_insufficient_balance`)
4. Use fixtures from `conftest.py`
5. No mocks of internal code (see mocking policy)

## Fixtures

Common fixtures in `tests/conftest.py`:
- `world` - Initialized World instance
- `ledger` - Ledger with test balances
- `agent_context` - Agent execution context
