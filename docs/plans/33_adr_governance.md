# Gap #33: ADR Governance System

**Status:** ✅ Complete

**Verified:** 2026-01-13T18:32:59Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-13T18:32:59Z
tests:
  unit: 997 passed in 10.83s
  e2e_smoke: skipped (--skip-e2e)
  doc_coupling: passed
commit: d7ca40d
```
**Certainty:** 100%
**Branch:** `plan-33-adr-governance`
**CC-ID:** -
**Blocked by:** None
**Required for:** Documentation consistency, decision tracking

## Summary

Implement Architecture Decision Records (ADRs) with enforceable linking to source code via governance headers.

## Problem

Claude Code instances lose track of architectural decisions and start ignoring ADRs, plans, etc. without warning. There's no systematic way to surface decisions at the point where they're relevant (when reading code).

## Solution

1. **ADR Directory** - `docs/adr/` with README, TEMPLATE, and ADR files
2. **Governance Config** - `scripts/governance.yaml` maps files → ADRs
3. **Sync Script** - `scripts/sync_governance.py` generates code headers
4. **CI Enforcement** - `--check` mode fails if headers drift

### Safeguards (Critical)

- Dry-run by default (--apply required)
- Only modifies between `GOVERNANCE START/END` markers
- Python syntax validation before replacing
- Git dirty check (--force to override)
- Atomic writes (temp file, validate, replace)
- Backup option (--backup)

## Implementation

### Files Created

| File | Purpose |
|------|---------|
| `docs/adr/README.md` | ADR index and usage guide |
| `docs/adr/TEMPLATE.md` | Template for new ADRs |
| `docs/adr/0001-everything-is-artifact.md` | First migrated ADR |
| `docs/adr/0002-no-compute-debt.md` | Second migrated ADR |
| `docs/adr/0003-contracts-can-do-anything.md` | Third migrated ADR |
| `scripts/governance.yaml` | File → ADR mappings |
| `scripts/sync_governance.py` | Sync script with safeguards |

### CI Integration

Added `governance-sync` job to `.github/workflows/ci.yml` that runs `--check` mode.

## Required Tests

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_sync_governance.py` | `test_dry_run_no_changes` | Dry run doesn't modify files |
| `tests/test_sync_governance.py` | `test_generates_correct_header` | Header format is correct |
| `tests/test_sync_governance.py` | `test_only_modifies_between_markers` | Code outside markers untouched |
| `tests/test_sync_governance.py` | `test_syntax_validation` | Syntax validation works |
| `tests/test_sync_governance.py` | `test_missing_adr_fails` | Reference to nonexistent ADR fails |
| `tests/test_sync_governance.py` | `test_check_mode_detects_drift` | --check finds out-of-sync files |

## Completion Criteria

- [x] ADR directory structure created
- [x] 3+ existing decisions migrated to ADRs
- [x] governance.yaml with initial mappings
- [x] sync_governance.py with all safeguards
- [x] Tests pass (12/12)
- [x] CI workflow updated
- [x] Source files have governance headers
