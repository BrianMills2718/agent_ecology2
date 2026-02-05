# Integration Tests Directory

Tests for multiple components working together.

## Scope

Integration tests verify components integrate correctly:
- Multiple classes/modules together
- Real database operations (in-memory/temp)
- Real file I/O (temp directories)
- No external API calls (mock those)

## Key Test Files

| File | Tests |
|------|-------|
| `test_runner.py` | SimulationRunner orchestration |
| `test_invoke.py` | Contract invocation flow |
| `test_checkpoint.py` | State persistence/restore |
| `test_alpha_prime.py` | Artifact-based agent loops |

## Running

```bash
# All integration tests
pytest tests/integration/ -v

# Single file
pytest tests/integration/test_escrow.py -v
```

## Writing Integration Tests

1. Test realistic scenarios (not just happy path)
2. Use real components where possible
3. Mock external APIs only (LLM, external services)
4. Verify observable outcomes
5. Clean up temp resources

## vs Unit vs E2E

| Type | Components | External APIs | Speed |
|------|------------|---------------|-------|
| Unit | 1 | None | Very fast |
| Integration | 2-5 | Mocked | Fast |
| E2E | All | Real or mocked | Slow |
