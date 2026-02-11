# Scripts Directory

Utility scripts for development and CI. All scripts support `--help` for options.

## Script Summary

### Core Workflow

| Script | Purpose |
|--------|---------|
| `merge_and_cleanup.py` | Merge PR + cleanup branch (used by `make finish`) |
| `merge_pr.py` | Merge PRs via GitHub CLI |
| `complete_plan.py` | Mark plan complete (runs tests, records evidence) |
| `generate_plan_index.py` | Auto-generate docs/plans/CLAUDE.md index from plan files |
| `sync_plan_status.py` | Sync plan status + validate content consistency |

### Worktree Coordination (Parallel CC Isolation)

| Script | Purpose |
|--------|---------|
| `check_claims.py` | Manage worktree claims — create, release, list, verify (`.claude/active-work.yaml`) |
| `safe_worktree_remove.py` | Safely remove worktrees — checks for uncommitted changes, active sessions |

### Documentation & Quality

| Script | Purpose |
|--------|---------|
| `file_context.py` | **Unified context loader**: CLAUDE.md chain, ADRs, coupled docs, concerns, tech debt |
| `extract_relevant_context.py` | Extract GLOSSARY, ONTOLOGY, ADR, PRD, and domain model context for a file |
| `audit_governance_mappings.py` | Audit governance mappings for completeness |
| `build_doc_index.py` | Build searchable index of docs for semantic search |
| `semantic_doc_search.py` | BM25 semantic search over documentation |
| `check_governance_completeness.py` | CI check for governance mapping coverage |
| `check_doc_coupling.py` | Verify docs updated when source changes |
| `check_planning_patterns.py` | Validate planning patterns (Open Questions, uncertainties) |
| `sync_governance.py` | Sync ADR governance headers |
| `check_mock_usage.py` | Detect suspicious mock patterns in tests |
| `check_claude_md.py` | Validate CLAUDE.md existence, coverage, and phantom refs |
| `check_locked_files.py` | Protect locked acceptance criteria (manual) |
| `validate_code_map.py` | Validate code mapping files (manual) |
| `get_governance_context.py` | Get doc graph context for a file (ADRs + coupled docs) |
| `visualize_doc_graph.py` | Visualize documentation graph (text, DOT, PNG/SVG) |
| `generate_doc_graph_html.py` | Generate interactive HTML visualization (D3.js) |
| `validate_relationships.py` | Validate relationships.yaml internal consistency (stale refs, missing ADRs) |
| `check_ontology_freshness.py` | Compare ONTOLOGY.yaml fields/actions/methods against source via AST |

### Plan Management

| Script | Purpose |
|--------|---------|
| `check_plan_tests.py` | Verify/run plan test requirements |

### Meta-Process Configuration

| Script | Purpose |
|--------|---------|
| `meta_config.py` | Read meta-process configuration (used by hooks/scripts) |
| `symbol_extractor.py` | Extract symbols from Python files (AST-based) |
| `bootstrap_meta_process.py` | Bootstrap meta-process for existing repos |
| `export_meta_process.py` | Export meta-process to standalone template repository |

### Analysis

| Script | Purpose |
|--------|---------|
| `cleanup_branches.py` | Delete stale remote branches (merged PRs) |
| `analyze_logs.py` | Analyze simulation logs (journeys, collaboration, loops) |
| `analyze_run.py` | Analyze simulation run results |
| `collect_metrics.py` | Collect metrics from events.jsonl |
| `compare_experiments.py` | Compare metrics between two runs |
| `view_log.py` | Parse run.jsonl events |
| `concat_for_review.py` | Concatenate files for review |
| `build_review_package.sh` | Build EXTERNAL_REVIEW_PACKAGE.md from target architecture docs |

### CI/Check

| Script | Purpose |
|--------|---------|
| `check.sh` | One-command validation: runs all CI checks locally (pytest, mypy, doc-coupling) |

### Setup

| Script | Purpose |
|--------|---------|
| `setup_hooks.sh` | Install git hooks |
| `repo_root.sh` | Get repository root directory (used by hooks/scripts) |

Config: `relationships.yaml` (unified doc graph)

## Common Commands

```bash
# Context loading
python scripts/file_context.py src/world/contracts.py           # Load all context for a file
python scripts/file_context.py src/world/contracts.py --json    # JSON output

# Doc coupling
python scripts/check_doc_coupling.py --suggest     # What docs to update
python scripts/check_doc_coupling.py --strict      # CI mode

# Plan status sync
python scripts/sync_plan_status.py --check         # CI mode (validates all)
python scripts/sync_plan_status.py --check --warn-stale 14  # + stale plan advisory
python scripts/sync_plan_status.py --sync          # Sync index to match files
python scripts/sync_plan_status.py --list          # Show all statuses
python scripts/sync_plan_status.py --warn-stale 14 # Standalone stale check

# Governance sync
python scripts/sync_governance.py --check          # CI mode
python scripts/sync_governance.py --apply          # Apply changes

# Plan completion
python scripts/complete_plan.py --plan N           # Complete with verification
python scripts/complete_plan.py --plan N --dry-run # Check without updating

# Mock usage
python scripts/check_mock_usage.py                 # Report mocks
python scripts/check_mock_usage.py --strict        # CI mode

# Branch cleanup
python scripts/cleanup_branches.py           # List stale branches
python scripts/cleanup_branches.py --delete  # Delete stale branches

# Quiz (scope-aware)
python scripts/generate_quiz.py src/world/contracts.py  # Full quiz
python scripts/generate_quiz.py src/world/contracts.py --trivial-threshold 5  # Reduced for small changes

# Worktree coordination (parallel CC instances)
python scripts/check_claims.py --list                   # List all claims
python scripts/check_claims.py --claim --plan 42 --task "Fix bug" --id plan-42-fix  # Create claim
python scripts/check_claims.py --release                # Release current branch's claim
python scripts/check_claims.py --cleanup                # Remove old completed entries
```

## Configuration

Edit `relationships.yaml` to add doc relationships:
- `governance`: ADR -> source file mappings
- `couplings`: source -> doc mappings (for CI enforcement)
