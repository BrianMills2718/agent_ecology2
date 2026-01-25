# Scripts Directory

Utility scripts for development and CI. All scripts support `--help` for options.

## Script Summary

### Core Workflow Scripts

| Script | Purpose |
|--------|---------|
| `meta_status.py` | **Dashboard**: claims, PRs, progress, issues |
| `check_claims.py` | Manage active work claims (scope-based) |
| `finish_pr.py` | Complete PR lifecycle: merge + cleanup + release claim |
| `merge_pr.py` | Merge PRs via GitHub CLI |
| `complete_plan.py` | Mark plan complete (runs tests, records evidence) |
| `safe_worktree_remove.py` | Safely remove worktrees (checks for uncommitted changes) |

### Plan Management

| Script | Purpose |
|--------|---------|
| `check_plan_tests.py` | Verify/run plan test requirements |
| `check_plan_blockers.py` | Detect stale blockers (blocked by complete plans) |
| `check_plan_exclusivity.py` | Enforce unique plan numbers across open PRs |
| `check_plan_overlap.py` | Detect overlapping plan implementations |
| `check_plan_completion.py` | Verify plan completion requirements |
| `validate_plan.py` | Pre-implementation validation gate |
| `validate_plan_completion.py` | Validate plan completion evidence |
| `parse_plan.py` | Parse plan file structure |
| `plan_progress.py` | Show plan implementation progress |
| `sync_plan_status.py` | Sync plan status + validate content consistency |

### Documentation & Quality

| Script | Purpose |
|--------|---------|
| `check_doc_coupling.py` | Verify docs updated when source changes |
| `check_adr_requirement.py` | Check if ADR is required for changes |
| `sync_governance.py` | Sync ADR governance headers |
| `check_mock_usage.py` | Detect suspicious mock patterns in tests |
| `check_mock_tests.py` | Detect mock usage in test files |
| `check_feature_coverage.py` | Verify all src files assigned to features |
| `check_locked_files.py` | Protect locked acceptance criteria |
| `check_new_code_tests.py` | Verify new code has test coverage |
| `validate_spec.py` | Validate feature spec YAML format |
| `validate_code_map.py` | Validate code mapping files |

### Inter-CC Messaging

| Script | Purpose |
|--------|---------|
| `check_messages.py` | Check inbox for CC messages (`--list`, `--ack`, `--archive`) |
| `send_message.py` | Send message to another CC instance |
| `session_manager.py` | Manage CC session identity |

### Cleanup & Analysis

| Script | Purpose |
|--------|---------|
| `cleanup_branches.py` | Delete stale remote branches (merged PRs) |
| `cleanup_orphaned_worktrees.py` | Find/clean orphaned worktrees (merged PRs) |
| `analyze_run.py` | Analyze simulation run results |
| `view_log.py` | Parse run.jsonl events |
| `concat_for_review.py` | Concatenate files for review |

### Setup

| Script | Purpose |
|--------|---------|
| `setup_hooks.sh` | Install git hooks |

Config: `relationships.yaml` (unified doc graph; legacy: `doc_coupling.yaml`, `governance.yaml`)

## Git Hooks

```bash
bash scripts/setup_hooks.sh   # Install (once after clone)
git commit --no-verify        # Bypass (not recommended)
```

- **pre-commit**: Doc-coupling + mypy on staged files
- **commit-msg**: Requires `[Plan #N]` prefix (all work needs a plan)

## Common Commands

```bash
# Doc coupling
python scripts/check_doc_coupling.py --suggest     # What docs to update
python scripts/check_doc_coupling.py --strict      # CI mode

# Plan status sync (index ↔ file ↔ content)
python scripts/sync_plan_status.py --check         # CI mode (validates all)
python scripts/sync_plan_status.py --fix-content   # Fix Needs Plan → Planned
python scripts/sync_plan_status.py --sync          # Sync index to match files
python scripts/sync_plan_status.py --list          # Show all statuses

# Plan blockers
python scripts/check_plan_blockers.py              # Report stale blockers
python scripts/check_plan_blockers.py --strict     # CI mode (fails if stale)
python scripts/check_plan_blockers.py --apply      # Fix stale blockers

# Governance sync
python scripts/sync_governance.py --check          # CI mode
python scripts/sync_governance.py --apply          # Apply changes

# Plan validation
python scripts/validate_plan.py --plan N           # Pre-impl gate

# Plan tests (TDD)
python scripts/check_plan_tests.py --plan N --tdd  # What to write
python scripts/check_plan_tests.py --plan N        # Run tests
pytest --plan N tests/                             # Run tests for plan N

# Plan completion
python scripts/complete_plan.py --plan N           # Complete with verification
python scripts/complete_plan.py --plan N --dry-run # Check without updating
python scripts/complete_plan.py --plan N --skip-real-e2e  # Skip real LLM E2E tests
python scripts/complete_plan.py --plan N --human-verified  # For plans with human review

# Mock usage
python scripts/check_mock_usage.py                 # Report mocks
python scripts/check_mock_usage.py --strict        # CI mode (fails on suspicious)

# Claims (scope-based)
python scripts/check_claims.py --list              # See active claims
python scripts/check_claims.py --list-features     # See available features
python scripts/check_claims.py --claim --plan N --task "X"     # Claim plan
python scripts/check_claims.py --claim --feature NAME --task "X"  # Claim feature
python scripts/check_claims.py --release --validate # Done + verify

# Merge PRs
python scripts/merge_pr.py 123           # Merge PR #123
python scripts/merge_pr.py 123 --dry-run # Check without merging
# Or via make:
make merge PR=123                        # Preferred way to merge
# Note: Branch protection ensures CI passes before merge

# Branch cleanup (stale branches from merged PRs)
python scripts/cleanup_branches.py           # List stale branches
python scripts/cleanup_branches.py --delete  # Delete stale branches
python scripts/cleanup_branches.py --all     # Include abandoned PRs too
# Run periodically to keep branch count low

# Worktree cleanup (orphaned worktrees from merged PRs)
python scripts/cleanup_orphaned_worktrees.py         # Report orphaned worktrees
python scripts/cleanup_orphaned_worktrees.py --auto  # Auto-cleanup (safe only)
python scripts/cleanup_orphaned_worktrees.py --force # Force cleanup (loses uncommitted!)
# Or via make:
make clean-worktrees                         # Report orphans
make clean-worktrees-auto                    # Auto-cleanup
```

## Configuration

Edit `relationships.yaml` to add doc relationships:
- `governance`: ADR → source file mappings
- `couplings`: source → doc mappings (for CI enforcement)
