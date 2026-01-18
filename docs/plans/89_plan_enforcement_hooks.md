# Plan 89: Plan Enforcement Hooks

**Status:** ✅ Complete

**Verified:** 2026-01-18T20:01:45Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-18T20:01:45Z
tests:
  unit: 1662 passed, 9 skipped, 3 warnings in 65.44s (0:01:05)
  e2e_smoke: PASSED (5.76s)
  e2e_real: PASSED (27.83s)
  doc_coupling: passed
commit: e9e7bc9
```
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Plans have `Files Affected` and `References Reviewed` sections (as of the recent template update), but there's no enforcement. CC can still:
- Edit files not declared in the plan
- Skip exploration and guess at implementations

**Target:** Two new hooks enforce plan discipline:
1. **File scope hook**: Block edits to files not in plan's `Files Affected` section
2. **References warning hook**: Warn (not block) if plan lacks `References Reviewed` section

---

## References Reviewed

- `.claude/hooks/protect-main.sh:1-125` - existing hook structure and patterns
- `.claude/settings.json` - hook configuration format
- `docs/meta/META_TEMPLATE_SPEC_V0.1.md:540-562` - proposed hook specifications
- `docs/meta/15_plan-workflow.md:81-103` - plan template with new sections
- `docs/plans/CLAUDE.md` - plan file location patterns

---

## Files Affected

- .claude/hooks/check-file-scope.sh (modify)
- .claude/hooks/check-references-reviewed.sh (modify)
- .claude/settings.json (modify)
- docs/meta/19_worktree-enforcement.md (modify)
- tests/test_hooks.py (create)

---

## Plan

### Hook 1: check-file-scope.sh

**Trigger:** PreToolUse on Edit/Write

**Logic:**
1. Get edited file path from tool input
2. Determine current plan from worktree branch name (e.g., `plan-89-hooks` → Plan #89)
3. Read plan file (`docs/plans/89_*.md`)
4. Parse `## Files Affected` section
5. Check if edited file is in the list
6. If not listed: BLOCK with message "File not in plan scope. Update plan's Files Affected first."

**Edge cases:**
- No plan number in branch name → Allow (not plan-based work)
- Plan file doesn't exist → Allow with warning
- No `Files Affected` section → Warn but allow (backwards compatibility)
- File matches a glob pattern in Files Affected → Allow

### Hook 2: check-references-reviewed.sh

**Trigger:** PreToolUse on Edit/Write (first edit only, or always?)

**Logic:**
1. Determine current plan from worktree branch name
2. Read plan file
3. Check for `## References Reviewed` section
4. Check it has at least 2 entries with file:line format
5. If missing/empty: WARN (not block) "Plan lacks References Reviewed. Explore codebase first."

**Design decision:** Warning only, not blocking. This nudges good behavior without creating hard friction.

### Implementation Steps

1. Create `check-file-scope.sh` with plan parsing logic
2. Create `check-references-reviewed.sh` with section detection
3. Update `.claude/settings.json` to register hooks
4. Test with a sample plan
5. Update `19_worktree-enforcement.md` to document new hooks

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_hooks.py` | `test_file_scope_blocks_undeclared` | Hook blocks edit to file not in Files Affected |
| `tests/test_hooks.py` | `test_file_scope_allows_declared` | Hook allows edit to file in Files Affected |
| `tests/test_hooks.py` | `test_file_scope_allows_no_plan` | Hook allows edit when branch has no plan number |
| `tests/test_hooks.py` | `test_references_warns_missing` | Hook warns when References Reviewed missing |
| `tests/test_hooks.py` | `test_references_silent_when_present` | Hook silent when References Reviewed exists |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/` | Full test suite - hooks shouldn't break anything |

---

## Verification

- [ ] `check-file-scope.sh` blocks undeclared files
- [ ] `check-file-scope.sh` allows declared files
- [ ] `check-references-reviewed.sh` warns on missing section
- [ ] Hooks registered in settings.json
- [ ] Documentation updated

---

## Notes

**Design decisions:**
- File scope is BLOCK, references is WARN - different severity for different problems
- Parse Files Affected as simple line-by-line, not complex YAML
- Support glob patterns in Files Affected (e.g., `src/world/*.py`)
- Cache plan parsing per-session if performance becomes an issue

**Alternative considered:** Single combined hook vs two separate hooks. Chose separate for clarity and independent enable/disable.
