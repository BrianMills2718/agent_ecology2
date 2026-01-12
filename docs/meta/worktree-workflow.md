# Pattern: Worktree Workflow

## Problem

When multiple Claude Code instances work on a shared codebase:
- Working in the same directory causes conflicts
- Switching branches disrupts other instances
- Reviewers can't easily examine PR changes
- Main directory gets cluttered with work-in-progress

## Solution

**All PR work MUST use git worktrees.** Each worktree is an isolated directory with its own branch, allowing:
- Multiple instances to work simultaneously without conflicts
- Clean separation between author and reviewer
- Main directory stays clean for reviews

## Files

| File | Purpose |
|------|---------|
| `Makefile` | `worktree`, `worktree-list`, `worktree-remove` targets |
| `CLAUDE.md` | Documents the requirement |

## Setup

### 1. Add Makefile targets

```makefile
worktree:  ## Create worktree for parallel CC work (usage: make worktree BRANCH=feature-name)
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree BRANCH=feature-name"; exit 1; fi
	git worktree add ../ecology-$(BRANCH) -b $(BRANCH)
	@echo ""
	@echo "Worktree created at ../ecology-$(BRANCH)"
	@echo "To use: cd ../ecology-$(BRANCH) && claude"
	@echo "To remove when done: git worktree remove ../ecology-$(BRANCH)"

worktree-list:  ## List active worktrees
	git worktree list

worktree-remove:  ## Remove a worktree (usage: make worktree-remove BRANCH=feature-name)
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree-remove BRANCH=feature-name"; exit 1; fi
	git worktree remove ../ecology-$(BRANCH)
```

### 2. Document in CLAUDE.md

Add to Multi-Claude Coordination section:

```markdown
### Worktree Requirement

**All PR work MUST use worktrees.** This ensures:
- Clean separation between author and reviewer
- No conflicts when multiple CC instances work simultaneously
- Main directory stays clean for reviews

```bash
# REQUIRED: Create worktree for any PR work
make worktree BRANCH=plan-03-docker
cd ../ecology-plan-03-docker && claude

# Do work, create PR, then cleanup
git worktree remove ../ecology-plan-03-docker
```

**Review pattern:**
1. Claude A creates PR from worktree
2. Claude B reviews in main directory (or different worktree)
3. Claude B approves/requests changes
4. After merge, remove worktree
```

## Usage

### Starting work

```bash
# Create worktree with new branch
make worktree BRANCH=plan-03-docker

# Navigate and start Claude
cd ../ecology-plan-03-docker
claude

# Claim work (inside worktree)
make claim TASK="Implement docker" PLAN=3
```

### During work

```bash
# List all worktrees
make worktree-list

# Or directly
git worktree list
```

### After PR merged

```bash
# Return to main directory
cd /path/to/main/repo

# Remove the worktree
make worktree-remove BRANCH=plan-03-docker

# Or directly
git worktree remove ../ecology-plan-03-docker
```

## Workflow Integration

Worktrees integrate with the claims system:

| Step | Command | Location |
|------|---------|----------|
| 1. Create worktree | `make worktree BRANCH=...` | Main directory |
| 2. Start Claude | `cd ../ecology-... && claude` | Worktree |
| 3. Claim work | `make claim TASK="..." PLAN=N` | Worktree |
| 4. Do work | Edit, test, commit | Worktree |
| 5. Create PR | `gh pr create` | Worktree |
| 6. Review | `git diff main..branch` | Main or other worktree |
| 7. Release claim | `make release` | Worktree |
| 8. Merge PR | `gh pr merge N` | Any |
| 9. Cleanup | `make worktree-remove BRANCH=...` | Main directory |

## Customization

### Worktree naming

Default pattern: `../ecology-$(BRANCH)`

To customize, edit Makefile:

```makefile
WORKTREE_PREFIX ?= ecology
WORKTREE_DIR ?= ..

worktree:
	git worktree add $(WORKTREE_DIR)/$(WORKTREE_PREFIX)-$(BRANCH) -b $(BRANCH)
```

### Existing branch

To create worktree for existing branch:

```bash
git worktree add ../ecology-existing-branch existing-branch
```

## Enforcement

This is a process requirement, not technically enforced. Violations result in:
- Merge conflicts when multiple instances edit same files
- Confusion about which instance owns which changes
- Difficulty reviewing PRs (can't diff cleanly)

The claims system helps surface violations - if two instances claim overlapping work without worktrees, conflicts will occur.
