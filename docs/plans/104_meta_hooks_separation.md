# Plan 104: Meta-Process Hooks Separation

**Status:** 📋 Deferred

**Priority:** Low
**Blocked By:** #103
**Blocks:** #105

---

## Gap

**Current:** Git hooks live in `hooks/` at root level, separate from other meta-process components.

**Target:** Hooks moved to `meta/hooks/` alongside other meta-process components.

**Why:** Completes meta-process consolidation, makes extraction easier.

**Why Deferred:**
- Plan #103 must complete first
- Hooks require updating `setup_hooks.sh` and potentially git config
- Lower priority than documentation separation
- Risk of breaking developer workflows

---

## Scope

This plan covers **Phase 3** of meta-process separation:
- Move `hooks/` → `meta/hooks/`
- Update `scripts/setup_hooks.sh` to use new path
- Update any git config references

---

## Changes Required

### Files to Move

| From | To |
|------|-----|
| `hooks/commit-msg` | `meta/hooks/commit-msg` |
| `hooks/pre-commit` | `meta/hooks/pre-commit` |

### Files to Update

| File | Change |
|------|--------|
| `scripts/setup_hooks.sh` | Update hooks path to `meta/hooks/` |
| `CLAUDE.md` | Update hooks reference |
| `scripts/CLAUDE.md` | Update hooks reference |
| `.gitconfig` (if any) | Update `core.hooksPath` |

---

## Implementation Steps

1. Wait for Plan #103 to complete
2. Move `hooks/` to `meta/hooks/`
3. Update `scripts/setup_hooks.sh` path
4. Update CLAUDE.md references
5. Test hook installation on fresh clone
6. Verify commit-msg and pre-commit hooks work

---

## Required Tests

### Manual Verification

- [ ] `bash scripts/setup_hooks.sh` succeeds
- [ ] Commit with bad message is rejected
- [ ] Pre-commit runs doc-coupling check
- [ ] Fresh clone can install hooks

---

## Acceptance Criteria

- [ ] `meta/hooks/` directory exists with hook files
- [ ] `scripts/setup_hooks.sh` uses new path
- [ ] No references to root `hooks/` remain
- [ ] Hook installation works on fresh clone
- [ ] Both hooks function correctly

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Developers have old hooks path | setup_hooks.sh handles migration |
| Git config points to old path | Script updates git config |
| Fresh clones confused | Clear documentation |

---

## Related

- Plan #103: Meta-Process Documentation Separation (Phase 1-2) - **blocks this**
- Plan #105: Meta-Process Scripts Separation (Phase 4)
