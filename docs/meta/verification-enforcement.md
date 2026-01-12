# Pattern: Verification Enforcement

## Problem

Without mandatory verification:
- Plans get marked "complete" without running tests
- Integration failures accumulate undetected
- "Big bang" testing reveals many issues at once
- No evidence that verification actually happened
- AI assistants may claim completion without proof

## Solution

Require a verification script to mark plans as complete. The script:
1. Runs required tests (unit + E2E smoke)
2. Checks doc-code coupling
3. Records evidence in the plan file
4. Updates status only if all checks pass

**Key principle:** The status update is gated by actual test runs, not promises.

## Files

| File | Purpose |
|------|---------|
| `scripts/complete_plan.py` | Enforcement script |
| `tests/e2e/test_smoke.py` | Basic E2E verification |
| `tests/e2e/conftest.py` | Mocked LLM fixtures |
| `docs/plans/NN_*.md` | Plan files with evidence |

## Setup

1. Create the E2E test directory:
```bash
mkdir -p tests/e2e
```

2. Copy or create the verification script:
```bash
# scripts/complete_plan.py
# See implementation in this project
```

3. Create E2E smoke tests that verify basic functionality:
```python
# tests/e2e/test_smoke.py
def test_basic_functionality(mock_llm):
    """Verify core system works end-to-end."""
    # Your basic smoke test here
    pass
```

4. Update CLAUDE.md to require the script:
```markdown
### Plan Completion (MANDATORY)

> **Never manually set a plan status to Complete.**
> Always use: `python scripts/complete_plan.py --plan N`
```

## Usage

### Completing a plan

```bash
# Standard completion
python scripts/complete_plan.py --plan 35

# Dry run (check without updating)
python scripts/complete_plan.py --plan 35 --dry-run

# Skip E2E for documentation-only plans
python scripts/complete_plan.py --plan 35 --skip-e2e
```

### What the script does

1. **Unit tests** - Runs `pytest tests/ --ignore=tests/e2e/`
2. **E2E smoke** - Runs `pytest tests/e2e/test_smoke.py`
3. **Doc coupling** - Runs `python scripts/check_doc_coupling.py --strict`
4. **Evidence** - Records results in plan file
5. **Status** - Updates to "Complete" only if all pass

### Evidence format

After completion, plan files include:

```markdown
**Status:** ✅ Complete
**Verified:** 2026-01-12T10:30:00Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-12T10:30:00Z
tests:
  unit: 145/145 passed
  e2e_smoke: PASSED (8.2s)
  doc_coupling: passed
commit: a9ba628
```
```

## Customization

### Adding more verification steps

Edit `complete_plan.py` to add checks:

```python
def run_custom_check(project_root: Path) -> tuple[bool, str]:
    """Add your custom verification."""
    result = subprocess.run(["your-command"], ...)
    return result.returncode == 0, "summary"
```

### Plan-specific tests

Plans can define required tests in their `## Required Tests` section. The `check_plan_tests.py` script validates these.

### Skipping E2E for specific plan types

For documentation-only or process plans:
```bash
python scripts/complete_plan.py --plan N --skip-e2e
```

## Limitations

- **Not a substitute for thorough testing** - Smoke tests catch crashes, not subtle bugs
- **Requires test infrastructure** - You need working tests first
- **Can be bypassed** - Determined users can edit files manually (git history shows this)
- **Doesn't verify correctness** - Only verifies that tests pass, not that implementation is right

## Integration with Other Patterns

| Pattern | Integration |
|---------|-------------|
| Plan Workflow | Verification is the final step |
| Claim System | Release claim only after verification |
| Git Hooks | Could add pre-commit check for unverified completions |
| Doc-Code Coupling | Verification includes coupling check |

## Origin

Emerged from agent_ecology after multiple "complete" plans were found to have failing tests. The cost of late integration testing exceeded the overhead of mandatory verification.
