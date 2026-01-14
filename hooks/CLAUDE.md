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

## Installation

```bash
# Symlink hooks to .git/hooks
ln -sf ../../hooks/pre-commit .git/hooks/pre-commit
ln -sf ../../hooks/commit-msg .git/hooks/commit-msg
ln -sf ../../hooks/post-commit .git/hooks/post-commit

# Or use the Makefile
make install-hooks
```

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

- `docs/meta/06_git-hooks.md` - Full pattern documentation
- `.github/workflows/ci.yml` - CI runs similar checks
