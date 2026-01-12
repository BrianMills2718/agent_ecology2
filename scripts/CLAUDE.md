# Scripts Directory

Utility scripts for development and CI. All scripts support `--help` for options.

## Script Summary

| Script | Purpose |
|--------|---------|
| `check_doc_coupling.py` | Verify docs updated when source changes |
| `check_plan_tests.py` | Verify/run plan test requirements |
| `check_claims.py` | Manage active work claims |
| `sync_plan_status.py` | Sync plan status across files |
| `sync_governance.py` | Sync ADR governance headers |
| `validate_plan.py` | Pre-implementation validation gate |
| `validate_plan_completion.py` | Validate plan completion criteria |
| `plan_progress.py` | Show plan implementation progress |
| `view_log.py` | Parse run.jsonl events |
| `concat_for_review.py` | Concatenate files for review |
| `setup_hooks.sh` | Install git hooks |
| `generate_coordination_tables.py` | Auto-generate CLAUDE.md coordination tables |

Config files: `relationships.yaml`, `doc_coupling.yaml`, `governance.yaml`

## Git Hooks

```bash
bash scripts/setup_hooks.sh   # Install (once after clone)
git commit --no-verify        # Bypass (not recommended)
```

- **pre-commit**: Doc-coupling + mypy on staged files
- **commit-msg**: Requires `[Plan #N]` or `[Unplanned]` prefix

## Common Commands

```bash
# Doc coupling
python scripts/check_doc_coupling.py --suggest     # What docs to update
python scripts/check_doc_coupling.py --strict      # CI mode

# Governance sync
python scripts/sync_governance.py --check          # CI mode
python scripts/sync_governance.py --apply          # Apply changes

# Plan validation
python scripts/validate_plan.py --plan N           # Pre-impl gate

# Plan tests (TDD)
python scripts/check_plan_tests.py --plan N --tdd  # What to write
python scripts/check_plan_tests.py --plan N        # Run tests

# Claims
python scripts/check_claims.py --list              # See claims
python scripts/check_claims.py --claim --task "X"  # Claim work
python scripts/check_claims.py --release --validate # Done + verify

# Coordination tables (auto-generated)
python scripts/generate_coordination_tables.py          # Preview
python scripts/generate_coordination_tables.py --check  # CI mode
python scripts/generate_coordination_tables.py --apply  # Update CLAUDE.md
```

## Configuration

Edit `doc_coupling.yaml` to add source→doc mappings. Edit `governance.yaml` to add file→ADR mappings.
