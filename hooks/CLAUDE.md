# Git Hooks Directory

Git hooks for local pre-commit/commit-msg validation.

## Purpose

Catch issues before they reach CI. These hooks run locally on every commit.

## Files

| Hook | Purpose |
|------|---------|
| `pre-commit` | Doc-coupling check, mypy on changed files, config validation |
| `commit-msg` | Validates commit message format (`[Plan #N]` or `[Trivial]`) |

## Installation

```bash
# Symlink hooks to .git/hooks
ln -sf ../../hooks/pre-commit .git/hooks/pre-commit
ln -sf ../../hooks/commit-msg .git/hooks/commit-msg

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

**commit-msg:**
1. Requires `[Plan #N]` or `[Trivial]` prefix
2. Validates plan number exists
3. Validates trivial commits are actually trivial

## Modifying Hooks

1. Edit the hook file in this directory
2. Test locally: `./hooks/pre-commit`
3. Commit the change (hooks apply to the hooks themselves)

## Related

- `docs/meta/06_git-hooks.md` - Full pattern documentation
- `.github/workflows/ci.yml` - CI runs similar checks
