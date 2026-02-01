# Gap 249: Plan-to-Diff Verification

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** —
**Blocks:** —

---

## Gap

**Current:** `parse_plan.py` (137 lines) parses "Files Affected" from plans. `check-file-scope.sh` hook blocks edits to undeclared files during implementation (disabled by default). 56% of active plans have "Files Affected" sections. But no merge-time check compares `git diff --name-only` against declarations. Scope creep is partially prevented (hook), but plan drift (declared files never touched = incomplete implementation) is undetected.

**Target:** A merge-time verification script that compares actual diff against plan declarations and reports discrepancies at three severity levels.

**Why Medium:** Plan drift hasn't caused visible problems yet, but as the codebase grows and more plans are in flight, undiscovered incomplete implementations become harder to catch retroactively.

---

## References Reviewed

- `meta-process/ISSUES.md` — MP-015 investigation findings
- `scripts/parse_plan.py` — 137 lines, already parses "Files Affected" sections
- `hooks/check-file-scope.sh` — existing scope check (disabled by default)
- `docs/plans/TEMPLATE.md` — "Files Affected" section format
- `scripts/check_doc_coupling.py` — example of existing merge-time validation pattern

---

## Open Questions

### Before Planning

1. [ ] **Question:** Should this run in CI or as a pre-merge hook?
   - **Status:** ❓ OPEN
   - **Why it matters:** CI enforcement is more reliable but adds merge latency. Hook enforcement is faster but can be bypassed.

2. [ ] **Question:** What whitelist entries are needed for common false positives?
   - **Status:** ❓ OPEN
   - **Why it matters:** Known false positives include `tests/conftest.py`, `config/schema.yaml`, `__init__.py`, `.claude/CONTEXT.md`. Whitelist needs to be comprehensive enough to avoid noise without hiding real issues.

### Resolved

1. [x] **Question:** Does infrastructure for parsing plan files already exist?
   - **Status:** ✅ RESOLVED
   - **Answer:** Yes. `parse_plan.py` already parses "Files Affected" sections from plan markdown files.
   - **Verified in:** `scripts/parse_plan.py`

2. [x] **Question:** What percentage of plans have "Files Affected" sections?
   - **Status:** ✅ RESOLVED
   - **Answer:** 56% of active plans (9/16) have the section. Required by template but not enforced.
   - **Verified in:** MP-015 investigation

---

## Files Affected

- `scripts/check_plan_diff.py` (create) — main verification script
- `tests/unit/test_check_plan_diff.py` (create)
- `Makefile` (modify) — add `check-plan-diff` target

---

## Plan

### Severity Levels

| Level | Condition | Meaning |
|-------|-----------|---------|
| **HIGH** | `src/` file in diff but not in plan | Scope creep — undeclared production code change |
| **MEDIUM** | `tests/` file in diff but not in plan | Undeclared test addition (usually benign) |
| **WARN** | File declared in plan but not in diff | Plan drift — declared work not done |

### Steps

1. Create `scripts/check_plan_diff.py`:
   - Accept `--plan N` and optional `--branch` (defaults to current branch)
   - Use existing `parse_plan.py` logic to extract declared files
   - Run `git diff --name-only <base>...<branch>` to get actual changes
   - Compare and report discrepancies at severity levels above
   - Exit code: non-zero if any HIGH findings

2. Add whitelist support:
   - Built-in whitelist: `tests/conftest.py`, `__init__.py`, `*.pyc`, `.claude/CONTEXT.md`, `config/schema.yaml`
   - Optional user whitelist via `--whitelist` flag or config

3. Integrate with `make check`:
   - Add `check-plan-diff` Makefile target
   - Only runs when current branch matches `plan-*` pattern
   - Advisory by default (warnings, not failures) until whitelist is tuned

4. Write tests:
   - Test file comparison logic with fixture data
   - Test severity classification
   - Test whitelist filtering
   - Test edge cases: no plan file, no "Files Affected" section, empty diff

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_check_plan_diff.py` | `test_no_discrepancies` | Clean diff matches plan exactly |
| `tests/unit/test_check_plan_diff.py` | `test_undeclared_src_is_high` | Undeclared src/ changes flagged HIGH |
| `tests/unit/test_check_plan_diff.py` | `test_undeclared_tests_is_medium` | Undeclared test/ changes flagged MEDIUM |
| `tests/unit/test_check_plan_diff.py` | `test_untouched_declared_is_warn` | Declared but untouched files flagged WARN |
| `tests/unit/test_check_plan_diff.py` | `test_whitelist_suppresses` | Whitelisted files excluded from findings |
| `tests/unit/test_check_plan_diff.py` | `test_no_files_affected_section` | Graceful handling when section is missing |
| `tests/unit/test_check_plan_diff.py` | `test_exit_code_on_high` | Non-zero exit when HIGH findings exist |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_parse_plan.py` | parse_plan.py behavior unchanged |

---

## E2E Verification

Not applicable — this is a meta-process verification script, not a simulation feature.

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 249`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] Script documented in `scripts/CLAUDE.md`
- [ ] `CLAUDE.md` quick reference updated with new make target

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released
- [ ] Branch merged or PR created

---

## Uncertainties

| Question | Status | Resolution |
|----------|--------|------------|
| False positive rate in practice — is whitelist sufficient? | ❓ Open | Start advisory, tune whitelist from real usage |
| Plans without "Files Affected" — enforce or skip? | ❓ Open | Skip with warning initially; enforcement is a separate concern |
| **Is `parse_plan.py` importable or CLI-only?** | ❓ Open | If logic is in `if __name__` / `main()` with no importable API, must refactor it first or duplicate parsing logic. Check before assuming reuse. |
| **When does advisory graduate to enforcement?** | ❓ Open | Need a concrete trigger: e.g., "enforce after 10 PRs pass with zero false positives" or "enforce after whitelist is stable for 2 weeks." Without a trigger, advisory mode becomes permanent and the check never catches anything. |

---

## Notes

- Builds on existing `parse_plan.py` infrastructure — reuse, don't rewrite
- `check-file-scope.sh` hook covers scope creep during implementation; this covers drift at merge time
- Advisory mode first, enforcement later — avoids blocking merges while tuning
- Source: MP-015 investigation in `meta-process/ISSUES.md`
