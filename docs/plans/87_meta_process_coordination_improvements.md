# Plan 87: Meta-Process Coordination Improvements

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** None
**Blocks:** #85

---

## Gap

**Current:** The worktree enforcement hook blocks ALL writes in main, including:
- Creating new plan files (coordination artifacts)
- Editing process documentation (docs/meta/*.md)

This forces worktree creation for pure coordination work, adding friction without benefit.

**Target:** Allow specific coordination file types from main while maintaining protection for implementation files.

**Why Medium:** Reduces friction for meta-process improvements and plan creation without compromising isolation guarantees.

---

## References Reviewed

- `.claude/hooks/protect-main.sh` - Existing worktree enforcement hook
- `docs/meta/19_worktree-enforcement.md` - Worktree enforcement documentation
- `CLAUDE.md:173-182` - Coordination files whitelist section

---

## Files Affected

- `.claude/hooks/protect-main.sh` (modify) - Add exceptions for plan files and docs/meta
- `docs/meta/19_worktree-enforcement.md` (modify) - Document new exceptions
- `docs/plans/85_inter_cc_messaging.md` (create) - New plan enabled by this change
- `docs/plans/CLAUDE.md` (modify) - Add Plan 85 to index

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `.claude/hooks/protect-main.sh` | Add `docs/meta/*.md` to whitelist |
| `.claude/hooks/protect-main.sh` | Add exception for NEW `docs/plans/NN_*.md` files |
| `docs/meta/19_worktree-enforcement.md` | Document new exceptions |

### Implementation

1. **Hook changes:**
   - Whitelist `docs/meta/*.md` (process docs, not implementation)
   - Allow creating NEW `docs/plans/[0-9]+_*.md` files (plan creation is coordination)
   - Still block modifying existing plan files (could conflict with claiming instance)

2. **Documentation:**
   - Add "Plan File Exception" section to worktree-enforcement.md
   - Update coordination files table with docs/meta

---

## Required Tests

Manual verification:
- [ ] Can create new plan file from main
- [ ] Cannot modify existing plan file from main
- [ ] Can edit docs/meta/*.md from main
- [ ] Still blocked from editing src/*.py from main

---

## Verification

### Tests & Quality
- [x] Hook correctly allows new plan files
- [x] Hook correctly allows docs/meta edits
- [x] Hook still blocks implementation files

### Documentation
- [x] `docs/meta/19_worktree-enforcement.md` updated with exceptions

### Completion
- [x] Plan file created
- [x] Changes implemented and tested
- [x] Enabled creation of Plan 85

---

## Notes

This plan was created retroactively to document meta-process improvements made during a coordination session. The changes enable more fluid multi-CC coordination while maintaining isolation for implementation work.

**Key principle:** Coordination artifacts (plans, process docs) should be editable from main. Implementation artifacts (code, tests) require worktrees.
