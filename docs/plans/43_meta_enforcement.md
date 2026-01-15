# Plan #43: Comprehensive Meta-Process Enforcement

**Status:** ✅ Complete

**Verified:** 2026-01-15T04:05:40Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-15T04:05:40Z
tests:
  unit: 1380 passed, 7 skipped, 5 warnings in 20.37s
  e2e_smoke: PASSED (2.40s)
  e2e_real: PASSED (34.93s)
  doc_coupling: passed
commit: 4f0c0d0
```
**Priority:** **Critical**
**Blocked By:** None
**Blocks:** All future work (meta-process integrity)

---

## Problem

Meta-processes are documented but not enforced. Documentation without enforcement is wishful thinking.

### Current State

| Pattern | Documented | Enforced | Gap |
|---------|------------|----------|-----|
| ADR Creation | ✅ | ❌ | Decisions made without ADRs |
| ADR Governance | ✅ | ✅ | Good |
| Claim System | ✅ | ❌ | Multi-CC conflicts |
| Plan Workflow | ✅ | Partial | Work without plans |
| Verification | ✅ | Partial | Plans merged without evidence |
| Human Review | ✅ | ❌ | Review flags ignored |
| E2E/Acceptance Tests | ✅ | ❌ | Features without acceptance tests |
| Git Hooks | ✅ | Partial | Not auto-installed |
| PR Coordination | ✅ | ❌ | PRs go stale |
| Worktree | ✅ | ✅ | Fixed in PR #117/#119 |

### Evidence of Failure

1. **ADRs**: 30+ decisions in DESIGN_CLARIFICATIONS.md, only 6 ADRs
2. **Claims**: Multi-CC instance conflicts lost work today
3. **Verification**: Plan #40 merged without complete_plan.py
4. **Acceptance**: No V1 acceptance test exists

---

## Solution: Enforcement at Every Layer

### Layer 1: Git Hooks (Immediate Feedback)

| Hook | Enforces | Status |
|------|----------|--------|
| pre-commit | Worktree/branch rules | ✅ Done |
| commit-msg | [Plan #N] prefix required | ✅ Done (hooks/commit-msg) |
| pre-push | Claim exists for branch | ✅ Done (hooks/pre-push, warning only) |

### Layer 2: CI Checks (PR Gates)

| Check | Enforces | Status |
|-------|----------|--------|
| Plan prefix | All commits have [Plan #N] or [Trivial] | ✅ Done (CI enforces, fails) |
| Claim validation | PR branch has active claim | ✅ Done (CI warns) |
| Verification evidence | Plan file has verification block | ✅ Done (post-merge check) |
| Human review flag | Plans with flag block until reviewed | ✅ Done (CI warns) |
| ADR requirement | Core changes require ADR link | ✅ Done (CI warns, uses script) |
| Acceptance tests | Features require acceptance test | ✅ Done (V1 exists) |
| PR freshness | Warn if >N commits behind main | ✅ Done (pre-commit hook) |

### Layer 3: Content Requirements (Quality Gates)

| Requirement | Trigger | Enforcement |
|-------------|---------|-------------|
| ADR creation | Changes to src/world/*.py core | CI blocks without ADR |
| Acceptance test | Feature marked complete | CI blocks without test |
| Human review | Plan has `## Human Review Required` | CI blocks until approved |

---

## Implementation

### Phase 1: Git Hooks

#### 1.1 Commit Message Hook

```bash
# .git/hooks/commit-msg
# Require [Plan #N] or [Trivial] prefix
MSG=$(cat "$1")
if ! echo "$MSG" | grep -qE '^\[(Plan #[0-9]+|Trivial)\]'; then
    echo "ERROR: Commit message must start with [Plan #N] or [Trivial]"
    exit 1
fi
```

#### 1.2 Pre-push Claim Check

```bash
# .git/hooks/pre-push  
# Warn if pushing branch without claim
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$BRANCH" != "main" ]]; then
    python scripts/check_claims.py --verify-branch "$BRANCH" || {
        echo "WARNING: No claim found for branch $BRANCH"
        echo "Consider: python scripts/check_claims.py --claim --task '...'"
    }
fi
```

### Phase 2: CI Enforcement

#### 2.1 Plan Prefix Check

```yaml
# .github/workflows/ci.yml
commit-message-check:
  runs-on: ubuntu-latest
  steps:
    - name: Check commit messages
      run: |
        for sha in $(git log --format=%H origin/main..HEAD); do
          msg=$(git log -1 --format=%s $sha)
          if ! echo "$msg" | grep -qE '^\[(Plan #[0-9]+|Trivial)\]'; then
            echo "ERROR: $sha has invalid prefix: $msg"
            exit 1
          fi
        done
```

#### 2.2 Claim Validation

```python
# scripts/check_claims.py --verify-pr
# Check if PR branch has associated claim
```

#### 2.3 Verification Evidence Check

```python
# scripts/check_plan_completion.py
# After merge, verify plan has verification block
```

#### 2.4 ADR Requirement Check

```python
# scripts/check_adr_requirement.py
# If PR touches src/world/{ledger,executor,artifacts,genesis}.py
# Require commit message references ADR or creates new one
```

#### 2.5 Acceptance Test Requirement

```python
# scripts/check_acceptance_tests.py
# If feature status changes to Complete
# Require tests/e2e/test_<feature>.py exists
```

### Phase 3: Content Backfill

#### 3.1 ADR Backlog

Create ADRs for high-certainty decisions:

| Decision | Certainty | New ADR | Status |
|----------|-----------|---------|--------|
| Single ID namespace | 90% | ADR-0007 | ✅ Created |
| Token bucket for flow | 90% | ADR-0008 | ✅ Created |
| Memory as artifact | 100% | ADR-0009 | ✅ Created |
| Continuous loops | 90% | ADR-0010 | ✅ Created |
| Standing = pays costs | 90% | ADR-0011 | ✅ Created |
| Scrip non-negative | 90% | ADR-0012 | ✅ Created |

#### 3.2 V1 Acceptance Test

Create `tests/e2e/test_v1_acceptance.py` per Plan #41.

---

## Required Tests

| Test | Verifies |
|------|----------|
| `tests/unit/test_commit_msg_hook.py::TestCommitMsgHook::test_rejects_no_prefix` | Hook blocks bad commits |
| `tests/unit/test_commit_msg_hook.py::TestCommitMsgHook::test_accepts_plan_prefix` | Hook allows [Plan #N] |
| `tests/unit/test_commit_msg_hook.py::TestCommitMsgHook::test_accepts_trivial` | Hook allows [Trivial] |
| `tests/unit/test_check_claims.py::TestVerifyBranch::test_verify_branch_with_matching_claim` | Claim check works |
| `tests/unit/test_check_adr_requirement.py::TestADRRequirement::test_requires_adr_for_core` | ADR requirement works |

---

## Verification

- [x] commit-msg hook rejects bad prefixes
- [x] CI fails on commits without [Plan #N]
- [x] CI warns on PRs without claims
- [x] CI warns on plans with human review flag
- [x] CI warns on ADR requirement for core file changes
- [x] ADR backlog cleared (6 new ADRs: 0007-0012)
- [x] V1 acceptance test exists (tests/e2e/test_v1_acceptance.py)

---

## Acceptance Criteria

1. **Zero unenforced meta-processes** - Every documented process has enforcement
2. **ADR coverage** - All 90%+ certainty decisions have ADRs
3. **Claim coverage** - 100% of PRs have associated claims
4. **Verification coverage** - 100% of completed plans have evidence

---

## Notes

This plan enforces content creation, not just content following:
- ADRs must be CREATED for architectural changes
- Acceptance tests must be CREATED for features
- Claims must be CREATED before work

The meta-process becomes self-enforcing.
