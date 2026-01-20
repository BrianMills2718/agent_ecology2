# Plan #136: Lifecycle Robustness

**Status:** 🔄 In Progress
**Priority:** High
**Blocked By:** None
**Blocks:** Meta-process reliability

---

## Problem Statement

Two issues causing confused state and stuck processes:

1. **`complete_plan.py` hangs forever** - subprocess.run() calls have no timeout, so if pytest hangs (network, input wait), the script never completes. Found 12+ stuck instances.

2. **Open PRs pile up unmerged** - No warning when starting new work with open PRs, leading to orphaned PRs and confused state.

## Solution

### Fix 1: Add Timeouts to complete_plan.py

Add timeout parameter to all subprocess.run() calls:

```python
result = subprocess.run(
    ["pytest", ...],
    cwd=project_root,
    capture_output=True,
    text=True,
    timeout=300,  # 5 minute timeout
)
```

Handle `subprocess.TimeoutExpired` and report clearly.

### Fix 2: Warn on Open PRs

In `scripts/create_worktree.py` (called by `make worktree`), check for open PRs owned by this instance and warn:

```
⚠️  You have 2 open PRs that should be merged first:
   - #458: [Plan #131] Edit artifact action
   - #459: [Plan #132] Standardize reasoning field

Merge with: make finish BRANCH=<branch> PR=<number>
Continue anyway? (y/N)
```

Make this configurable:
- `WARN_OPEN_PRS=warn` (default) - warn but allow proceeding
- `WARN_OPEN_PRS=block` - must merge first
- `WARN_OPEN_PRS=none` - no check

## Acceptance Criteria

- [ ] `complete_plan.py` has 5-minute timeout on all subprocess calls
- [ ] TimeoutExpired is caught and reports "Tests timed out after 5 minutes"
- [ ] `make worktree` warns if open PRs exist
- [ ] Warning is configurable via environment variable
- [ ] Tests pass

## Test Plan

1. Run `complete_plan.py --plan 133 --dry-run` - should complete (not hang)
2. Create a test PR, then run `make worktree` - should see warning
3. Set `WARN_OPEN_PRS=none`, run `make worktree` - no warning
