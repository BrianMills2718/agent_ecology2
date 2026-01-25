# Git Hooks Directory

Git hooks for local pre-commit/commit-msg validation.

## Purpose

Catch issues before they reach CI. These hooks run locally on every commit.

## Files

| Hook | Purpose |
|------|---------|
| `pre-commit` | Doc-coupling, mypy, config validation, branch divergence check |
| `commit-msg` | Validates commit message format (`[Plan #N]` or `[Trivial]`) |
| `post-commit` | Reminds about unpushed commits to prevent divergence |
| `pre-push` | Warns if pushing branch without active claim (warning only) |

## Installation

**Automatic (recommended):** Hooks auto-install when you run common make targets:
```bash
make test    # Auto-installs hooks before running tests
make check   # Auto-installs hooks before running checks
```

**Manual:** If needed, install explicitly:
```bash
make install-hooks
```

The Makefile creates symlinks from `.git/hooks/` to this directory.
Worktrees share hooks with the main repo automatically.

## Bypass

For emergencies only:

```bash
git commit --no-verify -m "..."
```

## What They Check

**pre-commit:**
1. Doc-coupling violations (strict mode)
2. Mypy on staged `src/` files
3. Coupling config validity
4. Plan status consistency (when plan files staged)
5. Branch divergence detection (blocks if diverged, warns if behind)

> **Note:** Plan status check (#4) prevents manual status edits that don't update both
> the plan file AND the index. Always use `complete_plan.py` instead of editing manually.

**commit-msg:**
1. Requires `[Plan #N]` or `[Trivial]` prefix
2. Validates plan number exists
3. Validates trivial commits are actually trivial

**post-commit:**
1. Shows count of unpushed commits
2. Reminds to push to prevent divergence

## Modifying Hooks

1. Edit the hook file in this directory
2. Test locally: `./hooks/pre-commit`
3. Commit the change (hooks apply to the hooks themselves)

## Related

- `meta/patterns/06_git-hooks.md` - Full pattern documentation
- `.github/workflows/ci.yml` - CI runs similar checks
