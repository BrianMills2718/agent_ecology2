# Understanding CWD and Paths

This document explains the "always run from main" rule and why it matters.

## The Rule

**Your current working directory (CWD) should always be the main repository.**

```bash
# Your CWD should be:
/path/to/repo              # Main repository

# NOT:
/path/to/repo/worktrees/plan-1-feature   # Inside a worktree
```

## Why This Matters

### Problem: Shell Breaks When Worktree Deleted

When you finish work and merge a PR, the worktree gets deleted:

```bash
make finish BRANCH=plan-1-feature PR=123
# This deletes: worktrees/plan-1-feature/
```

If your shell's CWD was inside that worktree:

```bash
$ pwd
/repo/worktrees/plan-1-feature

$ make finish BRANCH=plan-1-feature PR=123
# Worktree deleted...

$ ls
shell-init: error retrieving current directory: getcwd: cannot access parent directories
```

Your shell is now in an invalid state. Every command fails until you `cd` somewhere valid.

### Solution: Use Paths, Not CWD

Instead of changing into the worktree, reference it as a path:

```bash
# CWD stays at /repo (main)
$ pwd
/repo

# Edit files via path
$ vim worktrees/plan-1-feature/src/module.py

# Git commands via -C flag
$ git -C worktrees/plan-1-feature status
$ git -C worktrees/plan-1-feature add -A
$ git -C worktrees/plan-1-feature commit -m "[Plan #1] Add feature"

# After merge, CWD is still valid
$ make finish BRANCH=plan-1-feature PR=123
$ pwd
/repo   # Still works!
```

## Correct vs Incorrect Patterns

### Editing Files

```bash
# CORRECT - Use path from main
vim worktrees/plan-1/src/file.py
code worktrees/plan-1/src/file.py

# INCORRECT - cd into worktree
cd worktrees/plan-1
vim src/file.py
```

### Git Commands

```bash
# CORRECT - Use -C flag
git -C worktrees/plan-1 status
git -C worktrees/plan-1 add src/file.py
git -C worktrees/plan-1 commit -m "[Plan #1] Message"
git -C worktrees/plan-1 push -u origin plan-1

# INCORRECT - cd then git
cd worktrees/plan-1
git status
git add src/file.py
git commit -m "[Plan #1] Message"
```

### Running Tests

```bash
# CORRECT - Specify path
pytest worktrees/plan-1/tests/
python -m pytest worktrees/plan-1/tests/test_feature.py

# INCORRECT - cd then test
cd worktrees/plan-1
pytest tests/
```

### Make Commands

```bash
# CORRECT - Run from main (Makefile handles paths)
make test
make check
make finish BRANCH=plan-1 PR=123

# INCORRECT - Run from worktree
cd worktrees/plan-1
make test   # May not work; Makefile expects main CWD
```

## How Hooks Handle This

The meta-process hooks are designed to work from main:

```bash
# protect-main.sh checks if you're editing in main vs worktree
# It uses $(git rev-parse --show-toplevel) to find repo root

# block-worktree-remove.sh prevents accidental worktree deletion
# It validates paths relative to main
```

Hooks assume CWD is main. Running from inside a worktree may cause unexpected behavior.

## IDE Integration

### VS Code

Open the **main repository** as your workspace, not a worktree:

```bash
# CORRECT
code /path/to/repo

# INCORRECT
code /path/to/repo/worktrees/plan-1
```

Then use the file explorer to navigate to `worktrees/plan-1/src/...`

### Terminal in IDE

If your IDE opens a terminal, ensure it starts in main:

```bash
# Check your CWD
pwd
# Should be: /path/to/repo
# NOT: /path/to/repo/worktrees/...
```

## Exception: One-Off Commands

For quick one-off commands, you can use subshells:

```bash
# Subshell - CWD change is temporary
(cd worktrees/plan-1 && npm install)

# Your main shell's CWD is unchanged
pwd  # Still /repo
```

This is safe because the `cd` only affects the subshell.

## Troubleshooting

### "getcwd: cannot access parent directories"

Your CWD was deleted. Fix:

```bash
cd /path/to/repo   # Go back to main
```

### Commands fail with "not a git repository"

You may be in a deleted or invalid worktree:

```bash
# Check where you are
pwd

# If in worktrees/, go to main
cd /path/to/repo
```

### Hook errors about "not in main directory"

You're running a command from inside a worktree:

```bash
# Go to main first
cd /path/to/repo

# Then run your command
make test
```

## Quick Reference

| Task | Command (from main CWD) |
|------|-------------------------|
| Edit file | `vim worktrees/X/src/file.py` |
| Git status | `git -C worktrees/X status` |
| Git add | `git -C worktrees/X add -A` |
| Git commit | `git -C worktrees/X commit -m "msg"` |
| Git push | `git -C worktrees/X push -u origin X` |
| Run tests | `pytest worktrees/X/tests/` |
| Finish work | `make finish BRANCH=X PR=N` |

## Summary

1. **Always keep CWD at main repository**
2. **Use paths to reference worktree files**: `worktrees/X/src/file.py`
3. **Use `git -C` for git commands**: `git -C worktrees/X commit`
4. **After merge, your shell stays valid** because CWD wasn't inside the deleted worktree
