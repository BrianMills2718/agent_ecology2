# Pattern: Testing Strategy

## Philosophy

**Thin slices over big bang.** Every feature must prove it works end-to-end before declaring success. Unit tests passing with integration failing is a false positive.

**TDD as default.** Tests defined before implementation starts. Escape hatches exist for exploratory work.

**Real over mocked.** Prefer real dependencies. Mock only external APIs or when explicitly justified.

## The Thin Slice Principle

### Problem

Without mandatory E2E verification:
- All unit tests pass
- All integration tests pass
- Real system doesn't work
- Issues accumulate until a painful "big bang" integration

### Solution

Every feature (plan) must:
1. Define E2E acceptance criteria
2. Have at least one E2E test that exercises the feature
3. Pass E2E before marking Complete

```
Feature -> E2E Test -> Verified
         (not)
Feature -> Unit Tests Only -> "Complete" -> Broken in production
```

## Test Organization

### Recommended Structure

```
tests/
├── conftest.py              # Global fixtures
├── unit/                    # Single-component tests
│   └── test_ledger.py       # Can be marked with @pytest.mark.plans([1, 11])
├── integration/             # Multi-component tests
│   └── test_escrow.py       # Can be marked with @pytest.mark.plans([6])
├── e2e/                     # Full system tests
│   ├── test_smoke.py        # Generic smoke (mocked LLM)
│   └── test_real_e2e.py     # Real LLM ($$$)
└── plans/                   # Feature-specific E2E tests (NEW)
    ├── conftest.py          # Plan-specific fixtures
    ├── plan_01/
    │   └── test_rate_limiting_e2e.py
    ├── plan_06/
    │   └── test_unified_ontology_e2e.py
    └── ...
```

### Why Hybrid Structure?

| Approach | Pros | Cons |
|----------|------|------|
| Type-first (`unit/`, `integration/`) | Shared fixtures, pytest conventions | Hard to find tests for a plan |
| Plan-first (`plan_01/`, `plan_02/`) | Clear feature mapping | Duplication, deep nesting |
| **Hybrid** (both) | Best of both | Slightly more complex |

The hybrid approach:
- Keeps shared unit/integration tests in their traditional locations
- Adds `tests/plans/` for feature-specific E2E tests
- Uses pytest markers for queryability

### Pytest Markers

Register custom markers in `conftest.py`:

```python
# tests/conftest.py
import pytest

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "plans(nums): mark test as belonging to plan number(s)"
    )
    config.addinivalue_line(
        "markers", "feature_type: mark test as 'feature' or 'enabler'"
    )
```

Use in tests:

```python
# tests/integration/test_escrow.py
import pytest

@pytest.mark.plans([6, 22])
class TestEscrowIntegration:
    """Tests for escrow system (Plans #6, #22)."""
    pass
```

Query with:
```bash
# Run all tests for plan 6
pytest -m "plans and 6" tests/

# Or use the check script
python scripts/check_plan_tests.py --plan 6
```

## TDD Policy

### Default: Tests Before Implementation

1. **Define tests** in plan's `## Required Tests` section
2. **Create test stubs** (they will fail)
3. **Implement** until tests pass
4. **Add E2E test** in `tests/plans/plan_NN/`
5. **Verify with script** before marking complete

### Escape Hatch 1: Exploratory Work

For plans that require exploration before test definition:

1. Start implementation without tests
2. **Before completion**, define and implement tests
3. Document why TDD was skipped in the plan

```markdown
## Notes

TDD skipped: Required exploration to understand the API surface.
Tests added post-implementation: test_foo.py, test_bar.py
```

### Escape Hatch 2: Enabler Plans

Enabler plans (tooling, process, documentation) may not have feature E2E tests:

```bash
# Use --skip-e2e for enabler plans
python scripts/complete_plan.py --plan 32 --skip-e2e
```

Mark in plan:
```markdown
**Type:** Enabler (no feature E2E required)
```

## Plan Types

| Type | Definition | E2E Required? | Example |
|------|------------|---------------|---------|
| **Feature** | Delivers user-visible capability | Yes | Rate limiting, Escrow |
| **Enabler** | Improves dev process | No (validation script instead) | Dev tooling, ADR governance |
| **Refactor** | Changes internals, not behavior | Existing E2E must pass | Terminology cleanup |

## Enforcement Mechanisms

### 1. CI Gates Plan Tests

```yaml
# .github/workflows/ci.yml
plan-tests:
  runs-on: ubuntu-latest
  # NO continue-on-error - this is strict
  steps:
    - run: python scripts/check_plan_tests.py --all
```

### 2. Completion Script Requires Tests

```bash
# This runs E2E tests before allowing completion
python scripts/complete_plan.py --plan N
```

The script:
1. Runs unit tests
2. Runs E2E smoke tests
3. Checks doc-coupling
4. Records evidence in plan file
5. Only then updates status to Complete

### 3. Plan Test Definition Validation

The `check_plan_tests.py` script validates:
- Plans with status "In Progress" or "Complete" have tests defined
- Defined tests exist in the test files
- Defined tests pass

### 4. Pre-Merge Checklist

Before merging a plan PR:

```bash
# All must pass
pytest tests/ -v
python scripts/check_plan_tests.py --plan N
python scripts/complete_plan.py --plan N --dry-run
```

## Writing Good E2E Tests

### Feature E2E Test Template

```python
# tests/plans/plan_NN/test_feature_e2e.py
"""E2E test for Plan #NN: Feature Name.

This test verifies that [feature] works end-to-end with [real/mocked] LLM.
"""

import pytest
from src.simulation.runner import SimulationRunner

class TestFeatureE2E:
    """End-to-end tests for [feature]."""

    def test_feature_basic_flow(self, e2e_config):
        """Verify [feature] works in a real simulation."""
        # Arrange
        runner = SimulationRunner(e2e_config)

        # Act
        world = runner.run_sync()

        # Assert - feature-specific assertions
        assert [feature-specific condition]

    @pytest.mark.external
    def test_feature_with_real_llm(self, real_e2e_config):
        """Verify [feature] with real LLM (costs $$$)."""
        # Only runs with --run-external
        ...
```

### What Makes a Good E2E Test

| Good | Bad |
|------|-----|
| Tests user-visible behavior | Tests internal implementation |
| Minimal mocking | Mocks everything |
| Specific assertions | "Doesn't crash" only |
| Documents the feature | Cryptic test names |
| Fast (< 30s for mocked) | Slow (minutes) |

## Mocking Policy

See [mocking-policy.md](./mocking-policy.md) for details.

**Summary:**
- No mocks by default
- Mock external APIs (LLM, network) when needed for speed/cost
- Require `# mock-ok: <reason>` comment for justified mocks
- CI fails on suspicious mock patterns without justification

## Metrics

Track testing health with:

```bash
# Plan test coverage
python scripts/check_plan_tests.py --list

# Mock usage
python scripts/check_mock_usage.py

# Overall coverage (if using coverage.py)
pytest --cov=src tests/
```

## Migration from Big Bang

If your codebase has accumulated untested "complete" plans:

1. **Audit**: Run `python scripts/plan_progress.py --summary`
2. **Identify gaps**: Plans marked Complete with 0% test progress
3. **Prioritize**: Focus on high-priority plans first
4. **Add tests retroactively**: Create `tests/plans/plan_NN/` for each
5. **Update verification**: Run `complete_plan.py` to record evidence

## Origin

Adopted after discovering multiple "Complete" plans had never been E2E tested. The cost of late integration (debugging across multiple accumulated changes) exceeded the overhead of per-feature E2E verification.
