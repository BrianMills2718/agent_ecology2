# E2E Tests Directory

End-to-end tests that run the full simulation.

## Files

| File | Purpose | LLM |
|------|---------|-----|
| `test_smoke.py` | Basic simulation run | Mocked |
| `test_real_e2e.py` | Full simulation with real LLM | Real |

## Running

```bash
# Smoke tests (fast, runs in CI)
pytest tests/e2e/test_smoke.py -v

# Real E2E (requires --run-external, costs money)
pytest tests/e2e/test_real_e2e.py -v --run-external
```

## When to Use

- **Smoke tests**: CI, quick validation, development
- **Real E2E**: Pre-release validation, debugging LLM issues

## Writing E2E Tests

E2E tests should:
1. Set up a complete simulation environment
2. Run for a small number of ticks (1-3)
3. Verify observable outcomes (not internals)
4. Clean up resources after

Use fixtures from `conftest.py` for setup.

## Plan-Specific E2E

Feature-specific E2E tests go in `tests/plans/plan_NN/`, not here.
This directory is for general simulation validation.
