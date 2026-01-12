# Scripts Directory

Utility scripts for development and CI.

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `check_doc_coupling.py` | Verify docs updated when source changes | `python scripts/check_doc_coupling.py` |
| `check_plan_tests.py` | Verify plan test requirements | `python scripts/check_plan_tests.py` |
| `doc_coupling.yaml` | Source-to-doc mappings | Config file, not executable |
| `view_log.py` | Parse and view run.jsonl events | `python scripts/view_log.py` |
| `concat_for_review.py` | Concatenate files for external review | `python scripts/concat_for_review.py` |

## Doc Coupling Commands

```bash
# Check for violations (used in CI)
python scripts/check_doc_coupling.py --strict

# See what docs you should update
python scripts/check_doc_coupling.py --suggest

# Validate config file paths exist
python scripts/check_doc_coupling.py --validate-config
```

## Doc Coupling Types

Configured in `doc_coupling.yaml`:

| Type | Behavior |
|------|----------|
| **Strict** | CI fails if source changes without doc update |
| **Soft** (`soft: true`) | CI warns but doesn't fail |

## Adding New Couplings

Edit `doc_coupling.yaml`:

```yaml
couplings:
  - sources:
      - "src/new_module.py"
    docs:
      - "docs/architecture/current/new_module.md"
    description: "New module documentation"
    # soft: true  # Uncomment for warning-only
```

Then validate:
```bash
python scripts/check_doc_coupling.py --validate-config
```

## Plan Test Commands

```bash
# List all plans and test counts
python scripts/check_plan_tests.py --list

# TDD mode - see what tests to write for a plan
python scripts/check_plan_tests.py --plan 1 --tdd

# Run all required tests for a plan
python scripts/check_plan_tests.py --plan 1

# Check all plans with test requirements
python scripts/check_plan_tests.py --all
```

## TDD Workflow

1. **Define tests** - Add `## Required Tests` section to plan (see `docs/plans/CLAUDE.md`)
2. **Write tests** - Create test stubs in `tests/` (they will fail)
3. **Check status** - `python scripts/check_plan_tests.py --plan N --tdd`
4. **Implement** - Code until tests pass
5. **Verify** - `python scripts/check_plan_tests.py --plan N`
