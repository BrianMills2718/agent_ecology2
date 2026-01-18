# Plan 72: Plan Number Enforcement

**Status:** 🚧 In Progress
**Priority:** High
**Blocked By:** None
**Blocks:** Meta-process integrity

---

## Gap

**Current:** CI only validates that commits have `[Plan #N]` or `[Trivial]` prefix. It does NOT verify:
- Plan number matches actual plan content/description
- Only one active branch uses a given plan number
- Branch name matches plan scope

**Result:** Multiple branches can claim the same plan number for different work (see PR #255 using Plan #70 for "Ownership Check" when Plan #70 is "Agent Workflow Phase 1").

**Target:** CI enforces plan number exclusivity - only one active branch per plan number. Validates branch work matches plan description.

---

## Solution

### Phase 1: Plan Number Exclusivity (Minimum Viable)

Add CI check that validates no other open PR uses the same plan number.

**Implementation:**
1. In CI, get plan number from commit messages (`[Plan #N]`)
2. Query GitHub for other open PRs with same plan number
3. Fail if another PR already claims that plan number

### Phase 2: Plan-Content Alignment (Future)

Validate that branch name and work align with plan description. More complex, deferred.

---

## Files Affected

- `.github/workflows/ci.yml` (modify)
- `scripts/check_plan_exclusivity.py` (create)
- `tests/unit/test_check_plan_exclusivity.py` (create)

---

## Required Tests

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_check_plan_exclusivity.py` | `test_extracts_plan_number_from_commits` | Parses `[Plan #N]` from commit messages |
| `tests/unit/test_check_plan_exclusivity.py` | `test_no_conflict_when_unique` | Passes when no other PR uses same plan |
| `tests/unit/test_check_plan_exclusivity.py` | `test_fails_when_duplicate` | Fails when another open PR uses same plan |
| `tests/unit/test_check_plan_exclusivity.py` | `test_ignores_trivial_commits` | `[Trivial]` commits skip check |
| `tests/unit/test_check_plan_exclusivity.py` | `test_ignores_closed_prs` | Closed PRs don't count as conflicts |

---

## Acceptance Criteria

- [ ] CI fails if another open PR already uses the same plan number
- [ ] `[Trivial]` commits are exempt from check
- [ ] Closed/merged PRs don't trigger conflicts
- [ ] Clear error message shows which PR has the conflict

---

## Notes

### Why This Matters

Without this enforcement:
- Multiple instances can accidentally work on "different" features under the same plan number
- Plan tracking becomes unreliable (which PR actually implements Plan #N?)
- Merge conflicts are more likely and harder to resolve

### Design Decision

**Exclusivity, not alignment:** Phase 1 only enforces that plan numbers are unique across open PRs. It does NOT verify the work matches the plan description - that's a harder problem involving semantic understanding.

### Edge Cases

- Self-conflict: PR shouldn't conflict with itself (use PR number to exclude)
- Draft PRs: Should they count? Yes - they're still claiming the plan number
- Different plan numbers in same PR: Take first, or fail if multiple?
