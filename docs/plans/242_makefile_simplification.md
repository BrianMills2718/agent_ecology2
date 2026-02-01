# Gap 242: Makefile Workflow Simplification

**Status:** ✅ Complete

**Verified:** 2026-02-01T02:12:32Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-01T02:12:32Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: b844530
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Makefile had 54 targets (before this work began). Many were thin wrappers around single scripts, redundant variants, or dead targets. The large surface area made CLAUDE.md bloated and the workflow unclear.

**Target:** ~15 targets covering only the core workflow and simulation. Everything else accessed via scripts directly. CC hooks enforce that dangerous operations (merge, worktree management) go through make.

## What Was Done

### Phase 1 (PR #868): Remove dead targets
Removed 8 targets: `branch`, `pr-create`, `merge`, `pr-merge-admin`, 5x `dash-v2-*`. (54 → 46)

### Phase 2 (PR #870): Remove redundant wrappers
Removed 6 targets: `rebase`, `gaps`/`gaps-sync`/`gaps-check`, `clean-claims`/`clean-merged`. (46 → 40)

### Phase 3 (this PR): Slim to core
Removed 25 targets that were thin wrappers or rarely-used variants:
- **Thin wrappers** (script is just as easy to call directly): `claim`, `release`, `claims`, `pr-list`, `pr-view`, `worktree-list`, `mypy`, `lint`, `lint-suggest`, `install`
- **Variants** (consolidated as flags): `test-quick`, `check-quick`, `worktree-remove-force` (now `FORCE=1`), `health-fix` (now `--fix` flag), `recover-auto` (now `--auto` flag)
- **Rarely used**: `health`, `recover`, `clean-branches`, `clean-branches-delete`, `clean-worktrees`, `clean-worktrees-auto`, `ci-status`, `ci-require`, `ci-optional`, `install-hooks`

Final: 15 targets (14 public + 1 internal). (40 → 15)

Also:
- Fixed `enforce-make-merge.sh` hook: removed stale `make merge` references
- Updated CLAUDE.md: slimmed quick reference, fixed all stale make target refs
- Updated scripts/CLAUDE.md: removed stale `make merge`/`make clean-worktrees` refs

## Acceptance Criteria

- [x] Makefile has <20 targets
- [x] CC hooks enforce dangerous operations go through make
- [x] No broken references in CLAUDE.md or patterns
- [x] `make help` shows a clean, focused command list
