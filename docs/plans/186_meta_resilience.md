# Plan #186: Git-Level Meta-Process Resilience

**Status:** ✅ Complete

**Verified:** 2026-01-25T05:30:00Z
**Verification Evidence:**
```yaml
completed_by: Implementation
timestamp: 2026-01-25T05:30:00Z
notes: |
  - Git hooks installed as symlinks in .git/hooks/
  - Makefile has install-hooks and ensure-hooks targets
  - make test/check auto-install hooks via ensure-hooks
  - Pre-commit validates plan index completeness (step 5)
  - Inline CWD check in .claude/settings.json (more resilient than file-based)
tests:
  manual_verification:
    - hooks_auto_install: "Verified - rm .git/hooks/*, make ensure-hooks reinstalls"
    - plan_index_check: "Verified - 999_test.md detected as not in index"
  regression: 2264 tests pass (1 pre-existing isolation failure unrelated)
```

**Priority:** **Critical**
**Blocked By:** None
**Blocks:** All meta-process reliability

---

## Gap

**Current:** Meta-process enforcement relies on CC being able to run bash. When bash breaks (CWD invalid, hooks fail), enforcement stops and drift accumulates. Git hooks exist but aren't installed.

**Target:** Critical enforcement at git level - works regardless of CC state. Git hooks installed and validated.

**Why Critical:** User has tried to fix meta-process drift "100 times" - it keeps returning because all enforcement depends on CC being functional. When CC breaks, drift returns.

---

## References Reviewed

- `.claude/settings.json` - Hook configuration uses relative paths
- `.claude/hooks/check-cwd-valid.sh` - First hook, designed to catch invalid CWD but can't run when bash fails
- `hooks/pre-commit` - Exists but not installed in `.git/hooks/`
- `hooks/CLAUDE.md` - Documents installation but not enforced
- `.git/hooks/` - Empty (hooks not installed)
- `docs/plans/43_meta_enforcement.md` - Previous attempt, marked complete but hooks not actually installed

---

## Files Affected

- `.git/hooks/pre-commit` (symlink - create)
- `.git/hooks/commit-msg` (symlink - create)
- `.git/hooks/pre-push` (symlink - create)
- `.git/hooks/post-commit` (symlink - create)
- `hooks/pre-commit` (modify - add plan index validation)
- `Makefile` (modify - add install-hooks target and auto-install)
- `.claude/settings.json` (modify - use absolute paths)

---

## Plan

### Root Cause Analysis

The failure chain:
1. CC works in worktree
2. Worktree deleted (by `make finish`, another CC, etc.)
3. CC's CWD points to non-existent directory
4. Bash commands fail (including hooks)
5. Enforcement stops, drift accumulates

Why previous fixes failed:
- All enforcement depends on CC being able to run bash
- Git hooks existed but weren't installed
- No auto-installation mechanism

### Solution: Two-Layer Defense

**Layer 1: Git Hooks (works even when CC broken)**
- Install hooks as symlinks
- Add plan index validation to pre-commit
- Validates on EVERY commit, regardless of CC state

**Layer 2: CC Hook Resilience**
- Use absolute paths for first CC hook
- Allows graceful error when CWD invalid

### Changes Required

| File | Change |
|------|--------|
| `hooks/pre-commit` | Add plan index validation |
| `Makefile` | Add `install-hooks` target, call from common targets |
| `.git/hooks/*` | Create symlinks to `hooks/` |
| `.claude/settings.json` | Change first hook to absolute path |

### Steps

1. Add plan index validation to `hooks/pre-commit`
2. Create `install-hooks` target in Makefile
3. Hook into `make test`, `make check` to auto-install hooks
4. Install hooks (symlinks)
5. Update `.claude/settings.json` with absolute path for check-cwd-valid.sh
6. Test: create plan file without index entry, verify blocked

---

## Required Tests

### Manual Verification (git hooks can't have unit tests)

| Scenario | Steps | Expected |
|----------|-------|----------|
| New plan not in index | Create `docs/plans/999_test.md`, try to commit | BLOCKED by pre-commit |
| Plan in index | Create file AND add to index, commit | ALLOWED |
| Hooks auto-install | `rm .git/hooks/*`, run `make test` | Hooks recreated |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/` (all) | No regressions |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Prevent plan drift | Create plan file without index, commit | Commit blocked |
| Auto-install | Delete hooks, run make command | Hooks reinstalled |

---

## Verification

### Tests & Quality
- [x] Manual test: new plan without index entry blocked
- [x] Manual test: hooks auto-install on `make test`
- [x] Full test suite passes: `pytest tests/` (2264 pass, 1 pre-existing isolation issue)
- [x] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [x] `hooks/CLAUDE.md` notes auto-install behavior
- [x] Root `CLAUDE.md` updated if needed (already documents make commands)

### Completion Ceremony
- [x] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released
- [ ] Branch merged

---

## Notes

This plan enforces at git level, not CC level. The principle: CC hooks are convenience, git hooks are enforcement. Git hooks run on every commit regardless of CC state.
