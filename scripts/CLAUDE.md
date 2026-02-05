# Scripts Directory

Utility scripts for development and CI. All scripts support `--help` for options.

## Script Summary

### Core Workflow Scripts

| Script | Purpose |
|--------|---------|
| `meta_status.py` | **Dashboard**: claims, PRs, progress, issues |
| `check_claims.py` | Manage active work claims (scope-based) |
| `create_worktree.sh` | Create worktree with mandatory claiming (interactive or --branch/--task) |
| `finish_pr.py` | Complete PR lifecycle: merge + cleanup + release claim |
| `merge_pr.py` | Merge PRs via GitHub CLI |
| `complete_plan.py` | Mark plan complete (runs tests, records evidence) |
| `safe_worktree_remove.py` | Safely remove worktrees (checks for uncommitted changes) |

### Plan Management

| Script | Purpose |
|--------|---------|
| `check_plan_tests.py` | Verify/run plan test requirements |
| `check_plan_blockers.py` | Detect stale blockers (blocked by complete plans) |
| `check_plan_diff.py` | Compare plan declarations against actual git diff |
| `check_plan_exclusivity.py` | Enforce unique plan numbers across open PRs |
| `check_plan_overlap.py` | Detect overlapping plan implementations |
| `check_plan_completion.py` | Verify plan completion requirements |
| `validate_plan.py` | Pre-implementation validation gate |
| `validate_plan_completion.py` | Validate plan completion evidence |
| `parse_plan.py` | Parse plan file structure |
| `plan_progress.py` | Show plan implementation progress |
| `sync_plan_status.py` | Sync plan status + validate content consistency |
| `generate_plan_index.py` | Auto-generate docs/plans/CLAUDE.md index from plan files |

### Documentation & Quality

| Script | Purpose |
|--------|---------|
| `extract_relevant_context.py` | Extract GLOSSARY, ONTOLOGY, ADR, PRD, and domain model context for a file (Plan #288, #289, #294) |
| `check_file_context.py` | Check files have PRD/domain model context links (Plan #294) |
| `audit_governance_mappings.py` | Audit governance mappings for completeness (Plan #289) |
| `build_doc_index.py` | Build searchable index of docs for semantic search (Plan #289) |
| `semantic_doc_search.py` | BM25 semantic search over documentation (Plan #289) |
| `check_governance_completeness.py` | CI check for governance mapping coverage (Plan #289) |
| `check_doc_coupling.py` | Verify docs updated when source changes |
| `check_adr_requirement.py` | Check if ADR is required for changes |
| `check_planning_patterns.py` | Validate planning patterns (Open Questions, uncertainties, claims) |
| `sync_governance.py` | Sync ADR governance headers |
| `check_mock_usage.py` | Detect suspicious mock patterns in tests |
| `check_mock_tests.py` | Detect mock usage in test files |
| `check_claude_md.py` | Validate CLAUDE.md existence, coverage, and phantom refs |
| `check_feature_coverage.py` | Verify all src files assigned to features |
| `check_locked_files.py` | Protect locked acceptance criteria |
| `check_new_code_tests.py` | Verify new code has test coverage |
| `validate_spec.py` | Validate feature spec YAML format |
| `validate_code_map.py` | Validate code mapping files |
| `get_governance_context.py` | Get doc graph context for a file (ADRs + coupled docs) |
| `visualize_doc_graph.py` | Visualize documentation graph (text, DOT, PNG/SVG) |
| `generate_doc_graph_html.py` | Generate interactive HTML visualization (D3.js) |

### Meta-Process Configuration (Plan #218-220)

| Script | Purpose |
|--------|---------|
| `meta_process_config.py` | Check/configure meta-process weight level |
| `meta_config.py` | Read meta-process configuration (used by hooks/scripts) |
| `symbol_extractor.py` | Extract symbols from Python files (AST-based) |
| `bootstrap_meta_process.py` | Bootstrap meta-process for existing repos |
| `export_meta_process.py` | Export meta-process to standalone template repository |

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
| `cleanup_claims_mess.py` | One-time cleanup of stale/duplicate claims |
| `recover.py` | Auto-recover from meta-process issues (orphaned worktrees, stale claims, etc.) |
| `analyze_logs.py` | Analyze simulation logs (journeys, collaboration, loops) |
| `analyze_run.py` | Analyze simulation run results |
| `collect_metrics.py` | Collect metrics from events.jsonl (Plan #227) |
| `compare_experiments.py` | Compare metrics between two runs (Plan #227) |
| `view_log.py` | Parse run.jsonl events |
| `concat_for_review.py` | Concatenate files for review |
| `build_review_package.sh` | Build EXTERNAL_REVIEW_PACKAGE.md from target architecture docs |

### CI/Check

| Script | Purpose |
|--------|---------|
| `check.sh` | One-command validation: runs all CI checks locally (pytest, mypy, lint, doc-coupling) |
| `health_check.py` | Meta-process health check (validates worktrees, claims, hooks, config, git state) |
| `implementation_quiz.py` | Post-implementation quiz on changed files (Plan #296) |

### Setup

| Script | Purpose |
|--------|---------|
| `setup_hooks.sh` | Install git hooks |
| `repo_root.sh` | Get repository root directory (used by hooks/scripts) |

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
python scripts/check_doc_coupling.py --bidirectional  # Check both directions (Plan #216)
python scripts/check_doc_coupling.py --suggest-all FILE  # Show all relationships for FILE

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

# Merge PRs (use make finish for full lifecycle)
python scripts/merge_pr.py 123           # Merge PR #123
python scripts/merge_pr.py 123 --dry-run # Check without merging

# Branch cleanup (stale branches from merged PRs)
python scripts/cleanup_branches.py           # List stale branches
python scripts/cleanup_branches.py --delete  # Delete stale branches
python scripts/cleanup_branches.py --all     # Include abandoned PRs too
# Run periodically to keep branch count low

# Worktree cleanup (orphaned worktrees from merged PRs)
python scripts/cleanup_orphaned_worktrees.py         # Report orphaned worktrees
python scripts/cleanup_orphaned_worktrees.py --auto  # Auto-cleanup (safe only)
python scripts/cleanup_orphaned_worktrees.py --force # Force cleanup (loses uncommitted!)
```

## Meta-Process Weight (Plan #218)

```bash
# Check current weight and enabled checks
python scripts/meta_process_config.py

# Check if a specific check is enabled
python scripts/meta_process_config.py --check doc_coupling_strict

# List all checks and their minimum weights
python scripts/meta_process_config.py --list-checks
```

## Symbol Extraction (Plan #219)

```bash
# Extract symbols from a file
python scripts/symbol_extractor.py src/world/world.py

# Validate a specific symbol exists
python scripts/symbol_extractor.py src/world/world.py --validate World

# Find symbol at a line number
python scripts/symbol_extractor.py src/world/world.py --line 50
```

## Bootstrap Meta-Process (Plan #220)

```bash
# Analyze repo structure
python scripts/bootstrap_meta_process.py --analyze

# Initialize meta-process files at light weight
python scripts/bootstrap_meta_process.py --init --weight light

# Check progress toward full adoption
python scripts/bootstrap_meta_process.py --progress
```

## Configuration

Edit `relationships.yaml` to add doc relationships:
- `governance`: ADR → source file mappings
- `couplings`: source → doc mappings (for CI enforcement)

## Implementation Quiz (Plan #296)

```bash
# Quiz all changed files in current branch
python scripts/implementation_quiz.py

# Quiz specific files
python scripts/implementation_quiz.py --file src/world/ledger.py

# Dry run - show what would be quizzed
python scripts/implementation_quiz.py --dry-run

# Quiz against a different base branch
python scripts/implementation_quiz.py --base origin/main

# Show quiz configuration
python scripts/implementation_quiz.py --config
```

Configuration in `meta-process.yaml`:
- `quiz.integration`: manual | prompt | automatic
- `quiz.min_lines_changed`: minimum lines to include file
- `quiz.include_extensions`: file types to quiz
