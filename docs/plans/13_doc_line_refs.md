# Gap 13: Doc Line Number References

**Status:** 📋 Planned
**Priority:** Low
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Documentation references code by line numbers which become stale.

**Target:** Reference code by function/class names which are more stable.

---

## Motivation

Line numbers change constantly:
- Adding imports shifts everything
- Refactoring moves code
- Documentation goes stale silently

Function/class names are more stable anchors.

---

## Plan

### Phase 1: Identify References

1. Grep docs for `:123` style line references
2. Catalog which need updating
3. Prioritize high-traffic docs

### Phase 2: Update References

Change from:
```markdown
See `src/world/ledger.py:145` for transfer logic.
```

To:
```markdown
See `Ledger.transfer_scrip()` in `src/world/ledger.py`.
```

### Phase 3: CI Check (Optional)

1. Script to detect line number references
2. Warn on new line number refs in PRs

---

## Required Tests

None - documentation only.

---

## Verification

- [ ] Major docs updated to use function/class names
- [ ] No critical line number references remain
- [ ] Optional: CI warns on new line refs
