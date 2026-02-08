# Git Hooks Directory

Git hooks for local pre-commit/commit-msg validation.

## Purpose

Catch issues before they reach CI. These hooks run locally on every commit.

## Files

| Hook | Purpose |
|------|---------|
| `pre-commit` | Plan index regeneration, doc-coupling check, mypy on staged files |
| `commit-msg` | Validates commit message format (`[Plan #N]` or `[Trivial]`) |
| `post-commit` | Reminds about unpushed commits to prevent divergence |

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

## Bypass

For emergencies only:

```bash
git commit --no-verify -m "..."
```

## What They Check

**pre-commit:**
1. Plan index regeneration (`generate_plan_index.py`)
2. Doc-coupling violations (respects `strict_doc_coupling` config + weight system)
3. Mypy on staged `src/` files (non-blocking warning)

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

- `.github/workflows/ci.yml` - CI runs similar checks
