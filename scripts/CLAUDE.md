# Scripts Directory

Utility scripts for development and CI.

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `check_doc_coupling.py` | Verify docs updated when source changes | `python scripts/check_doc_coupling.py` |
| `check_plan_tests.py` | Verify plan test requirements | `python scripts/check_plan_tests.py` |
| `check_claims.py` | Manage active work claims (YAML-backed) | `python scripts/check_claims.py` |
| `sync_plan_status.py` | Sync plan status across files | `python scripts/sync_plan_status.py` |
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
# 1. Doc-coupling on STAGED files (source + doc must be staged together)
# 2. Mypy on changed src/ files
# 3. Coupling config validity

# Bypass (not recommended)
git commit --no-verify
```

The hook uses `--staged` mode for doc-coupling, so commits that include both source changes AND their required doc updates will pass.

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

Claims are stored in `.claude/active-work.yaml` and synced to the CLAUDE.md table.
Branch name is used as instance identity by default.

```bash
# Check for stale claims (default >4 hours)
python scripts/check_claims.py

# List all active claims
python scripts/check_claims.py --list

# Claim work on a plan (checks dependencies first)
python scripts/check_claims.py --claim --plan 3 --task "Implement docker"

# Claim work (no plan)
python scripts/check_claims.py --claim --task "Fix bug in executor"

# Check plan dependencies without claiming
python scripts/check_claims.py --check-deps 7

# Force claim even if dependencies not met (not recommended)
python scripts/check_claims.py --claim --plan 7 --task "..." --force

# Release a claim (when done)
python scripts/check_claims.py --release

# Release with TDD validation (recommended for plan work)
python scripts/check_claims.py --release --validate

# Clean up old completed entries (>24h)
python scripts/check_claims.py --cleanup

# Sync YAML to CLAUDE.md table
python scripts/check_claims.py --sync
```

### Dependency Enforcement

When claiming a plan, the script checks if all blockers are complete:
- If dependencies not met, claim is blocked (use `--force` to override)
- Use `--check-deps N` to check dependencies without claiming

### TDD Enforcement

When releasing with `--validate`:
- Runs required tests for the plan
- Runs full test suite
- Blocks release if tests fail (use `--force` to override)

## Plan Status Sync

Ensures plan status is consistent across plan files and index.

```bash
# Check for inconsistencies
python scripts/sync_plan_status.py --check

# Sync index to match plan files
python scripts/sync_plan_status.py --sync

# List all plan statuses
python scripts/sync_plan_status.py --list
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
