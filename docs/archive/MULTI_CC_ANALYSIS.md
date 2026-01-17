# Multi-Claude Code Coordination: Analysis and Recommendations

**Created:** 2026-01-12
**Purpose:** Analyze failure modes and propose improvements for multi-instance Claude Code coordination.

---

## Current System Overview

### Components

| Component | Purpose | Enforcement |
|-----------|---------|-------------|
| **CLAUDE.md hierarchy** | AI context per directory | Automatic (Claude loads) |
| **Plans (`docs/plans/`)** | Gap tracking + implementation | Manual status updates |
| **Doc-code coupling** | Force doc updates with code | CI (strict/soft) |
| **TDD test requirements** | Define tests before implementing | CI (informational) |
| **Active Work table** | Track who's doing what | Manual (in CLAUDE.md) |
| **Git worktrees** | Isolate parallel work | Manual (recommended pattern) |

### Workflow (Intended)

```
1. Claim task in Active Work table
2. Create git worktree/branch
3. Update plan status to "In Progress"
4. Implement (TDD: write tests first)
5. Run tests + mypy + doc-coupling check
6. Update current/ docs
7. Update plan status to "Complete"
8. Clear claim from Active Work table
9. PR/merge
```

---

## Failure Modes

### Category 1: Coordination Failures

#### FM-1: Unclaimed Work Collision
**What:** Two instances start same task without claiming.
**Likelihood:** Medium (claiming is manual, easily forgotten)
**Impact:** High (wasted effort, merge conflicts)
**Current mitigation:** Active Work table (manual)
**Detection:** None until merge conflict

#### FM-2: Stale Claims
**What:** Instance claims work, then user abandons session. Claim remains.
**Likelihood:** High (no expiry mechanism)
**Impact:** Medium (blocks others from starting)
**Current mitigation:** None
**Detection:** None (human must notice staleness)

#### FM-3: No Session Handoff Mechanism
**What:** User ends session (closes terminal, runs /clear, starts new instance) with no way to pass context to next session.
**Likelihood:** High (normal workflow includes session boundaries)
**Impact:** High (next instance starts blind, must rediscover state)
**Current mitigation:** Handoff protocol (manual)
**Detection:** N/A

**Note:** Claude Code auto-compacts (summarizes) but does NOT auto-clear. This failure mode is about **intentional session boundaries**, not surprise context loss. Scenarios requiring handoff:
- User runs `/clear` to reset
- User closes terminal / ends session
- User starts new instance to continue work
- User switches between multiple instances

### Category 2: Status Drift

#### FM-4: Plan Status Not Updated
**What:** Work done but plan status not changed to "In Progress" or "Complete".
**Likelihood:** High (easy to forget)
**Impact:** Medium (coordination confusion, duplicate work)
**Current mitigation:** Soft coupling warning
**Detection:** Manual review only

#### FM-5: Index/Plan Mismatch
**What:** Plan file says "Complete" but `plans/CLAUDE.md` index says "In Progress".
**Likelihood:** Medium (two places to update)
**Impact:** Low (confusion but detectable)
**Current mitigation:** Soft coupling warning
**Detection:** Manual review

#### FM-6: Premature Completion
**What:** Plan marked "Complete" but tests don't pass or docs not updated.
**Likelihood:** Medium
**Impact:** High (false confidence, bugs)
**Current mitigation:** CI checks (but informational)
**Detection:** `check_plan_tests.py` (if run)

### Category 3: Documentation Drift

#### FM-7: Soft Coupling Ignored
**What:** CI warns about doc update needed, warning ignored.
**Likelihood:** High (warnings are easy to ignore)
**Impact:** Medium (docs drift from code)
**Current mitigation:** Warning only
**Detection:** Manual review

#### FM-8: Missing Coupling Definition
**What:** New file created without adding to coupling config.
**Likelihood:** Medium (must remember to update config)
**Impact:** Medium (new code has no doc enforcement)
**Current mitigation:** `--validate-config` (must be run manually)
**Detection:** Manual audit

#### FM-9: GLOSSARY Drift
**What:** New terms introduced without GLOSSARY update.
**Likelihood:** High (soft coupling only)
**Impact:** Low (terminology confusion)
**Current mitigation:** Soft coupling warning
**Detection:** Manual review

### Category 4: Test/Quality Failures

#### FM-10: TDD Skipped
**What:** Implementation done without writing required tests first.
**Likelihood:** High (TDD requires discipline)
**Impact:** Medium (tests may not cover edge cases)
**Current mitigation:** `check_plan_tests.py --tdd` (must be run)
**Detection:** Manual or CI (informational)

#### FM-11: Tests Exist But Don't Test Right Thing
**What:** Test functions exist but don't actually verify plan requirements.
**Likelihood:** Medium
**Impact:** High (false confidence)
**Current mitigation:** Code review
**Detection:** Manual review only

### Category 5: Branch/Merge Failures

#### FM-12: Branch-Plan Mismatch
**What:** No convention linking git branches to plans.
**Likelihood:** High (no convention exists)
**Impact:** Low (harder to track)
**Current mitigation:** None
**Detection:** None

#### FM-13: Long-Running Branches
**What:** Branch diverges significantly from main, painful merge.
**Likelihood:** Medium
**Impact:** Medium (merge conflicts, integration issues)
**Current mitigation:** None
**Detection:** Manual

---

## Risk Matrix

| ID | Failure Mode | Likelihood | Impact | Risk | Priority |
|----|--------------|------------|--------|------|----------|
| FM-3 | No Session Handoff | High | High | **High** | 1 |
| FM-1 | Unclaimed Work Collision | Medium | High | **High** | 2 |
| FM-2 | Stale Claims | High | Medium | **High** | 3 |
| FM-4 | Plan Status Not Updated | High | Medium | **High** | 4 |
| FM-6 | Premature Completion | Medium | High | **High** | 5 |
| FM-10 | TDD Skipped | High | Medium | Medium | 6 |
| FM-7 | Soft Coupling Ignored | High | Medium | Medium | 7 |
| FM-8 | Missing Coupling Definition | Medium | Medium | Medium | 8 |
| FM-11 | Tests Don't Test Right Thing | Medium | High | Medium | 9 |
| FM-12 | Branch-Plan Mismatch | High | Low | Low | 10 |

**Note:** FM-3 downgraded from "Critical" to "High" - it's about session boundaries (user-controlled), not unexpected context loss.

---

## Proposed Improvements

### P1: Session Handoff File (Addresses FM-3)

**Problem:** Context lost on /clear with no handoff mechanism.

**Solution:** Before /clear, write structured handoff to `.claude/handoff.md`:

```markdown
# Session Handoff
**Created:** 2026-01-12T14:30:00
**Plan:** #1 Rate Allocation

## Completed This Session
- Created `src/world/token_bucket.py`
- Added 5 of 7 required tests

## In Progress
- Integrating TokenBucket into Ledger
- File: `src/world/ledger.py` line 145

## Blockers/Notes
- Decimal precision issue - see test_capacity_capping failure

## Next Steps
1. Fix precision issue in TokenBucket._accumulate
2. Complete remaining 2 tests
3. Update resources.md
```

**Implementation:** Add to CLAUDE.md as required step before /clear.

### P2: Claim Expiry Script (Addresses FM-2)

**Problem:** Claims never expire.

**Solution:** Add timestamp to claims, script to check/warn:

```markdown
| CC-ID | Task | Claimed At | Status |
|-------|------|------------|--------|
| CC-7 | Rate Allocation | 2026-01-12T10:00 | Active |
```

Script `scripts/check_claims.py`:
- Warn if claim > 4 hours old
- Option to auto-clear stale claims

### P3: Plan Completion Validator (Addresses FM-6)

**Problem:** Plans marked complete without verification.

**Solution:** Script `scripts/validate_plan_completion.py`:

```bash
python scripts/validate_plan_completion.py --plan 1
```

Checks:
- [ ] All required tests exist
- [ ] All required tests pass
- [ ] Doc-coupling satisfied
- [ ] Plan status is "Complete" in both file and index
- [ ] No TODO comments referencing plan number

Only after all pass can plan be marked complete.

### P4: Branch Naming Convention (Addresses FM-12)

**Problem:** No link between branches and plans.

**Solution:** Convention: `plan-NN-short-description`

```bash
git checkout -b plan-01-token-bucket
```

Add to CI: warn if PR branch doesn't match pattern when plan files changed.

### P5: Promote Soft Couplings Selectively (Addresses FM-4, FM-7)

**Problem:** Important updates hidden in soft warnings.

**Solution:** Promote critical soft couplings to strict:

| Coupling | Current | Proposed |
|----------|---------|----------|
| current/*.md → plans/CLAUDE.md | Soft | **Strict** |
| Plan file → plans/CLAUDE.md index | Soft | **Strict** |
| Terminology → GLOSSARY | Soft | Keep soft |

### P6: Pre-Commit Hook (Addresses FM-4, FM-7, FM-8)

**Problem:** Checks only run in CI, too late.

**Solution:** Git pre-commit hook:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check doc-coupling
python scripts/check_doc_coupling.py --base HEAD~1
if [ $? -ne 0 ]; then
    echo "Doc-coupling violations. Commit blocked."
    exit 1
fi

# Validate coupling config
python scripts/check_doc_coupling.py --validate-config
```

### P7: Claim-Before-Work Enforcement (Addresses FM-1)

**Problem:** Starting work without claiming is easy.

**Solution:** Script `scripts/claim_work.py`:

```bash
# Claim work
python scripts/claim_work.py --plan 1 --cc-id CC-8

# Release claim
python scripts/claim_work.py --release --plan 1

# Check claims
python scripts/claim_work.py --list
```

Features:
- Updates CLAUDE.md Active Work table
- Adds timestamp
- Validates plan exists and isn't already claimed
- Can integrate with git hooks (warn if committing to plan without claim)

### P8: Completion Ceremony Checklist (Addresses FM-6)

**Problem:** Easy to forget completion steps.

**Solution:** Add to plan template, enforce in validator:

```markdown
## Completion Checklist
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan N`
- [ ] Doc-coupling passes: `python scripts/check_doc_coupling.py`
- [ ] Plan file status updated to Complete
- [ ] plans/CLAUDE.md index updated
- [ ] Claim released from Active Work table
- [ ] Branch merged or PR created
```

---

## Additional Improvement Ideas

Beyond the core proposals above, here are additional improvements worth considering:

### A1: Structured Handoff Template

Create `.claude/handoff_template.md`:

```markdown
# Session Handoff
**Date:** YYYY-MM-DD HH:MM
**Plan:** #N - Name
**Branch:** plan-NN-description

## Session Summary
<!-- 2-3 sentences: what was the goal, what was achieved -->

## Changes Made
<!-- Files created/modified with brief description -->
- `src/foo.py` - Added TokenBucket class
- `tests/test_foo.py` - 5 of 7 tests written

## Current State
<!-- Where exactly did you stop? -->
- Working in: `src/world/ledger.py:145`
- Test status: 5 pass, 2 not written yet
- Blocking issue: None / Describe blocker

## Context for Next Session
<!-- What does the next instance need to know? -->
- Design decision: Using Decimal for precision (see DESIGN_CLARIFICATIONS.md)
- Edge case found: Negative capacity not handled
- Question for user: Should debt have a cap?

## Next Steps
1. [ ] Specific next action
2. [ ] Another action
3. [ ] ...
```

**Benefit:** Consistent handoffs, nothing forgotten.

### A2: Session Audit Log

Append session summaries to `.claude/sessions.log` (gitignored):

```
2026-01-12T10:00 | Plan #1 | Started token bucket implementation
2026-01-12T14:30 | Plan #1 | Completed 5/7 tests, ledger integration WIP
2026-01-12T14:35 | Plan #1 | Handoff written, session ended
```

**Benefit:** Track progress over time, debug coordination issues.

### A3: Git Worktree Helper

Script `scripts/worktree.py`:

```bash
# Create worktree for plan (auto-names branch and directory)
python scripts/worktree.py --create --plan 1
# Creates: ../ecology-plan-01 with branch plan-01-rate-allocation

# List active worktrees
python scripts/worktree.py --list

# Clean up merged worktrees
python scripts/worktree.py --cleanup
```

**Benefit:** Reduces friction for parallel work.

### A4: Plan Dependency Validation

When starting a plan, check dependencies:

```bash
python scripts/validate_plan_start.py --plan 2
# Error: Plan #2 is blocked by #1 (not complete)
```

**Benefit:** Prevents starting blocked work.

### A5: Auto-Detect Plan from Branch

If branch is `plan-NN-*`, Claude instances could auto-populate context:

```markdown
<!-- In CLAUDE.md or auto-generated -->
**Current Plan:** #1 Rate Allocation (detected from branch: plan-01-token-bucket)
**Status:** 📋 Planned
**Required Tests:** 7 new, 3 existing
```

**Benefit:** Reduces manual context setting.

### A6: Apply Project Philosophy to Coordination

This project emphasizes **observability over control**. Apply that:

| Principle | Application to Multi-CC |
|-----------|------------------------|
| Observe, don't prescribe | Log session activity, don't block |
| Accept risk, learn from outcomes | Track coordination failures, improve |
| Emergence over prescription | Let patterns emerge, then codify |

Consider: `scripts/coordination_report.py` that analyzes:
- Claim/release patterns
- Branch-plan alignment
- Completion ceremony compliance
- Handoff quality

### A7: Concurrent Edit Detection

Git hooks or file-based locks:

```bash
# Pre-edit hook checks
if [ -f ".claude/editing/$FILE.lock" ]; then
    echo "Warning: $FILE may be edited by another session"
fi
```

**Benefit:** Early warning of conflicts.

### A8: Plan Progress Tracking

Parse plan files for completion:

```bash
python scripts/plan_progress.py --plan 1
# Plan #1: Rate Allocation
# Tests: 0/7 written (0%)
# Verification: 0/10 checked (0%)
# Estimated: Not started
```

**Benefit:** Quantified progress visibility.

### A9: Retrospective Template

After completing a plan, capture learnings:

```markdown
## Plan #N Retrospective

**Completed:** YYYY-MM-DD
**Sessions:** ~N
**Actual vs Expected:** [comparison]

### What Went Well
- ...

### What Was Difficult
- ...

### Improvements for Next Time
- ...
```

**Benefit:** Continuous improvement of the process itself.

### A10: Commit Message Convention

Link commits to plans:

```
[Plan #1] Add TokenBucket class

- Implements rate-based resource accumulation
- Supports debt (negative balance)

Part of: docs/plans/01_rate_allocation.md
```

**Benefit:** Git history tied to plans.

---

## Implementation Roadmap

### Phase 1: Low-Effort High-Impact (Done)

| Action | Effort | Impact | Status |
|--------|--------|--------|--------|
| Document handoff protocol | Low | High | ✅ Done |
| Add branch naming convention | Low | Medium | ✅ Done |
| Promote plan index coupling to strict | Low | Medium | ✅ Done |
| Add completion checklist to template | Low | Medium | ✅ Done |
| Create handoff template (A1) | Low | High | ✅ Done |
| Add commit message convention (A10) | Low | Medium | ✅ Done |

### Phase 2: Automation Scripts (Done)

| Script | Effort | Impact | Status |
|--------|--------|--------|--------|
| `check_claims.py` | Medium | High | ✅ Done |
| `validate_plan_completion.py` | Medium | High | ✅ Done |
| `plan_progress.py` (A8) | Low | Medium | ✅ Done |
| `claim_work.py` | Medium | Medium | TODO |
| `worktree.py` (A3) | Medium | Medium | TODO |

### Phase 3: Enforcement & Integration

| Action | Effort | Impact | Addresses |
|--------|--------|--------|-----------|
| Pre-commit hook (P6) | Medium | High | ✅ Done |
| Strict completion validation in CI | Medium | High | FM-6 |
| Plan dependency validation (A4) | Medium | Medium | Starting blocked plans |
| Branch-plan validation in CI | Low | Low | FM-12 |

### Phase 4: Observability (Aligned with Project Philosophy)

| Action | Effort | Impact |
|--------|--------|--------|
| Session audit log (A2) | Low | Medium |
| Coordination report script (A6) | Medium | Medium |
| Retrospective template (A9) | Low | Low |

### Prioritized Next Steps

1. ~~**Create handoff template** (A1)~~ ✅ Done
2. ~~**Add commit convention to CLAUDE.md** (A10)~~ ✅ Done
3. ~~**Implement `check_claims.py`**~~ ✅ Done
4. ~~**Implement `validate_plan_completion.py`**~~ ✅ Done
5. ~~**Implement `plan_progress.py`** (A8)~~ ✅ Done
6. ~~**Pre-commit hook** (P6)~~ ✅ Done
7. **Implement `claim_work.py`** - Automate claim/release in CLAUDE.md
8. **Implement `worktree.py`** (A3) - Reduce parallel work friction

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-12 | Created this analysis | Need to understand multi-CC failure modes |
| 2026-01-12 | Clarified FM-3 | /clear is user-controlled, not auto; renamed to "session handoff" |
| 2026-01-12 | Promoted plan→index coupling to strict | High-impact, prevents status drift |
| 2026-01-12 | Added completion ceremony checklist | Low-effort, prevents premature completion |

---

## References

- `CLAUDE.md` - Current coordination protocol
- `docs/plans/CLAUDE.md` - Plan workflow
- `scripts/doc_coupling.yaml` - Coupling definitions
- `scripts/check_plan_tests.py` - TDD verification
