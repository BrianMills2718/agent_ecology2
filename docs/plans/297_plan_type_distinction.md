# Plan #297: Plan Type Distinction

**Status:** ✅ Complete

**Verified:** 2026-02-05T15:52:57Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-05T15:52:57Z
tests:
  unit: skipped (design plan)
  e2e_smoke: skipped (design plan)
  e2e_real: skipped (design plan)
  doc_coupling: skipped (design plan)
commit: 97ace33
```
**Priority:** Medium
**Theme:** Meta-Process

---

## Problem Statement

Plans marked "Complete" with unchecked verification items cause confusion:
- User thinks implementation is done when only a design doc exists
- No distinction between "design doc complete" and "code merged"
- `--status-only` bypasses verification with no guardrails

Audit of 21 "Complete" plans with unchecked items found:
- 19 were actually done (verification checkboxes just weren't updated)
- 2 had genuine incomplete work (#245, #295)

Root cause: Same template/workflow for design docs and implementation plans.

---

## Proposed Solution

### 1. Add Plan Type Field

Add `type` field to plan template header:

```markdown
**Status:** ✅ Complete

**Verified:** 2026-02-05T15:52:57Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-05T15:52:57Z
tests:
  unit: skipped (design plan)
  e2e_smoke: skipped (design plan)
  e2e_real: skipped (design plan)
  doc_coupling: skipped (design plan)
commit: 97ace33
```
**Type:** design | implementation
**Priority:** High
```

- `design` - Output is the document itself (architecture, analysis, process)
- `implementation` - Output is merged code

### 2. Type-Aware Verification

Update `scripts/complete_plan.py`:

```python
def complete_plan(plan_num, status_only=False):
    plan_type = extract_plan_type(plan_path)

    if plan_type == "design":
        # Design docs: just mark complete, no code verification needed
        # But still require all "Open Questions" resolved
        if has_unresolved_questions(plan_path):
            raise Error("Design doc has unresolved Open Questions")
        mark_complete(plan_path)

    elif plan_type == "implementation":
        if status_only:
            # Require explicit acknowledgment
            if not has_verification_evidence(plan_path):
                raise Error("--status-only requires verification evidence (PR link, commit SHA)")
        else:
            # Normal flow: run tests, check verification items
            run_verification(plan_path)
```

### 3. Block Completion with Unchecked Items

For implementation plans, block `--status-only` if:
- Unchecked `- [ ]` items exist in Verification section
- No PR/commit evidence provided

### 4. Update Plan Template

Update `meta-process/templates/plan.md`:

```markdown
# Plan #N: Title

**Status:** ✅ Complete

**Verified:** 2026-02-05T15:52:57Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-05T15:52:57Z
tests:
  unit: skipped (design plan)
  e2e_smoke: skipped (design plan)
  e2e_real: skipped (design plan)
  doc_coupling: skipped (design plan)
commit: 97ace33
```
**Type:** implementation  <!-- design | implementation -->
**Priority:** High

---

## Problem Statement
...

## Proposed Solution
...

## Verification  <!-- Only for implementation plans -->
- [ ] Tests pass
- [ ] Type checks pass
- [ ] Doc-coupling valid
```

### 5. Backfill Existing Plans (Optional)

Add `**Type:** design` to the 6 design docs identified in audit:
- #234, #246, #284, #285, #294, #296

---

## Files to Modify

| File | Change |
|------|--------|
| `scripts/complete_plan.py` | Add type-aware completion logic |
| `meta-process/templates/plan.md` | Add Type field |
| `scripts/validate_plan.py` | Validate Type field exists |

---

## Verification

- [ ] Plan template includes Type field
- [ ] `complete_plan.py` checks plan type before completion
- [ ] Design plans complete without code verification
- [ ] Implementation plans require verification or explicit evidence
- [ ] Existing tests pass

---

## Notes

This is a lightweight fix. The goal is preventing confusion, not adding bureaucracy.

Design docs are legitimate outputs - they just need different completion criteria than implementation plans.
