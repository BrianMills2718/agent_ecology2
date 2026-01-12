# Scripts Directory

Utility scripts for development and CI.

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `check_doc_coupling.py` | Verify docs updated when source changes | `python scripts/check_doc_coupling.py` |
| `check_plan_tests.py` | Verify plan test requirements | `python scripts/check_plan_tests.py` |
| `check_claims.py` | Detect stale claims in Active Work table | `python scripts/check_claims.py` |
| `validate_plan_completion.py` | Validate plan completion criteria | `python scripts/validate_plan_completion.py` |
| `plan_progress.py` | Show plan implementation progress | `python scripts/plan_progress.py` |
| `doc_coupling.yaml` | Source-to-doc mappings | Config file, not executable |
| `view_log.py` | Parse and view run.jsonl events | `python scripts/view_log.py` |
| `concat_for_review.py` | Concatenate files for external review | `python scripts/concat_for_review.py` |
| `setup_hooks.sh` | Install git pre-commit hook | `bash scripts/setup_hooks.sh` |

## Git Hooks

Pre-commit hook catches issues before they reach CI:

```bash
# Install (run once after cloning)
bash scripts/setup_hooks.sh

# What it checks:
# 1. Doc-coupling violations (strict)
# 2. Mypy on changed src/ files
# 3. Coupling config validity

# Bypass (not recommended)
git commit --no-verify
```

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

## Claim Management

```bash
# Check for stale claims (default >4 hours)
python scripts/check_claims.py

# List all active claims
python scripts/check_claims.py --list

# Clear a stale claim
python scripts/check_claims.py --clear CC-5
```

## Plan Progress

```bash
# Summary of all plans (one line each)
python scripts/plan_progress.py --summary

# Detailed progress for one plan
python scripts/plan_progress.py --plan 1

# All plans detailed
python scripts/plan_progress.py --all
```

## Plan Completion Validation

```bash
# Validate plan is ready for completion
python scripts/validate_plan_completion.py --plan 1

# Check all plans marked as complete
python scripts/validate_plan_completion.py --check-complete
```
