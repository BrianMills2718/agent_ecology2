# Plan #41: Meta-Process Enforcement Gaps

**Status:** 🚧 In Progress

**Priority:** **Critical**
**Blocked By:** None
**Blocks:** All future work (meta-process integrity)

---

## Problem

The meta-process has good documentation but **brittle or missing enforcement**. Multiple gaps allow work to bypass verification:

### Gap 1: Test Parser Only Handles Tables

`check_plan_tests.py` only parses markdown table format:
```markdown
| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/foo.py` | `test_bar` | Does X |
```

But Claude instances often write bullet format:
```markdown
- `tests/foo.py::test_bar`
```

**Result:** Tests defined in bullets are invisible to CI. Plan #40 had 6 required tests that were never validated.

### Gap 2: No CI Enforcement of complete_plan.py

`complete_plan.py` is documented as "mandatory" but:
- No CI check verifies it was run
- PRs can merge without verification evidence
- Plan status can stay "In Progress" after implementation merges

**Result:** Plan #40 merged without `complete_plan.py` ever running.

### Gap 3: "No Tests Defined" Passes CI

When a plan has no parseable `## Required Tests` section:
- CI reports "No test requirements defined"
- This is treated as **pass**, not fail
- Plans without tests slip through

**Result:** Zero enforcement for plans that don't follow exact format.

### Gap 4: No V1 Acceptance Definition

- No `docs/V1_ACCEPTANCE.md` defining what V1 means
- No `tests/e2e/test_v1_acceptance.py` validating V1 criteria
- "V1 complete" is guesswork based on plan status

**Result:** Can't prove V1 works. Only generic smoke tests exist.

### Gap 5: Acceptance Criteria Not Linked to Tests

Plans have `## Acceptance Criteria` sections but:
- No tooling validates criteria are covered by tests
- No traceability from criteria → test → evidence

**Result:** Criteria exist as documentation only, not gates.

---

## Solution

### Fix 1: Robust Test Parser

Update `check_plan_tests.py` to parse multiple formats:

```python
# Table format (existing)
| `tests/foo.py` | `test_bar` | description |

# Bullet format (new)
- `tests/foo.py::test_bar`
- `tests/foo.py::TestClass::test_method`

# Inline code format (new)
`tests/foo.py::test_bar` - description
```

### Fix 2: CI Verification Evidence Check

Add GitHub Action that:
1. Detects PRs with `[Plan #N]` in commit messages
2. After merge, checks plan file has `**Verified:**` block
3. Fails/warns if implementation merged without evidence

```yaml
# .github/workflows/ci.yml
plan-completion-check:
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  steps:
    - name: Check plan verification evidence
      run: python scripts/check_plan_completion.py --recent-commits 5
```

### Fix 3: Fail on Missing Tests

Change `check_plan_tests.py` behavior:
- Plans marked "In Progress" or "Planned" with no tests → **warning**
- PRs referencing plans with no tests → **fail** (new strict mode)

### Fix 4: V1 Acceptance Criteria

Create:
1. `docs/V1_ACCEPTANCE.md` - defines V1 scope with concrete criteria
2. `tests/e2e/test_v1_acceptance.py` - tests each criterion
3. CI job that runs V1 acceptance on main branch

### Fix 5: Criteria-Test Traceability (Future)

Add optional `criteria_id` to test markers:
```python
@pytest.mark.criteria("AC-1")  # Links to acceptance criteria
def test_agents_can_discover_artifacts():
    ...
```

Script validates all criteria have at least one test.

---

## Implementation Steps

1. **Fix test parser** - Support bullet and inline formats
2. **Add completion check script** - `scripts/check_plan_completion.py`
3. **Add CI job** - Verify evidence exists post-merge
4. **Change CI behavior** - Fail on plans without tests in PRs
5. **Create V1 acceptance** - Definition + E2E test
6. **Update docs/meta** - Document failures and fixes

---

## Progress (as of 2026-01-14)

### Completed
- ✅ **Step 1 (partial):** Bullet format parsing added to `check_plan_tests.py` (lines 129-166)
- ✅ **Step 2:** `scripts/check_plan_completion.py` exists
- ✅ **Step 3:** CI job `plan-completion-evidence` added to `.github/workflows/ci.yml`
- ✅ **Step 6:** `docs/meta/17_verification-enforcement.md` created
- ✅ **Gap 6:** PR check added to `scripts/create_worktree.sh` (warns on existing PRs)
- ✅ **Gap 7:** Blocker enforcement added to `scripts/validate_plan.py` (PR #135)

### Remaining
- ❌ **Step 1 (partial):** Inline code format parsing not implemented
- ❓ **Step 4:** CI strict mode for plans without tests - unclear if done
- ❌ **Step 5:** V1 acceptance doc (`docs/V1_ACCEPTANCE.md`) not created
- ❌ **Step 5:** V1 acceptance test (`tests/e2e/test_v1_acceptance.py`) not created
- ⏳ **Gap 5:** Criteria-Test Traceability - marked as future work

### Recommendation
V1 acceptance (Step 5) is significant scope - requires defining what V1 means and creating comprehensive E2E tests. Consider splitting into a separate plan (e.g., Plan #51: V1 Acceptance Criteria).

---

## Required Tests

### Existing Tests

| Test Pattern | Why |
|--------------|-----|
| `tests/e2e/test_smoke.py` | Smoke tests still work |

**Note:** Parser fix verified manually - Plan #40 now shows 6 tests instead of 0.

---

## Future Tests (Planned for Later Phases)

The following tests are planned for future phases of Plan #41 and are NOT part of this PR's requirements:

| Test File | Test Function | Phase |
|-----------|---------------|-------|
| `tests/unit/test_check_plan_tests.py` | `test_parses_bullet_format` | Parser testing |
| `tests/unit/test_check_plan_completion.py` | `test_detects_missing_evidence` | CI enforcement |
| `tests/e2e/test_v1_acceptance.py` | `test_artifact_discovery` | V1 acceptance |
| `tests/e2e/test_v1_acceptance.py` | `test_artifact_interfaces` | V1 acceptance |
| `tests/e2e/test_v1_acceptance.py` | `test_structured_errors` | V1 acceptance |
| `tests/e2e/test_v1_acceptance.py` | `test_scrip_transfers` | V1 acceptance |
| `tests/e2e/test_v1_acceptance.py` | `test_resource_constraints` | V1 acceptance |

These will be added as Plan #41 progresses through its phases.

---

## Acceptance Criteria

1. `check_plan_tests.py` parses bullet format correctly
2. `check_plan_tests.py` parses inline code format correctly
3. CI fails when PR references plan without required tests
4. CI warns when merged plan lacks verification evidence
5. V1 acceptance criteria documented in `docs/V1_ACCEPTANCE.md`
6. V1 acceptance test exists and passes
7. `docs/meta/17_verification-enforcement.md` updated with lessons learned

---

## Design Rationale

**Why fix parser vs mandate table format?**
- Claude instances naturally vary in formatting
- Mandating exact format adds friction and will be violated
- Robust parsing is more resilient than process compliance

**Why warn vs fail on missing evidence post-merge?**
- Can't block already-merged PRs
- Warning creates visibility for manual follow-up
- Future: could require evidence before merge

**Why V1 acceptance test now?**
- We claimed V1 progress without proof
- E2E acceptance test is the only way to know V1 works
- Sets pattern for V2, V3, etc.

---

## Notes

This plan emerged from investigating why Plan #40 was merged without verification. The root cause was multiple enforcement gaps that compounded:

1. Tests in wrong format → invisible to CI
2. No completion enforcement → script never run
3. "No tests" passes → no safety net
4. No V1 test → can't prove anything works

Each gap alone might be caught. Together, they allowed unverified work through.

**META-PROCESS LESSON:** Enforcement must be:
- **Format-agnostic** - Parse what humans write, not what we wish they'd write
- **Positive verification** - Require evidence, not absence of failure
- **Defense in depth** - Multiple checks, not single points of failure

### Gap 6: Claims Are Local-Only (Not Shared)

The claim system stores claims in `.claude/active-work.yaml` which is LOCAL. The `create_worktree.sh` script:
1. Claims work in `.claude/active-work.yaml` (local file)
2. Creates worktree
3. Does NOT push the claim to origin

**Result:** Multiple instances can claim the same plan if they don't pull each other's changes first. Plan #41 had 4 different PRs (#117, #118, #120, #123) because instances claimed simultaneously without seeing each other's claims.

**Fix:** Add check for existing open PRs on the same plan before allowing a claim. In `create_worktree.sh`:
```bash
# Check for existing PRs on this plan
if [ -n "$PLAN" ]; then
    EXISTING_PRS=$(gh pr list --state open --search "[Plan #$PLAN]" 2>/dev/null | wc -l || echo "0")
    if [ "$EXISTING_PRS" -gt 0 ]; then
        echo "WARNING: There are already $EXISTING_PRS open PRs for Plan #$PLAN"
        gh pr list --state open --search "[Plan #$PLAN]"
        read -p "Continue anyway? (y/N): " PR_CONTINUE
        if [[ ! "$PR_CONTINUE" =~ ^[Yy]$ ]]; then
            echo "Aborting. Coordinate with existing PR authors first."
            exit 0
        fi
    fi
fi
```

### Gap 7: Blocker Enforcement Not in validate_plan.py

`validate_plan.py` is the pre-implementation gate, but it didn't check the "Blocked By" field. Plans could start implementation even when blocked by incomplete plans.

**Evidence:** Plan #44 (blocked by #42) was marked Complete while Plan #42 was still "Planned".

**Fix:** Added to `validate_plan.py`:
- `get_plan_blockers(plan_num)` - extracts blocker plan numbers from `**Blocked By:**` field
- `get_plan_status(plan_num)` - gets status of a plan
- `check_active_blockers(plan_num)` - returns list of incomplete blockers

Now `validate_plan.py --plan 44` shows:
```
🚫 BLOCKED BY INCOMPLETE PLANS:
  - Plan #42 (📋 Planned)

  Cannot implement this plan until blockers are complete.
```

And exits with code 1 to fail CI/gating.
