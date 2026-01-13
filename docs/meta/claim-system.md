# Pattern: Claim System

## Problem

When multiple AI instances (or developers) work in parallel:
- Two instances start the same work
- Neither knows the other is working
- Merge conflicts, wasted effort, confusion

## Solution

1. Before starting work, "claim" it in a shared file
2. **Overlap detection** warns if similar work is already claimed
3. Other instances see the claim and work on something else
4. When done, "release" the claim
5. Stale claims (>4 hours) flagged for cleanup
6. Plan dependencies checked before claiming
7. **CI verifies claims** to catch violations

## Enforcement Levels

| Level | What | When |
|-------|------|------|
| **Overlap Detection** | Blocks claims that overlap with existing work | At claim time |
| **Worktree Mandate** | `make worktree` requires claiming first | At worktree creation |
| **CI Verification** | Warns if PR branch wasn't claimed | At PR creation |

### Overlap Detection (NEW)

When you try to claim work, the system checks for overlapping claims:

```bash
$ python scripts/check_claims.py --claim --task "Create feature definitions"

============================================================
⚠️  POTENTIAL OVERLAP DETECTED
============================================================

  Overlap with: feature-definitions
  Their task:   Create feature definitions for core capabilities
  Similarity:   80% (overlapping: feature)

------------------------------------------------------------
This may cause duplicate work or merge conflicts.
Check with the other instance before proceeding.

Use --force to claim anyway (coordinates at your own risk).
```

Overlap is detected based on:
- **Same plan number** - Always blocked (100% overlap)
- **Similar task descriptions** - Keyword-based similarity (>40% triggers warning)

### CI Verification (NEW)

CI checks that PR branches were claimed before work started:

```yaml
# .github/workflows/ci.yml
claim-verification:
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - name: Verify branch was claimed
      run: python scripts/check_claims.py --verify-claim
```

Currently informational (warnings only). Will become strict enforcement.

## Files

| File | Purpose |
|------|---------|
| `.claude/active-work.yaml` | Machine-readable claim storage |
| `CLAUDE.md` | Human-readable Active Work table |
| `scripts/check_claims.py` | Claim management script |

## Usage

### Checking for overlaps before claiming

```bash
# Preview mode - check without claiming
python scripts/check_claims.py --check-overlap "Create feature definitions"

# Check overlap for a specific plan
python scripts/check_claims.py --check-overlap "Implement tests" --plan 21
```

### Claiming work

```bash
# Claim with auto-detected branch ID
python scripts/check_claims.py --claim --task "Implement feature X"

# Claim with plan reference
python scripts/check_claims.py --claim --plan 3 --task "Docker isolation"

# Force claim despite overlap warning
python scripts/check_claims.py --claim --task "Feature Y" --force
```

### Checking claims

```bash
# List all active claims
python scripts/check_claims.py --list

# Check for stale claims (default action)
python scripts/check_claims.py

# Check plan dependencies before claiming
python scripts/check_claims.py --check-deps 7

# CI mode: verify current branch has a claim
python scripts/check_claims.py --verify-claim
```

### Releasing claims

```bash
# Release current branch's claim
python scripts/check_claims.py --release

# Release with TDD validation
python scripts/check_claims.py --release --validate
```

### Maintenance

```bash
# Sync YAML to CLAUDE.md table
python scripts/check_claims.py --sync

# Clean up old completed entries (>24h)
python scripts/check_claims.py --cleanup
```

## Overlap Detection Algorithm

The system uses keyword-based scope detection:

```python
SCOPE_KEYWORDS = {
    "feature": ["feature", "features", "definition", "definitions", "yaml"],
    "test": ["test", "tests", "testing", "tdd", "pytest"],
    "doc": ["doc", "docs", "documentation", "readme", "claude.md"],
    "ci": ["ci", "workflow", "github", "actions", "enforcement"],
    "plan": ["plan", "plans", "gap", "gaps", "implementation"],
    "claim": ["claim", "claims", "coordination", "checkout"],
}
```

Two tasks overlap if:
1. They're for the same plan number, OR
2. They share scope keywords AND have ≥3 significant words in common

The similarity threshold is 40%. Tasks below this are considered non-overlapping.

## Best Practices

1. **Check overlaps first** - `--check-overlap "task"` before claiming
2. **Claim before starting** - Even for "quick" work
3. **Use specific task descriptions** - Helps overlap detection
4. **Release promptly** - Don't hold claims overnight
5. **Check claims first** - `--list` before starting any work
6. **Use plan references** - Links claim to documentation
7. **Clean up regularly** - Run `--cleanup` periodically

## Limitations

- **Overlap detection is heuristic** - May miss some overlaps or flag false positives
- **CI check is informational** - Currently warns but doesn't block (will be strict later)
- **Git conflicts** - If two instances claim simultaneously, YAML may conflict
- **Stale detection is passive** - Only flagged when script runs
- **No lock** - Claim is advisory, not a mutex

## See Also

- [worktree-enforcement.md](worktree-enforcement.md) - Worktree + claim workflow
- [pr-coordination.md](pr-coordination.md) - PR workflow with claims
- [plan-workflow.md](plan-workflow.md) - Plans that claims reference
- [git-hooks.md](git-hooks.md) - Can check for claim before commit
